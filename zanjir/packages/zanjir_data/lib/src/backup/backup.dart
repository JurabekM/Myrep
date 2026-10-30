import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';
import 'package:drift/native.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import '../repo/audit_repository.dart';
import '../repo/context.dart';
import '../repo/settings_repository.dart';
import '../repo/user_repository.dart';

/// Qurilmadagi profil identifikatorlari (`local_pref`).
typedef ProfileIds = ({String orgId, String userId, String deviceId});

/// Shifrlangan zaxira fayli (ADR-0017): butun lokal baza (`VACUUM INTO`, gzip), parol → Argon2id kaliti →
/// ChaCha20-Poly1305 (autentifikatsiyalangan). Sarlavha shifrlanmaydi, lekin AEAD bilan himoyalangan (o'zgartirilsa —
/// ochilmaydi). Format:
///
///     "ZNJB" | 0x01 | uint32 BE sarlavha uzunligi | sarlavha (JSON) | shifrmatn | MAC (16 bayt)
///
/// Faylda shaxsiy ma'lumot va imzolangan protokollar bor — parolsiz o'qib bo'lmaydi; parol yo'qolsa zaxira ham yo'qoladi.
const backupFormat = 'zanjir.backup/1';
const backupFileExtension = 'zanjir';
const _magic = [0x5A, 0x4E, 0x4A, 0x42]; // "ZNJB"
const _version = 1;

/// Zaxira paroli kamida shuncha belgi.
const backupPasswordMinLength = 10;

/// Argon2id parametrlari (RFC 9106, 2-tavsiya ruhida: 64 MiB, t=3, p=1). Faylda saqlanadi; o'qishda chegaralar
/// tekshiriladi (zararli fayl telefonni xotirasiz qoldirmasin).
class KdfParams {
  const KdfParams({required this.memoryKib, required this.iterations, required this.parallelism});
  final int memoryKib;
  final int iterations;
  final int parallelism;

  static const standard = KdfParams(memoryKib: 64 * 1024, iterations: 3, parallelism: 1);

  Map<String, Object?> toJson() => {
    'alg': 'argon2id',
    'memory_kib': memoryKib,
    'iterations': iterations,
    'parallelism': parallelism,
  };

  static KdfParams fromJson(Object? j) {
    if (j is! Map || j['alg'] != 'argon2id') throw const DataRuleException('backup_invalid', 'kdf');
    final m = j['memory_kib'], t = j['iterations'], p = j['parallelism'];
    if (m is! int || t is! int || p is! int || m < 8 * 1024 || m > 256 * 1024 || t < 1 || t > 10 || p < 1 || p > 4) {
      throw const DataRuleException('backup_invalid', 'kdf');
    }
    return KdfParams(memoryKib: m, iterations: t, parallelism: p);
  }
}

/// Sarlavha (shifrlanmagan): format, yaratilgan vaqt, sxema versiyasi, KDF, tuz va nonce. Shaxsiy ma'lumot yo'q.
class BackupHeader {
  const BackupHeader({
    required this.createdAt,
    required this.schemaVersion,
    required this.kdf,
    required this.salt,
    required this.nonce,
  });
  final DateTime createdAt;
  final int schemaVersion;
  final KdfParams kdf;
  final List<int> salt;
  final List<int> nonce;

  Map<String, Object?> toJson() => {
    'format': backupFormat,
    'created_at': isoUtcMillis(createdAt),
    'schema_version': schemaVersion,
    'kdf': kdf.toJson(),
    'salt': base64Encode(salt),
    'cipher': 'chacha20-poly1305',
    'nonce': base64Encode(nonce),
  };

  static BackupHeader fromJson(Object? j) {
    if (j is! Map || j['format'] != backupFormat || j['cipher'] != 'chacha20-poly1305') {
      throw const DataRuleException('backup_invalid', 'header');
    }
    try {
      return BackupHeader(
        createdAt: DateTime.parse(j['created_at']! as String),
        schemaVersion: j['schema_version']! as int,
        kdf: KdfParams.fromJson(j['kdf']),
        salt: base64Decode(j['salt']! as String),
        nonce: base64Decode(j['nonce']! as String),
      );
    } on Object catch (e) {
      if (e is DataRuleException) rethrow;
      throw const DataRuleException('backup_invalid', 'header');
    }
  }
}

