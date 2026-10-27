import 'dart:ffi';
import 'dart:io';
import 'dart:typed_data';

import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/connection.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:drift/drift.dart' hide isNull;
import 'package:flutter_test/flutter_test.dart';
import 'package:sqlite3/open.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../helpers/fakes.dart';

/// Hostʼdagi SQLCipher kutubxonasi: Linux CIʼda `libsqlcipher-dev`,
/// boshqa joyda `SQLCIPHER_LIBRARY` muhit oʻzgaruvchisi. Topilmasa,
/// shifrlash testi oʻtkazib yuboriladi — u qurilmada
/// `integration_test/encrypted_db_test.dart` bilan baribir tekshiriladi.
String? _sqlcipherPath() {
  final explicit = Platform.environment['SQLCIPHER_LIBRARY'];
  if (explicit != null && File(explicit).existsSync()) return explicit;
  if (Platform.isLinux) {
    for (final dir in ['/usr/lib/x86_64-linux-gnu', '/usr/lib', '/lib']) {
      for (final name in ['libsqlcipher.so.0', 'libsqlcipher.so']) {
        if (File('$dir/$name').existsSync()) return '$dir/$name';
      }
    }
  }
  return null;
}

Uint8List _key(int seed) => Uint8List.fromList(
  List<int>.generate(32, (i) => (i * 7 + seed) & 0xFF),
);

void main() {
  test(
    'SQLCipher yuklanmagan boʻlsa baza ochilmaydi (shifrsizga tushmaydi)',
    () {
      // Oddiy sqlite: `cipher_version` boʻsh.
      final plain = sqlite3.openInMemory();
      addTearDown(plain.dispose);
      if (plain.select('PRAGMA cipher_version;').isNotEmpty) {
        markTestSkipped('Joriy kutubxona SQLCipher — bu holat tekshirilmaydi');
        return;
      }
      expect(
        () => applyCipherKey(plain, keyPragma(_key(1))),
        throwsA(isA<StateError>()),
      );
    },
  );

  test('kalit 32 bayt boʻlishi shart', () {
    expect(
      () => openEncryptedDatabase(file: File('x'), key: Uint8List(16)),
      throwsArgumentError,
    );
  });

  test('pragma xom kalit formatida', () {
    expect(
      keyPragma(Uint8List.fromList(List.filled(32, 0xAB))),
      'PRAGMA key = "x\'${'ab' * 32}\'";',
    );
  });

  final cipher = _sqlcipherPath();
  group(
    'SQLCipher (host)',
    () {
      late Directory dir;
      late File file;

      setUpAll(() {
        open
          ..overrideFor(
            OperatingSystem.linux,
            () => DynamicLibrary.open(cipher!),
          )
          ..overrideFor(
            OperatingSystem.windows,
            () => DynamicLibrary.open(cipher!),
          );
      });

      setUp(() async {
        dir = await Directory.systemTemp.createTemp('baraka_cipher');
        file = File('${dir.path}/baraka.sqlite');
        final clock = FakeClock();
        final db = AppDatabase(
          openEncryptedDatabase(file: file, key: _key(1), inBackground: false),
          metaFactory: SyncMetaFactory(UuidV7Generator(clock: clock), clock),
        );
        await db.select(db.categories).get(); // yaratish + seed
        await db.close();
      });

      tearDown(() => dir.delete(recursive: true));

      test('fayl sarlavhasi oddiy SQLite emas', () {
        final header = file.readAsBytesSync().sublist(0, 16);
        expect(
          String.fromCharCodes(header),
          isNot(startsWith('SQLite format 3')),
        );
      });

      test('kalitsiz ochib boʻlmaydi', () {
        final raw = sqlite3.open(file.path);
        addTearDown(raw.dispose);
        expect(
          () => raw.select('SELECT count(*) FROM categories'),
          throwsA(isA<SqliteException>()),
        );
      });

      test('notoʻgʻri kalit bilan ochib boʻlmaydi', () {
        final raw = sqlite3.open(file.path);
        addTearDown(raw.dispose);
        expect(
          () => applyCipherKey(raw, keyPragma(_key(2))),
          throwsA(isA<SqliteException>()),
        );
      });

      test('toʻgʻri kalit bilan maʼlumot oʻqiladi', () {
        final raw = sqlite3.open(file.path);
        addTearDown(raw.dispose);
        applyCipherKey(raw, keyPragma(_key(1)));
        expect(
          raw.select('SELECT count(*) AS n FROM categories').first['n'],
          11,
        );
      });
    },
    skip: cipher == null
        ? 'SQLCipher hostʼda yoʻq — qurilmada integration_test tekshiradi'
        : false,
  );
}
