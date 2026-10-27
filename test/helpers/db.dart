import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes.dart';

/// In-memory Drift bazasi (kickoff Vazifa 3: repository testlari).
class TestDb {
  TestDb._(this.db, this.clock, this.meta);

  factory TestDb.open() {
    driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
    final clock = FakeClock();
    final meta = SyncMetaFactory(UuidV7Generator(clock: clock), clock);
    final db = AppDatabase(NativeDatabase.memory(), metaFactory: meta);
    addTearDown(db.close);
    return TestDb._(db, clock, meta);
  }

  final AppDatabase db;
  final FakeClock clock;
  final SyncMetaFactory meta;

  Future<String> householdId() async =>
      (await db.select(db.households).getSingle()).id;
}
