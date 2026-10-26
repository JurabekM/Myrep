import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:drift_dev/api/migrations_native.dart';
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'generated/schema.dart';

/// v1 → v2 migratsiyasi: mavjud ma'lumot (append-only jadvallar ham) o'zgarmaydi, triggerlar ishlaydi,
/// yangi jadvallar ishlatiladi.
void main() {
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
  late SchemaVerifier verifier;
  setUpAll(() => verifier = SchemaVerifier(GeneratedHelper()));

  test('v1 ma\'lumotlari bilan v2 ga migratsiya', () async {
    final schema = await verifier.schemaAt(1);
    const t = "'2026-10-26T07:00:00.000Z'";
    for (final sql in [
      "insert into organization (id, name, created_at, updated_at) values ('org', 'Lab', $t, $t)",
      "insert into app_user (id, org_id, full_name, phone, role, created_at, updated_at) values ('u', 'org', 'M', '+998', 'LEAD', $t, $t)",
      "insert into device (id, org_id, user_id, public_key_ed25519, sig_alg, registered_at, created_at, updated_at) values ('d', 'org', 'u', 'aa', 'Ed25519', $t, $t, $t)",
      "insert into instrument (id, org_id, kind, model, serial_no, created_at, updated_at) values ('i', 'org', 'K', 'M', 'S', $t, $t)",
      "insert into site (id, org_id, name, earthing_system, u0_volts, created_at, updated_at) values ('s', 'org', 'Obyekt', 'TN-S', 220, $t, $t)",
      "insert into node (id, org_id, site_id, kind, label, attrs, created_at, updated_at) values ('n', 'org', 's', 'CABLE', 'W1', '{\"length_m\":22}', $t, $t)",
      "insert into measurement_session (id, org_id, site_id, kind, engineer_id, started_at, created_at, updated_at) values ('ms', 'org', 's', 'DAVRIY', 'u', $t, $t, $t)",
      "insert into measurement (id, org_id, session_id, node_id, type, instrument_id, \"values\", entered_via, verdict, norm_set_version, eval_detail, created_at, updated_at) values ('m', 'org', 'ms', 'n', 'CONTINUITY_BONDING', 'i', '{\"r_ohm\":0.03}', 'MANUAL', 'PASS', '0.1.0', '{}', $t, $t)",
      "insert into audit_event (id, org_id, device_id, seq, prev_hash, event_hash, actor_id, event_type, payload_hash, device_sig, sig_alg, event_at, created_at, updated_at) values ('a', 'org', 'd', 1, 'p', 'e', 'u', 'X', 'h', 's', 'Ed25519', $t, $t, $t)",
    ]) {
      schema.rawDatabase.execute(sql);
    }

    final db = ZanjirDatabase(schema.newConnection());
    addTearDown(db.close);
    await verifier.migrateAndValidate(db, 2);

    final m = await db.select(db.measurements).getSingle();
    expect((m.id, m.verdict, m.normSetVersion), ('m', Verdict.pass, '0.1.0'));
    expect(m.values, {'r_ohm': 0.03});
    expect((await db.select(db.nodes).getSingle()).attrs, {'length_m': 22});
    expect((await db.select(db.auditEvents).getSingle()).eventHash, 'e');
    await expectLater(db.customUpdate("delete from measurement where id = 'm'"), throwsA(isA<SqliteException>()));
    await expectLater(db.customUpdate('update audit_event set seq = 2'), throwsA(isA<SqliteException>()));

    // Yangi jadvallar.
    final ctx = DataContext(db: db, orgId: 'org');
    expect((await SettingsRepository(ctx).current()).kCorr, 1.0);
    await LocalPrefRepository(db).set('ui.locale', 'ru');
    expect(await LocalPrefRepository(db).get('ui.locale'), 'ru');
  });
}
