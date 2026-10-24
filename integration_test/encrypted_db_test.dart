// Qurilmada (emulyator yoki telefon) ishga tushiriladi:
//   flutter test integration_test/encrypted_db_test.dart -d <qurilma>
//
// Haqiqiy zanjir: Kotlin Keystore → getOrCreateDatabaseKey → SQLCipher
// (sqlcipher_flutter_libs) → Drift. Kickoff Vazifa 3 qabul mezoni:
// «Shifrlangan DB faylini kalitsiz ochib bo'lmasligi tekshirilgan».
import 'dart:io';
import 'dart:typed_data';

import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/connection.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqlite3/sqlite3.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late Directory dir;
  late File file;

  setUpAll(() async {
    useSqlCipherOnAndroid();
    final base = await getTemporaryDirectory();
    dir = await Directory('${base.path}/enc_test').create(recursive: true);
    file = File('${dir.path}/test.sqlite');
    if (file.existsSync()) file.deleteSync();
  });

  tearDownAll(() => dir.delete(recursive: true));

  AppDatabase openWith(Uint8List key) => AppDatabase(
    openEncryptedDatabase(file: file, key: key),
    metaFactory: SyncMetaFactory(
      UuidV7Generator(clock: const SystemClock()),
      const SystemClock(),
    ),
  );

  testWidgets('Keystore kaliti barqaror va 32 bayt', (tester) async {
    final api = SecurityApi();
    final a = await api.getOrCreateDatabaseKey();
    final b = await api.getOrCreateDatabaseKey();
    expect(a, hasLength(32));
    expect(b, a);
  });

  testWidgets('SQLCipher yuklangan', (tester) async {
    final raw = sqlite3.openInMemory();
    addTearDown(raw.dispose);
    final v = raw.select('PRAGMA cipher_version;');
    expect(v, isNotEmpty);
  });

  testWidgets("shifrlangan baza: to'g'ri kalit bilan ochiladi", (
    tester,
  ) async {
    final key = await SecurityApi().getOrCreateDatabaseKey();
    final db = openWith(key);
    expect(
      await db.select(db.categories).get(),
      hasLength(CategoryKey.values.length),
    );
    await db.close();

    // Qayta ochish — ma'lumot saqlangan.
    final again = openWith(await SecurityApi().getOrCreateDatabaseKey());
    expect(
      await again.select(again.categories).get(),
      hasLength(CategoryKey.values.length),
    );
    await again.close();
  });

  testWidgets('fayl sarlavhasi oddiy SQLite emas', (tester) async {
    final header = file.readAsBytesSync().sublist(0, 16);
    expect(
      String.fromCharCodes(header),
      isNot(startsWith('SQLite format 3')),
    );
  });

  testWidgets("kalitsiz ochib bo'lmaydi", (tester) async {
    final raw = sqlite3.open(file.path);
    addTearDown(raw.dispose);
    expect(
      () => raw.select('SELECT count(*) FROM categories'),
      throwsA(isA<SqliteException>()),
    );
  });

  testWidgets("noto'g'ri kalit bilan ochib bo'lmaydi", (tester) async {
    final raw = sqlite3.open(file.path);
    addTearDown(raw.dispose);
    final wrong = Uint8List(32)..fillRange(0, 32, 7);
    expect(
      () => applyCipherKey(raw, keyPragma(wrong)),
      throwsA(isA<SqliteException>()),
    );
  });
}
