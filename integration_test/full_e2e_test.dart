// Yakuniy E2E (MVP_PLAN Vazifa 15) qurilmada:
//   flutter build apk --release --target-platform android-x64 \
//     -t integration_test/full_e2e_test.dart
//   adb install -r ...; adb shell am start ...; adb logcat -s flutter:I
//
// Haqiqiy zanjir: Keystore kaliti → SQLCipher bazasi (alohida vaqtinchalik
// fayl, ilovaning asosiy bazasiga tegmaydi) → ilova provayderlari va
// servislari → Kotlin BackupCipher (PBKDF2-HMAC-SHA256 310 000 + AES-256-GCM)
// → ikkinchi shifrlangan bazaga 1:1 tiklash.
import 'dart:io';

import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/connection.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/backup/data/backup_providers.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';

import 'full_scenario.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late Directory dir;

  setUpAll(() async {
    useSqlCipherOnAndroid();
    final base = await getTemporaryDirectory();
    dir = Directory('${base.path}/e2e_full');
    if (dir.existsSync()) dir.deleteSync(recursive: true);
    await dir.create(recursive: true);
  });

  tearDownAll(() => dir.delete(recursive: true));

  Future<AppDatabase> openEncrypted(String name) async {
    final key = Uint8List.fromList(
      await SecurityApi().getOrCreateDatabaseKey(),
    );
    const clock = SystemClock();
    return AppDatabase(
      openEncryptedDatabase(file: File('${dir.path}/$name'), key: key),
      metaFactory: SyncMetaFactory(UuidV7Generator(clock: clock), clock),
    );
  }

  testWidgets('Akmal: boshidan oxirigacha, shifrlangan zaxira va tiklash', (
    tester,
  ) async {
    final db = await openEncrypted('full.sqlite');
    final c = ProviderContainer(
      overrides: [appDatabaseProvider.overrideWith((ref) async => db)],
    );
    final result = await runFullScenario(
      c,
      now: const SystemClock().nowUtc(),
      log: debugPrint,
    );

    final backup = await c.read(backupServiceProvider.future);
    final sw = Stopwatch()..start();
    final file = await backup.export('Akmal-zaxira-2026');
    debugPrint(
      'E2E: zaxira ${file.length} bayt, shifrlash ${sw.elapsedMilliseconds} ms',
    );
    expect(String.fromCharCodes(file.sublist(0, 4)), 'BRKD');

    // Yangi telefon: boshqa shifrlangan baza.
    final fresh = await openEncrypted('restored.sqlite');
    final restored = BackupService(
      fresh,
      NativeBackupCipher(SecurityApi()),
      const SystemClock(),
    );
    await expectLater(
      restored.import(file, 'notoʻgʻri-parol'),
      throwsA(
        isA<DomainRuleException>().having(
          (e) => e.code,
          'code',
          BackupService.errBadPassword,
        ),
      ),
    );
    final rows = await restored.import(file, 'Akmal-zaxira-2026');
    final after = await restored.dump();
    for (final t in result.dump.keys) {
      expect(after[t], result.dump[t], reason: t);
    }
    debugPrint('E2E: tiklandi $rows qator, ${result.dump.length} jadval 1:1');

    c.dispose();
    await db.close();
    await fresh.close();
  });
}
