import 'dart:convert';
import 'dart:typed_data';

import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';

/// Test shifri: parol tekshiriladi, mazmun aylantiriladi (haqiqiy AES-GCM —
/// Kotlin `BackupCipherTest`).
class FakeCipher implements BackupCipher {
  @override
  Future<Uint8List> encrypt(String password, Uint8List plain) async =>
      Uint8List.fromList([
        ...utf8.encode(password),
        0,
        ...plain.reversed,
      ]);

  @override
  Future<Uint8List> decrypt(String password, Uint8List data) async {
    final prefix = [...utf8.encode(password), 0];
    if (data.length < prefix.length ||
        !_eq(data.sublist(0, prefix.length), prefix)) {
      throw const DomainRuleException(BackupService.errBadPassword);
    }
    return Uint8List.fromList(data.sublist(prefix.length).reversed.toList());
  }

  static bool _eq(List<int> a, List<int> b) {
    for (var i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }
}