/// Zaxira yaratish. Vaqtinchalik ochiq baza nusxasi tizimning vaqtinchalik papkasida faqat shu chaqiruv davomida turadi.
Future<Uint8List> createBackup(
  ZanjirDatabase db, {
  required String password,
  required DateTime now,
  KdfParams kdf = KdfParams.standard,
  Random? random,
}) async {
  if (password.length < backupPasswordMinLength) throw const DataRuleException('backup_password_too_short');
  final rnd = random ?? Random.secure();
  final tmp = await Directory.systemTemp.createTemp('zanjir-backup-');
  try {
    final file = File('${tmp.path}/db.sqlite');
    await db.customStatement('VACUUM INTO ?', [file.path]);
    final plain = gzip.encode(await file.readAsBytes());
    final header = BackupHeader(
      createdAt: now.toUtc(),
      schemaVersion: db.schemaVersion,
      kdf: kdf,
      salt: List.generate(16, (_) => rnd.nextInt(256)),
      nonce: List.generate(12, (_) => rnd.nextInt(256)),
    );
    final headerBytes = utf8.encode(jsonEncode(header.toJson()));
    final prefix = _prefix(headerBytes);
    return Uint8List.fromList([...prefix, ...await _seal(plain, password, header, prefix)]);
  } finally {
    await tmp.delete(recursive: true);
  }
}

/// Faqat sarlavha (parolsiz): fayl ZANJIR zaxirasimi, qachon yaratilgan.
BackupHeader readBackupHeader(List<int> bytes) => _parse(bytes).header;

/// Zaxirani bo'sh bazaga tiklash (yangi telefon). Telefon yangi qurilma sifatida ro'yxatdan o'tadi ([signer] — yangi
/// kalit), eski qurilmalarning imzolari tekshiriladigan holda qoladi; `BACKUP_RESTORED` audit hodisasi yoziladi.
///
/// Xatolar: `backup_invalid` (ZANJIR zaxirasi emas / buzilgan), `backup_wrong_password` (parol noto'g'ri yoki fayl
/// o'zgartirilgan), `backup_newer_version`, `restore_target_not_empty`, `backup_audit_broken`.
Future<ProfileIds> restoreBackup(
  ZanjirDatabase target,
  List<int> bytes, {
  required String password,
  required Signer signer,
  required DateTime Function() clock,
}) async {
  final parsed = _parse(bytes);
  final header = parsed.header;
  if (header.schemaVersion > target.schemaVersion) throw const DataRuleException('backup_newer_version');
  final orgs = await target.customSelect('SELECT count(*) AS n FROM organization').getSingle();
  if (orgs.read<int>('n') != 0) throw const DataRuleException('restore_target_not_empty');

  final plain = await _open(parsed, password) ?? (throw const DataRuleException('backup_wrong_password'));

  final String orgId, userId, oldDeviceId;
  final tmp = await Directory.systemTemp.createTemp('zanjir-restore-');
  try {
    final file = File('${tmp.path}/db.sqlite');
    await file.writeAsBytes(gzip.decode(plain), flush: true);
    // Manba bazani ochish eski sxemani joriy versiyagacha ko'taradi (migratsiyalar).
    final source = ZanjirDatabase(NativeDatabase(file));
    try {
      final check = await source.customSelect('PRAGMA integrity_check').getSingle();
      if (check.data.values.first != 'ok') throw const DataRuleException('backup_invalid', 'integrity');
      final prefs = LocalPrefRepository(source);
      orgId =
          await prefs.get(LocalPrefRepository.orgId) ?? (throw const DataRuleException('backup_invalid', 'profile'));
      userId =
          await prefs.get(LocalPrefRepository.userId) ?? (throw const DataRuleException('backup_invalid', 'profile'));
      oldDeviceId =
          await prefs.get(LocalPrefRepository.deviceId) ?? (throw const DataRuleException('backup_invalid', 'profile'));
      final chains = await verifyOrgChains(DataContext(db: source, orgId: orgId));
      final broken = [
        for (final e in chains.entries)
          if (!e.value.ok) e.key,
      ];
      if (broken.isNotEmpty) throw DataRuleException('backup_audit_broken', broken.join(', '));
    } finally {
      await source.close();
    }
    // Nusxalash, yangi qurilma va audit hodisasi — bitta tranzaksiyada (yarim tiklangan baza qolmaydi).
    return await _copyAll(target, file.path, () async {
      final ctx = DataContext(db: target, orgId: orgId, clock: clock);
      final device = await DeviceRepository(ctx)
          .register(userId: userId, publicKeyHex: signer.publicKeyHex, sigAlg: signer.sigAlg);
      await LocalPrefRepository(target).set(LocalPrefRepository.deviceId, device.id);
      await AuditRepository(ctx, signer: signer, deviceId: device.id, actorId: userId).append(
        eventType: 'BACKUP_RESTORED',
        entityId: device.id,
        payload: {
          'backup_created_at': isoUtcMillis(header.createdAt),
          'backup_sha256': sha256Hex(bytes),
          'previous_device_id': oldDeviceId,
        },
      );
      return (orgId: orgId, userId: userId, deviceId: device.id);
    });
  } finally {
    await tmp.delete(recursive: true);
  }
}

