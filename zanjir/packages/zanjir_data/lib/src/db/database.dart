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
);

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
  int get schemaVersion => 3;

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
