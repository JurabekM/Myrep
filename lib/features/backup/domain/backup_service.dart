import 'dart:convert';
import 'dart:io';

import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/journal_guard.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/security/security_api.pigeon.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter/services.dart';

/// Zaxira nusxani parol bilan shifrlash (Kotlin: PBKDF2 + AES-256-GCM).
abstract interface class BackupCipher {
  Future<Uint8List> encrypt(String password, Uint8List plain);
  Future<Uint8List> decrypt(String password, Uint8List data);
}

/// Native (Pigeon) shifr; xato kodlari domen kodlariga aylantiriladi.
class NativeBackupCipher implements BackupCipher {
  NativeBackupCipher(this._api);

  final SecurityApi _api;

  @override
  Future<Uint8List> encrypt(String password, Uint8List plain) =>
      _api.encryptBackup(password, plain);

  @override
  Future<Uint8List> decrypt(String password, Uint8List data) async {
    try {
      return await _api.decryptBackup(password, data);
    } on PlatformException catch (e) {
      throw DomainRuleException(switch (e.code) {
        'BACKUP_BAD_PASSWORD' => BackupService.errBadPassword,
        'BACKUP_FORMAT' => BackupService.errFormat,
        _ => BackupService.errFormat,
      });
    }
  }
}

/// Shifrlangan eksport va import (MVP_PLAN Vazifa 15): butun baza
/// (hamma jadval, qatorlar o'zgarishsiz) JSON → gzip → parol bilan shifr.
/// Import hozirgi ma'lumotlarni to'liq almashtiradi (1:1 tiklash).
class BackupService {
  BackupService(this._db, this._cipher, this._clock);

  static const format = 'baraka-daftari-backup';
  static const minPassword = 8;

  static const errWeakPassword = 'backup_password_too_short';
  static const errBadPassword = 'backup_bad_password';
  static const errFormat = 'backup_bad_format';

  /// Boshqa sxema versiyasidagi nusxa (ilovani yangilang).
  static const errVersion = 'backup_schema_mismatch';

  final AppDatabase _db;
  final BackupCipher _cipher;
  final Clock _clock;

  List<String> get _tables => [
    for (final t in _db.allTables) t.actualTableName,
  ]..sort();

  /// Hamma jadvallar xom ko'rinishda (ustun → qiymat).
  Future<Map<String, List<Map<String, Object?>>>> dump() async => {
    for (final t in _tables)
      t: [
        for (final r in await _db.customSelect('SELECT * FROM "$t"').get())
          r.data,
      ],
  };

  static Object? _encode(Object? v) =>
      v is Uint8List ? {r'$b64': base64Encode(v)} : v;

  static Object? _decode(Object? v) => v is Map && v.containsKey(r'$b64')
      ? base64Decode(v[r'$b64'] as String)
      : v;

  Future<Uint8List> export(String password) async {
    if (password.length < minPassword) {
      throw const DomainRuleException(errWeakPassword);
    }
    final tables = await dump();
    final json = jsonEncode({
      'format': format,
      'schemaVersion': _db.schemaVersion,
      'exportedAt': _clock.nowUtc().toIso8601String(),
      'tables': {
        for (final MapEntry(:key, :value) in tables.entries)
          key: [
            for (final row in value)
              {for (final c in row.entries) c.key: _encode(c.value)},
          ],
      },
    });
    final packed = Uint8List.fromList(gzip.encode(utf8.encode(json)));
    return _cipher.encrypt(password, packed);
  }

  /// Faylni ochib, bazani to'liq almashtirish. Natija — tiklangan qatorlar.
  Future<int> import(Uint8List data, String password) async {
    final packed = await _cipher.decrypt(password, data);
    final Map<String, dynamic> root;
    try {
      root =
          jsonDecode(utf8.decode(gzip.decode(packed))) as Map<String, dynamic>;
    } on Object {
      throw const DomainRuleException(errFormat);
    }
    if (root['format'] != format) {
      throw const DomainRuleException(errFormat);
    }
    if (root['schemaVersion'] != _db.schemaVersion) {
      throw const DomainRuleException(errVersion);
    }
    final tables = (root['tables'] as Map<String, dynamic>).map(
      (k, v) => MapEntry(k, (v as List).cast<Map<String, dynamic>>()),
    );
    final known = _tables.toSet();
    if (tables.keys.any((t) => !known.contains(t))) {
      throw const DomainRuleException(errFormat);
    }
    // Uy xo'jaligi yo'q yuk (bo'sh yoki buzuq) butun bazani o'chirib qo'ymasin:
    // onboarding har doim uy xo'jaligini yaratadi, demak haqiqiy nusxada bor.
    if ((tables['households'] ?? const <Map<String, dynamic>>[]).isEmpty) {
      throw const DomainRuleException(errFormat);
    }
    var count = 0;
    // Tashqi kalitlar butun almashtirish davomida o'chiriladi (tartib
    // ahamiyatsiz), oxirida tekshiriladi.
    await _db.customStatement('PRAGMA foreign_keys = OFF');
    try {
      // Jurnal append-only (trigger) — faqat to'liq tiklashda, bitta
      // tranzaksiya ichida ochiladi.
      await _db.transaction(
        () => withJournalUnlocked(_db, () async {
          for (final t in known) {
            await _db.customStatement('DELETE FROM "$t"');
          }
          for (final MapEntry(key: t, value: rows) in tables.entries) {
            for (final row in rows) {
              final cols = row.keys.toList();
              await _db.customStatement(
                'INSERT INTO "$t" (${cols.map((c) => '"$c"').join(', ')}) '
                'VALUES (${List.filled(cols.length, '?').join(', ')})',
                [for (final c in cols) _decode(row[c])],
              );
              count++;
            }
          }
          final broken = await _db
              .customSelect('PRAGMA foreign_key_check')
              .get();
          if (broken.isNotEmpty) throw const DomainRuleException(errFormat);
        }),
      );
    } finally {
      await _db.customStatement('PRAGMA foreign_keys = ON');
    }
    return count;
  }
}
