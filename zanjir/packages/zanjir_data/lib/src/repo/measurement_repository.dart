import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'audit_repository.dart';
import 'context.dart';
import 'graph_repository.dart';
import 'instrument_repository.dart';
import 'norm_set_repository.dart';
import 'session_repository.dart';
import 'settings_repository.dart';
import 'site_repository.dart';

/// O'lchovlar — append-only (CLAUDE.md, 5-qoida). O'zgartirish yoki o'chirish metodlari yo'q:
/// xato o'lchov `supersedesId` bilan yangi yozuv orqali almashtiriladi.
class MeasurementRepository {
  MeasurementRepository(this._ctx, {required this._audit, required this._normSets});
  final DataContext _ctx;
  final AuditRepository _audit;
  final NormSetRepository _normSets;
  ZanjirDatabase get _db => _ctx.db;

  /// O'lchovni normaga solishtiradi (`evaluate`, laboratoriya sozlamalari bilan), saqlaydi va `MEASUREMENT_ADDED` audit hodisasini yozadi — bitta tranzaksiyada.
  Future<MeasurementRow> record({
    required String sessionId,
    required String nodeId,
    required MeasurementType type,
    required String instrumentId,
    required Map<String, Object?> values,
    required EnteredVia enteredVia,
    required String normSetVersion,
    String? supersedesId,
  }) => _db.transaction(() async {
    final session = await SessionRepository(_ctx).requireOpen(sessionId);
    final graphRepo = GraphRepository(_ctx);
    final node = await graphRepo.getNode(nodeId);
    if (node == null || node.siteId != session.siteId) throw DataRuleException('node_not_in_site', nodeId);
    final instrument =
        await InstrumentRepository(_ctx).get(instrumentId) ?? (throw NotFoundException('instrument', instrumentId));
    final normSet = await _normSets.load(normSetVersion);
    if (supersedesId != null) await _checkSupersede(supersedesId, sessionId, nodeId, type);

    final site = SiteRepository(_ctx);
    final graph = await graphRepo.loadGraph(session.siteId);
    final id = _ctx.newId();
    final measurement = Measurement(
      id: id,
      sessionId: sessionId,
      nodeId: nodeId,
      type: type,
      instrumentId: instrumentId,
      values: values,
      enteredVia: enteredVia,
      supersedesId: supersedesId,
    );
    final result = evaluate(
      measurement: measurement,
      node: graph.node(nodeId)!,
      site: site.toCore(await site.require(session.siteId)),
      session: MeasurementSession(
        id: session.id,
        siteId: session.siteId,
        kind: session.kind,
        engineerId: session.engineerId,
        ambientTempC: session.ambientTempC,
        humidityPct: session.humidityPct,
      ),
      normSet: normSet,
      graph: graph,
      settings: (await SettingsRepository(_ctx).current()).evalSettings,
    );
    final now = _ctx.now();
    final row = await _db
        .into(_db.measurements)
        .insertReturning(
          MeasurementsCompanion.insert(
            id: id,
            orgId: _ctx.orgId,
            sessionId: sessionId,
            nodeId: nodeId,
            type: type,
            instrumentId: instrumentId,
            values: measurement.values,
            enteredVia: enteredVia,
            verdict: result.verdict,
            normId: Value(result.normId),
            normSetVersion: result.normSetVersion,
            // O'lchov paytidagi qiyoslash muddati (6-qoida): asbob keyin qayta qiyoslansa ham bu o'lchov o'sha muddat
            // bo'yicha baholanadi (ADR-0016).
            evalDetail: {...result.detail, instrumentVerifiedUntilKey: _iso(instrument.verifiedUntil)},
            supersedesId: Value(supersedesId),
            createdAt: now,
            updatedAt: now,
          ),
        );
    await _audit.append(eventType: 'MEASUREMENT_ADDED', entityId: id, payload: measurementAuditPayload(row));
    return row;
  });

  Future<MeasurementRow?> get(String id) =>
      (_db.select(_db.measurements)..where((m) => m.id.equals(id) & m.orgId.equals(_ctx.orgId))).getSingleOrNull();

  /// Sessiya o'lchovlari (yaratilish tartibida). Standart — faqat amaldagilari (almashtirilmaganlar).
  Future<List<MeasurementRow>> forSession(String sessionId, {bool includeSuperseded = false}) async {
    final all =
        await (_db.select(_db.measurements)
              ..where((m) => m.sessionId.equals(sessionId) & m.orgId.equals(_ctx.orgId))
              ..orderBy([(m) => OrderingTerm(expression: m.createdAt), (m) => OrderingTerm(expression: m.id)]))
            .get();
    if (includeSuperseded) return all;
    final replaced = {for (final m in all) ?m.supersedesId};
    return [
      for (final m in all)
        if (!replaced.contains(m.id)) m,
    ];
  }

  /// Tugunning barcha o'lchovlari (barcha sessiyalar, eng yangisi birinchi), almashtirilganlari ham.
  Future<List<MeasurementRow>> forNode(String nodeId) =>
      (_db.select(_db.measurements)
            ..where((m) => m.nodeId.equals(nodeId) & m.orgId.equals(_ctx.orgId))
            ..orderBy([(m) => OrderingTerm.desc(m.createdAt), (m) => OrderingTerm.desc(m.id)]))
          .get();

  Future<void> _checkSupersede(String oldId, String sessionId, String nodeId, MeasurementType type) async {
    final old = await get(oldId) ?? (throw NotFoundException('measurement', oldId));
    if (old.sessionId != sessionId || old.nodeId != nodeId || old.type != type) {
      throw DataRuleException('supersede_mismatch', oldId);
    }
    final already = await (_db.select(
      _db.measurements,
    )..where((m) => m.supersedesId.equals(oldId) & m.orgId.equals(_ctx.orgId))).getSingleOrNull();
    if (already != null) throw DataRuleException('already_superseded', oldId);
  }
}

/// `MEASUREMENT_ADDED` audit hodisasining payload'i (hash shu xaritadan hisoblanadi).
Map<String, Object?> measurementAuditPayload(MeasurementRow m) => {
  'id': m.id,
  'session_id': m.sessionId,
  'node_id': m.nodeId,
  'type': m.type.code,
  'instrument_id': m.instrumentId,
  'values': m.values,
  'entered_via': m.enteredVia.code,
  'verdict': m.verdict.code,
  'norm_id': m.normId,
  'norm_set_version': m.normSetVersion,
  'supersedes_id': m.supersedesId,
};

/// `eval_detail` dagi o'lchov paytidagi asbob qiyoslash muddati (ISO UTC yoki null — guvohnomasiz).
const instrumentVerifiedUntilKey = 'instrument_verified_until';

String? _iso(DateTime? t) => t == null ? null : isoUtcMillis(t);
