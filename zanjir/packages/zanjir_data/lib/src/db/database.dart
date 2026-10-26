import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'converters.dart';
import 'tables.dart';

part 'database.g.dart';

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
    AuditEvents,
    IsolationPlans,
    NormSets,
  ],
  include: {'triggers.drift'},
)
class ZanjirDatabase extends _$ZanjirDatabase {
  ZanjirDatabase(super.e);

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) => m.createAll(),
    onUpgrade: (m, from, to) async {
      // Yangi versiyalar shu yerga `stepByStep` bilan qo'shiladi.
      if (from > to) throw StateError('Bazani pastga tushirish mumkin emas: $from → $to');
      throw StateError('Noma\'lum migratsiya: $from → $to');
    },
    beforeOpen: (details) async {
      await customStatement('PRAGMA foreign_keys = ON');
    },
  );
}