/// Barcha jadvallar (ustunlar nomi bo'yicha — migratsiya qilingan va yangi yaratilgan sxemada tartib farq qilishi
/// mumkin) va [then] — bitta tranzaksiyada; tashqi kalitlar oxirida tekshiriladi.
Future<T> _copyAll<T>(ZanjirDatabase target, String sourcePath, Future<T> Function() then) async {
  await target.customStatement('ATTACH DATABASE ? AS src', [sourcePath]);
  try {
    return await target.transaction(() async {
      await target.customStatement('PRAGMA defer_foreign_keys = ON');
      for (final t in target.allTables) {
        final name = t.actualTableName;
        final cols = [for (final c in t.$columns) '"${c.name}"'].join(', ');
        await target.customStatement('INSERT INTO main."$name" ($cols) SELECT $cols FROM src."$name"');
      }
      return then();
    });
  } finally {
    await target.customStatement('DETACH DATABASE src');
  }
}

// Argon2id (64 MiB) va shifrlash sof Dart'da bir necha soniya oladi — alohida isolate'da (UI qotmaydi).
Future<List<int>> _seal(List<int> plain, String password, BackupHeader h, List<int> aad) => Isolate.run(() async {
  final box = await Chacha20.poly1305Aead().encrypt(
    plain,
    secretKey: await _key(password, h),
    nonce: h.nonce,
    aad: aad,
  );
  return [...box.cipherText, ...box.mac.bytes];
});

/// `null` — parol noto'g'ri yoki fayl o'zgartirilgan (MAC mos emas).
Future<List<int>?> _open(_Parsed p, String password) => Isolate.run(() async {
  try {
    return await Chacha20.poly1305Aead().decrypt(
      SecretBox(p.cipherText, nonce: p.header.nonce, mac: Mac(p.mac)),
      secretKey: await _key(password, p.header),
      aad: p.prefix,
    );
  } on SecretBoxAuthenticationError {
    return null;
  }
});

Future<SecretKey> _key(String password, BackupHeader h) => Argon2id(
  parallelism: h.kdf.parallelism,
  memory: h.kdf.memoryKib,
  iterations: h.kdf.iterations,
  hashLength: 32,
).deriveKeyFromPassword(password: password, nonce: h.salt);

List<int> _prefix(List<int> headerBytes) => [
  ..._magic,
  _version,
  ...(ByteData(4)..setUint32(0, headerBytes.length)).buffer.asUint8List(),
  ...headerBytes,
];

typedef _Parsed = ({BackupHeader header, List<int> prefix, List<int> cipherText, List<int> mac});

_Parsed _parse(List<int> bytes) {
  const fixed = 4 + 1 + 4;
  bool startsWithMagic() {
    for (var i = 0; i < _magic.length; i++) {
      if (bytes[i] != _magic[i]) return false;
    }
    return true;
  }

  if (bytes.length < fixed + 16 || !startsWithMagic() || bytes[4] != _version) {
    throw const DataRuleException('backup_invalid', 'magic');
  }
  final len = ByteData.sublistView(Uint8List.fromList(bytes.sublist(5, 9))).getUint32(0);
  if (len > 4096 || fixed + len + 16 > bytes.length) throw const DataRuleException('backup_invalid', 'header');
  final Object? json;
  try {
    json = jsonDecode(utf8.decode(bytes.sublist(fixed, fixed + len)));
  } on FormatException {
    throw const DataRuleException('backup_invalid', 'header');
  }
  return (
    header: BackupHeader.fromJson(json),
    prefix: bytes.sublist(0, fixed + len),
    cipherText: bytes.sublist(fixed + len, bytes.length - 16),
    mac: bytes.sublist(bytes.length - 16),
  );
}
