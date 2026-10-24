import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/backup/data/backup_providers.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';
import 'package:drift/drift.dart' show driftRuntimeOptions;
import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../integration_test/full_scenario.dart';
import '../helpers/fake_backup_cipher.dart';
import '../helpers/fakes.dart';

/// Yakuniy E2E ssenariy host'da (in-memory baza, soxta shifr). Qurilmadagi
/// varianti — `integration_test/full_e2e_test.dart` (SQLCipher, AES-GCM).
void main() {
  test('Akmal ssenariysi + zaxiradan 1:1 tiklash', () async {
    driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
    final clock = FakeClock();
    final meta = SyncMetaFactory(UuidV7Generator(clock: clock), clock);
    AppDatabase open() =>
        AppDatabase(NativeDatabase.memory(), metaFactory: meta);
    final db = open();
    addTearDown(db.close);
    ProviderContainer containerFor(AppDatabase d) {
      final c = ProviderContainer(
        overrides: [
          appDatabaseProvider.overrideWith((ref) async => d),
          clockProvider.overrideWithValue(clock),
          secureBlobStoreProvider.overrideWithValue(InMemorySecureBlobStore()),
          pinHasherProvider.overrideWithValue(ReferencePinHasher()),
          backupCipherProvider.overrideWithValue(FakeCipher()),
        ],
      );
      addTearDown(c.dispose);
      return c;
    }

    final c = containerFor(db);
    final steps = <String>[];
    final result = await runFullScenario(
      c,
      now: clock.nowUtc(),
      log: steps.add,
    );
    expect(steps, hasLength(14));

    final file = await (await c.read(
      backupServiceProvider.future,
    )).export('Akmal-zaxira-2026');
    final fresh = open();
    addTearDown(fresh.close);
    final restored = BackupService(fresh, FakeCipher(), clock);
    await restored.import(file, 'Akmal-zaxira-2026');
    final after = await restored.dump();
    for (final t in result.dump.keys) {
      expect(after[t], result.dump[t], reason: t);
    }
  });
}
