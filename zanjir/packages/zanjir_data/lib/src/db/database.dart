import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'converters.dart';
import 'database.steps.dart';
import 'tables.dart';

part 'database.g.dart';

/// Versiyalangan migratsiya qadamlari (`drift_dev make-migrations`, ADR-0008). Har bir qadam faqat qo'shadi —
/// append-only jadvallardagi ma'lumot o'zgartirilmaydi.
final OnUpgrade _steps = stepByStep(
  from1To2: (m, schema) async {
    // 5-faza: laboratoriya sozlamalari va qurilma sozlamalari (ADR-0009).
    await m.createTable(schema.orgSetting);
    await m.createTable(schema.localPref);
  },
  from2To3: (m, schema) async {
    // 6-faza: imzolangan protokol hujjati (payload + PDF), append-only (ADR-0010).
    await m.createTable(schema.protocolDocument);
    await m.createTrigger(schema.protocolDocumentAppendOnlyUpdate);
    await m.createTrigger(schema.protocolDocumentAppendOnlyDelete);
  },
  from3To4: (m, schema) async {
    // 8-faza: sinxronlash navbati (ADR-0012). Mavjud ma'lumot ham navbatga qo'yiladi (hali serverga yuborilmagan).
    await m.createTable(schema.syncOutbox);
    for (final t in [
      schema.organizationOutboxIns,
      schema.organizationOutboxUpd,
      schema.instrumentOutboxIns,
      schema.instrumentOutboxUpd,
      schema.siteOutboxIns,
      schema.siteOutboxUpd,
      schema.nodeOutboxIns,
      schema.nodeOutboxUpd,
      schema.edgeOutboxIns,
      schema.edgeOutboxUpd,
      schema.measurementSessionOutboxIns,
      schema.measurementSessionOutboxUpd,
      schema.measurementOutboxIns,
      schema.protocolOutboxIns,
      schema.protocolDocumentOutboxIns,
      schema.auditEventOutboxIns,
      schema.isolationPlanOutboxIns,
      schema.isolationPlanOutboxUpd,
      schema.normSetOutboxIns,
      schema.normSetOutboxUpd,
      schema.orgSettingOutboxIns,
      schema.orgSettingOutboxUpd,
    ]) {
      await m.createTrigger(t);
    }
    for (final (table, order) in outboxBackfillOrder) {
      await m.database.customStatement(
        'INSERT OR IGNORE INTO sync_outbox (table_name, row_id, op_id) '
        "SELECT '$table', id, lower(hex(randomblob(16))) FROM $table ORDER BY $order",
      );
    }
  },
  from4To5: (m, schema) async {
    // 13-faza: ilova to'liq oflayn (ADR-0017) — sinxronlash navbati, uning triggerlari va kursorlari o'chiriladi.
    // Ma'lumot jadvallariga (ayniqsa append-only) tegilmaydi.
    for (final trigger in outboxTriggers) {
      await m.database.customStatement('DROP TRIGGER IF EXISTS $trigger');
    }
    await m.database.customStatement('DROP TABLE IF EXISTS sync_outbox');
    await m.database.customStatement("DELETE FROM local_pref WHERE \"key\" LIKE 'sync.%'");
  },
);

/// v4 dagi sinxronlash navbati triggerlari (v5 da o'chiriladi).
final outboxTriggers = [
  for (final t in [
    'organization',
    'instrument',
    'site',
    'node',
    'edge',
    'measurement_session',
    'isolation_plan',
    'norm_set',
    'org_setting',
  ])
    for (final op in ['ins', 'upd']) '${t}_outbox_$op',
  for (final t in ['measurement', 'protocol', 'protocol_document', 'audit_event']) '${t}_outbox_ins',
];

/// Navbatga qo'yiladigan jadvallar (ota jadvallar birinchi) va ichki tartib.
const outboxBackfillOrder = [
  ('organization', 'created_at'),
  ('norm_set', 'created_at'),
  ('org_setting', 'created_at'),
  ('instrument', 'created_at'),
  ('site', 'created_at'),
  ('node', 'created_at'),
  ('edge', 'created_at'),
  ('measurement_session', 'created_at'),
  ('audit_event', 'seq'),
  ('measurement', 'created_at'),
  ('protocol', 'created_at'),
  ('protocol_document', 'created_at'),
  ('isolation_plan', 'created_at'),
];

/// ZANJIR lokal bazasi — qurilmadagi asosiy manba (offline-first).
/// Sxema versiyasi o'zgarsa: `dart run drift_dev make-migrations` va migratsiya testi (ADR-0008).
@DriftDatabase(
  tables: [
    Organizations,
    AppUsers,
    Devices,
    Instruments,
    Sites,
    Nodes,
    Edges,
    MeasurementSessions,
    Measurements,
    Protocols,
    ProtocolDocuments,
    AuditEvents,
    IsolationPlans,
    NormSets,
    OrgSettings,
    LocalPrefs,
  ],
  include: {'triggers.drift'},
)
class ZanjirDatabase extends _$ZanjirDatabase {
  ZanjirDatabase(super.e);

  @override
  int get schemaVersion => 5;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) => m.createAll(),
    onUpgrade: (m, from, to) async {
      if (from > to) throw StateError('Bazani pastga tushirish mumkin emas: $from → $to');
      await _steps(m, from, to);
    },
    beforeOpen: (details) async {
      await customStatement('PRAGMA foreign_keys = ON');
    },
  );
}
