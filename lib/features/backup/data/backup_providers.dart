import 'dart:typed_data';

import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:share_plus/share_plus.dart';

part 'backup_providers.g.dart';

@Riverpod(keepAlive: true)
BackupCipher backupCipher(Ref ref) =>
    NativeBackupCipher(ref.watch(securityApiProvider));

@Riverpod(keepAlive: true)
Future<BackupService> backupService(Ref ref) async => BackupService(
  await ref.watch(appDatabaseProvider.future),
  ref.watch(backupCipherProvider),
  ref.watch(clockProvider),
);

/// Shifrlangan faylni foydalanuvchiga berish (ulashish oynasi: Fayllar,
/// Telegram «Saqlangan», Drive). Testlarda almashtiriladi.
typedef BackupSaver = Future<void> Function(Uint8List bytes, String fileName);

/// Zaxira faylini tanlash (`null` — bekor qilindi).
typedef BackupPicker = Future<Uint8List?> Function();

@Riverpod(keepAlive: true)
BackupSaver backupSaver(Ref ref) =>
    (bytes, fileName) => SharePlus.instance.share(
      ShareParams(
        files: [
          XFile.fromData(
            bytes,
            mimeType: 'application/octet-stream',
            name: fileName,
          ),
        ],
        fileNameOverrides: [fileName],
      ),
    );

@Riverpod(keepAlive: true)
BackupPicker backupPicker(Ref ref) =>
    ref.watch(securityApiProvider).pickBackupFile;
