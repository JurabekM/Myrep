import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'context.dart';
import 'site_repository.dart';
import 'user_repository.dart';

class SessionRepository {
  SessionRepository(this._ctx);
  final DataContext _ctx;
  ZanjirDatabase get _db => _ctx.db;

  Future<MeasurementSessionRow> start({
    required String siteId,
    required SessionKind kind,
    required String engineerId,
    double? ambientTempC,
    double? humidityPct,
  }) async {
    await SiteRepository(_ctx).require(siteId);
    await UserRepository(_ctx).require(engineerId);
    final now = _ctx.now();
    return _db
        .into(_db.measurementSessions)
        .insertReturning(
          MeasurementSessionsCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            siteId: siteId,
            kind: kind,
            engineerId: engineerId,
            ambientTempC: Value(ambientTempC),
            humidityPct: Value(humidityPct),
            startedAt: now,
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<MeasurementSessionRow?> get(String id) => (_db.select(
    _db.measurementSessions,
  )..where((s) => s.id.equals(id) & s.orgId.equals(_ctx.orgId) & s.deleted.equals(false))).getSingleOrNull();

  Future<MeasurementSessionRow> require(String id) async =>
      await get(id) ?? (throw NotFoundException('measurement_session', id));

  /// Ochiq sessiya; yopilgan bo'lsa — `session_closed`.
  Future<MeasurementSessionRow> requireOpen(String id) async {
    final s = await require(id);
    if (s.closedAt != null) throw DataRuleException('session_closed', id);
    return s;
  }

  Future<List<MeasurementSessionRow>> forSite(String siteId) =>
      (_db.select(_db.measurementSessions)
            ..where((s) => s.siteId.equals(siteId) & s.orgId.equals(_ctx.orgId) & s.deleted.equals(false))
            ..orderBy([(s) => OrderingTerm(expression: s.startedAt)]))
          .get();

  /// Harorat va namlik — faqat ochiq sessiyada.
  Future<MeasurementSessionRow> updateConditions(
    String id, {
    Value<double?> ambientTempC = const Value.absent(),
    Value<double?> humidityPct = const Value.absent(),
  }) async {
    final s = await requireOpen(id);
    final row = s.copyWith(
      ambientTempC: ambientTempC.present ? ambientTempC : Value(s.ambientTempC),
      humidityPct: humidityPct.present ? humidityPct : Value(s.humidityPct),
      updatedAt: _ctx.now(),
      rev: s.rev + 1,
    );
    await _db.update(_db.measurementSessions).replace(row);
    return row;
  }

  Future<MeasurementSessionRow> close(String id) async {
    final s = await requireOpen(id);
    final now = _ctx.now();
    final row = s.copyWith(closedAt: Value(now), updatedAt: now, rev: s.rev + 1);
    await _db.update(_db.measurementSessions).replace(row);
    return row;
  }
}
