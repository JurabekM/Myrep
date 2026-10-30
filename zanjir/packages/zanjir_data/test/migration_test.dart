import 'package:drift/native.dart';
import 'package:drift_dev/api/migrations_native.dart';
import 'package:test/test.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'drift/zanjir/generated/schema.dart';

void main() {
  late SchemaVerifier verifier;
  setUpAll(() => verifier = SchemaVerifier(GeneratedHelper()));

  test('joriy sxema versiyasi eksport qilingan oxirgi sxemaga teng', () {
    final db = ZanjirDatabase(NativeDatabase.memory());
    addTearDown(db.close);
    expect(
      db.schemaVersion,
      GeneratedHelper.versions.last,
      reason: 'sxema o\'zgarsa: dart run drift_dev make-migrations',
    );
  });

  test('yangi baza eksport qilingan sxemaga (jadvallar, triggerlar, indekslar) aynan mos', () async {
    final connection = await verifier.startAt(GeneratedHelper.versions.last);
    final db = ZanjirDatabase(connection);
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, db.schemaVersion);
  });

  for (final from in GeneratedHelper.versions) {
    test('migratsiya v$from → joriy versiya', () async {
      final connection = await verifier.startAt(from);
      final db = ZanjirDatabase(connection);
      addTearDown(db.close);
      await verifier.migrateAndValidate(db, db.schemaVersion);
    });
  }

  test('pastga tushirish (yangiroq versiyadagi baza) rad etiladi', () async {
    final raw = NativeDatabase.memory(setup: (db) => db.execute('PRAGMA user_version = 99'));
    final db = ZanjirDatabase(raw);
    addTearDown(db.close);
    await expectLater(db.customSelect('select 1').get(), throwsA(isA<StateError>()));
  });

  test('foreign key tekshiruvi yoqilgan, append-only triggerlar mavjud', () async {
    final db = ZanjirDatabase(NativeDatabase.memory());
    addTearDown(db.close);
    final fk = await db.customSelect('PRAGMA foreign_keys').getSingle();
    expect(fk.data.values.single, 1);
    final triggers = await db
        .customSelect(
          "select name from sqlite_master where type = 'trigger' and name like '%append_only%' order by name",
        )
        .map((r) => r.read<String>('name'))
        .get();
    expect(triggers, [
      for (final t in ['audit_event', 'measurement', 'protocol', 'protocol_document']) ...[
        '${t}_append_only_delete',
        '${t}_append_only_update',
      ],
    ]);
    await expectLater(
      db
          .into(db.sites)
          .insert(
            SitesCompanion.insert(
              id: 's',
              orgId: 'mavjud-emas',
              name: 'x',
              createdAt: DateTime.utc(2026),
              updatedAt: DateTime.utc(2026),
            ),
          ),
      throwsA(isA<SqliteException>()),
    );
  });
}
