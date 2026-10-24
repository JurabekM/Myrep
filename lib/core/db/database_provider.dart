import 'dart:io';
import 'dart:typed_data';

import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/connection.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:drift/drift.dart' show QueryExecutor;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'database_provider.g.dart';

/// Baza fayli: `<app support>/db/baraka.sqlite` (backup'dan chiqarilgan).
@Riverpod(keepAlive: true)
Future<File> databaseFile(Ref ref) async {
  final dir = await getApplicationSupportDirectory();
  return File(p.join(dir.path, 'db', 'baraka.sqlite'));
}

/// Shifrlangan baza. Kalit Kotlin'dan (Keystore bilan wrap qilingan)
/// olinadi va baza ochilgach xotiradagi nusxasi tozalanadi.
@Riverpod(keepAlive: true)
Future<AppDatabase> appDatabase(Ref ref) async {
  // Platforma kanalidan kelgan ro'yxat o'zgarmas (unmodifiable) — uni
  // tozalab bo'lmaydi, shuning uchun o'zimizning nusxa bilan ishlaymiz.
  // (Qurilmada topilgan xato: fillRange «Cannot modify an unmodifiable list».)
  final key = Uint8List.fromList(
    await ref.watch(securityApiProvider).getOrCreateDatabaseKey(),
  );
  final file = await ref.watch(databaseFileProvider.future);
  await file.parent.create(recursive: true);
  final QueryExecutor executor;
  try {
    executor = openEncryptedDatabase(file: file, key: key);
  } finally {
    key.fillRange(0, key.length, 0);
  }
  final db = AppDatabase(
    executor,
    metaFactory: ref.watch(syncMetaFactoryProvider),
  );
  ref.onDispose(db.close);
  return db;
}
