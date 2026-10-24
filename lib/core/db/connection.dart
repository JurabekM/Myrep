import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:sqlcipher_flutter_libs/sqlcipher_flutter_libs.dart';
import 'package:sqlite3/open.dart';
import 'package:sqlite3/sqlite3.dart';

/// SQLCipher bilan shifrlangan bazani ochadi (SPEC 4.5).
///
/// * Kalit — 32 baytlik xom kalit (`PRAGMA key = "x'…'"`), PBKDF talab
///   qilinmaydi: u allaqachon tasodifiy va Keystore'da wrap qilingan.
/// * SQLCipher yuklanmagan bo'lsa (`cipher_version` bo'sh) baza **ochilmaydi**
///   — jimgina shifrlanmagan bazaga tushib qolish oldi olinadi.
/// * Kalit noto'g'ri bo'lsa birinchi so'rovdayoq xato beradi.
QueryExecutor openEncryptedDatabase({
  required File file,
  required Uint8List key,
  bool inBackground = true,
}) {
  if (key.length != 32) throw ArgumentError("Kalit 32 bayt bo'lishi kerak");
  final pragma = keyPragma(key);
  void setup(Database db) => applyCipherKey(db, pragma);
  return inBackground
      ? NativeDatabase.createInBackground(
          file,
          isolateSetup: useSqlCipherOnAndroid,
          setup: setup,
        )
      : NativeDatabase(file, setup: setup);
}

/// Android'da tizim sqlite o'rniga ilova bilan keladigan SQLCipher.
void useSqlCipherOnAndroid() {
  open.overrideFor(OperatingSystem.android, openCipherOnAndroid);
}

String keyPragma(Uint8List key) {
  final hex = key.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return 'PRAGMA key = "x\'$hex\'";';
}

/// Testlarda ham ishlatiladi.
void applyCipherKey(Database db, String pragma) {
  final version = db.select('PRAGMA cipher_version;');
  if (version.isEmpty || (version.first.values.first as String?) == null) {
    throw StateError('SQLCipher yuklanmagan — shifrsiz baza ochilmaydi');
  }
  db
    ..execute(pragma)
    // Kalitni darhol tekshirish: noto'g'ri bo'lsa «file is not a database».
    ..select('SELECT count(*) FROM sqlite_master;');
}
