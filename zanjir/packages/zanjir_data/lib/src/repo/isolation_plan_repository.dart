import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'context.dart';
import 'graph_repository.dart';
import 'site_repository.dart';
import 'settings_repository.dart';

/// Ajratish rejalari: DRAFT → APPROVED → EXECUTED; DRAFT/APPROVED → CANCELLED; graf o'zgarsa → STALE.
/// Reja — tavsiya; tasdiqlash LEAD/ADMIN zimmasida (CLAUDE.md, 1-qoida).
class IsolationPlanRepository {
  IsolationPlanRepository(this._ctx);
  final DataContext _ctx;
  ZanjirDatabase get _db => _ctx.db;

  static const _approverRoles = {'LEAD', 'ADMIN'};

  Future<IsolationPlanRow> save({required String siteId, required IsolationPlan plan}) async {
    if (plan.graphSnapshotHash != await _currentHash(siteId)) throw const DataRuleException('plan_stale');
    final now = _ctx.now();
    final json = plan.toJson();
    return _db
        .into(_db.isolationPlans)
        .insertReturning(
          IsolationPlansCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            siteId: siteId,
            targetNodeIds: plan.targetNodeIds,
            solverVersion: plan.solverVersion,
            graphSnapshotHash: plan.graphSnapshotHash,
            steps: json['steps']! as List<Object?>,
            warnings: json['warnings']! as List<Object?>,
            status: 'DRAFT',
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<IsolationPlanRow?> get(String id) => (_db.select(
    _db.isolationPlans,
  )..where((p) => p.id.equals(id) & p.orgId.equals(_ctx.orgId) & p.deleted.equals(false))).getSingleOrNull();

  Future<IsolationPlanRow> approve(String id, {required String approvedBy}) async {
    final plan = await _require(id);
    _expectStatus(plan, const {'DRAFT'});
    await requireRole(_ctx, approvedBy, _approverRoles);
    await _ensureFresh(plan);
    return _setStatus(plan, 'APPROVED', approvedBy: Value(approvedBy));
  }

  Future<IsolationPlanRow> execute(String id) async {
    final plan = await _require(id);
    _expectStatus(plan, const {'APPROVED'});
    await _ensureFresh(plan);
    return _setStatus(plan, 'EXECUTED');
  }

  Future<IsolationPlanRow> cancel(String id) async {
    final plan = await _require(id);
    _expectStatus(plan, const {'DRAFT', 'APPROVED'});
    return _setStatus(plan, 'CANCELLED');
  }

  /// Graf (yoki yerga ulash tizimi) o'zgargan DRAFT/APPROVED rejalarni STALE qiladi; ularning ID'lari.
  Future<List<String>> refreshStale(String siteId) async {
    final hash = await _currentHash(siteId);
    final active =
        await (_db.select(_db.isolationPlans)..where(
              (p) =>
                  p.siteId.equals(siteId) &
                  p.orgId.equals(_ctx.orgId) &
                  p.deleted.equals(false) &
                  p.status.isIn(const ['DRAFT', 'APPROVED']),
            ))
            .get();
    final stale = [
      for (final p in active)
        if (p.graphSnapshotHash != hash) p,
    ];
    for (final p in stale) {
      await _setStatus(p, 'STALE');
    }
    return [for (final p in stale) p.id];
  }

  Future<void> _ensureFresh(IsolationPlanRow plan) async {
    if (plan.graphSnapshotHash != await _currentHash(plan.siteId)) {
      await _setStatus(plan, 'STALE');
      throw DataRuleException('plan_stale', plan.id);
    }
  }

  Future<String> _currentHash(String siteId) async {
    final site = await SiteRepository(_ctx).require(siteId);
    final graph = await GraphRepository(_ctx).loadGraph(siteId);
    return graphSnapshotHash(graph, earthingSystem: site.earthingSystem);
  }

  Future<IsolationPlanRow> _require(String id) async =>
      await get(id) ?? (throw NotFoundException('isolation_plan', id));

  void _expectStatus(IsolationPlanRow plan, Set<String> allowed) {
    if (!allowed.contains(plan.status)) throw DataRuleException('invalid_transition', '${plan.status} (${plan.id})');
  }

  Future<IsolationPlanRow> _setStatus(
    IsolationPlanRow plan,
    String status, {
    Value<String?> approvedBy = const Value.absent(),
  }) async {
    final row = plan.copyWith(
      status: status,
      approvedBy: approvedBy.present ? approvedBy : Value(plan.approvedBy),
      updatedAt: _ctx.now(),
      rev: plan.rev + 1,
    );
    await _db.update(_db.isolationPlans).replace(row);
    return row;
  }
}
