import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'audit_repository.dart';
import 'context.dart';
import 'graph_repository.dart';
import 'settings_repository.dart';
import 'site_repository.dart';

/// Bajarilgan qadam (audit hodisasidan): kim va qachon.
class StepRecord {
  const StepRecord({required this.order, required this.actorId, required this.at});
  final int order;
  final String actorId;
  final String at;
}

/// Ajratish rejalari (ADR-0006, ADR-0013): DRAFT → APPROVED → (qadamlar ketma-ket) → EXECUTED;
/// DRAFT/APPROVED → CANCELLED; graf o'zgarsa → STALE. Reja — tavsiya; tasdiqlash LEAD/ADMIN zimmasida (CLAUDE.md, 1-qoida).
///
/// Har bir o'tish va bajarilgan qadam — imzolangan audit hodisasi (`PLAN_*`). Qadam hodisasi `entity_id` =
/// `<reja ID>#<tartib>`; payload deterministik (`plan_id`, `order`, `kind`, tasdiq) — sinxronlangan boshqa qurilmalar ham
/// qaysi qadam bajarilganini audit zanjiridan biladi.
class IsolationPlanRepository {
  IsolationPlanRepository(this._ctx, {required this._audit});
  final DataContext _ctx;
  final AuditRepository _audit;
  ZanjirDatabase get _db => _ctx.db;

  static const _fieldRoles = {'ENGINEER', 'LEAD', 'ADMIN'};

  Future<IsolationPlanRow> save({required String siteId, required IsolationPlan plan}) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, _fieldRoles);
    if (plan.graphSnapshotHash != await _currentHash(siteId)) throw const DataRuleException('plan_stale');
    final now = _ctx.now();
    final json = plan.toJson();
    final row = await _db
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
    await _audit.append(
      eventType: 'PLAN_CREATED',
      entityId: row.id,
      payload: {
        'id': row.id,
        'site_id': siteId,
        'target_node_ids': row.targetNodeIds,
        'graph_snapshot_hash': row.graphSnapshotHash,
        'solver_version': row.solverVersion,
      },
    );
    return row;
  });

  Future<IsolationPlanRow?> get(String id) => (_db.select(
    _db.isolationPlans,
  )..where((p) => p.id.equals(id) & p.orgId.equals(_ctx.orgId) & p.deleted.equals(false))).getSingleOrNull();

  /// Obyekt rejalari, eng yangisi birinchi.
  Future<List<IsolationPlanRow>> forSite(String siteId) =>
      (_db.select(_db.isolationPlans)
            ..where((p) => p.siteId.equals(siteId) & p.orgId.equals(_ctx.orgId) & p.deleted.equals(false))
            ..orderBy([(p) => OrderingTerm.desc(p.createdAt), (p) => OrderingTerm.desc(p.id)]))
          .get();

  /// Faqat LEAD/ADMIN (joriy foydalanuvchi), graf o'zgarmagan bo'lsa.
  Future<IsolationPlanRow> approve(String id) => _fresh(id, const {'DRAFT'}, (plan) async {
    await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
    final row = await _setStatus(plan, 'APPROVED', approvedBy: Value(_audit.actorId));
    await _audit.append(eventType: 'PLAN_APPROVED', entityId: id, payload: planApprovalPayload(plan));
    return row;
  });

  /// Qadamlar (saqlangan JSON'dan).
  List<PlanStep> steps(IsolationPlanRow plan) => [
    for (final s in plan.steps) PlanStep.fromJson((s! as Map).cast<String, Object?>()),
  ];

  List<PlanWarning> warnings(IsolationPlanRow plan) => [
    for (final w in plan.warnings) PlanWarning.fromJson((w! as Map).cast<String, Object?>()),
  ];

  /// Bajarilgan qadamlar (barcha qurilmalarning audit hodisalaridan), tartib → birinchi yozuv.
  Future<Map<int, StepRecord>> doneSteps(String planId) async {
    final events =
        await (_db.select(_db.auditEvents)
              ..where(
                (e) =>
                    e.orgId.equals(_ctx.orgId) &
                    e.eventType.equals('PLAN_STEP_DONE') &
                    e.entityId.like('${_escapeLike(planId)}#%', escapeChar: r'\'),
              )
              ..orderBy([(e) => OrderingTerm(expression: e.eventAt), (e) => OrderingTerm(expression: e.id)]))
            .get();
    final out = <int, StepRecord>{};
    for (final e in events) {
      final order = int.tryParse(e.entityId!.substring(planId.length + 1));
      if (order != null) out.putIfAbsent(order, () => StepRecord(order: order, actorId: e.actorId, at: e.eventAt));
    }
    return out;
  }

  /// Qadamni bajarilgan deb belgilash — faqat tasdiqlangan, eskirmagan rejada, ketma-ket va aniq tasdiq bilan
  /// (`checkStepCompletion`). Kuchlanish yo'qligini tekshirishni o'tkazib yuborib yoki avtomatik belgilab bo'lmaydi.
  Future<StepRecord> completeStep(String planId, int order, StepConfirmation confirmation) =>
      _fresh(planId, const {'APPROVED'}, (plan) async {
        await requireRole(_ctx, _audit.actorId, _fieldRoles);
        final list = steps(plan);
        final done = (await doneSteps(planId)).keys.toSet();
        final reason = checkStepCompletion(list, done, order, confirmation);
        if (reason != null) throw DataRuleException(reason, '$planId#$order');
        final step = list.firstWhere((s) => s.order == order);
        final e = await _audit.append(
          eventType: 'PLAN_STEP_DONE',
          entityId: '$planId#$order',
          payload: stepPayload(planId, step, confirmation),
        );
        return StepRecord(order: order, actorId: e.actorId, at: e.eventAt);
      });

  /// Barcha qadamlar bajarilgandagina.
  Future<IsolationPlanRow> execute(String id) => _fresh(id, const {'APPROVED'}, (plan) async {
    await requireRole(_ctx, _audit.actorId, _fieldRoles);
    if (!allStepsDone(steps(plan), (await doneSteps(id)).keys.toSet())) throw DataRuleException('steps_incomplete', id);
    final row = await _setStatus(plan, 'EXECUTED');
    await _audit.append(eventType: 'PLAN_EXECUTED', entityId: id, payload: {'id': id});
    return row;
  });

  Future<IsolationPlanRow> cancel(String id) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, _fieldRoles);
    final plan = await _require(id);
    _expectStatus(plan, const {'DRAFT', 'APPROVED'});
    final row = await _setStatus(plan, 'CANCELLED');
    await _audit.append(eventType: 'PLAN_CANCELLED', entityId: id, payload: {'id': id});
    return row;
  });

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

  /// Holat va graf tekshiruvi, so'ng [body] — tranzaksiyada. Eskirgan reja STALE ga o'tkaziladi (bu o'zgarish
  /// saqlanadi — tranzaksiyadan tashqarida) va `plan_stale` xatosi.
  Future<T> _fresh<T>(String id, Set<String> allowed, Future<T> Function(IsolationPlanRow plan) body) async {
    final plan = await _require(id);
    _expectStatus(plan, allowed);
    if (plan.graphSnapshotHash != await _currentHash(plan.siteId)) {
      await _setStatus(plan, 'STALE');
      throw DataRuleException('plan_stale', plan.id);
    }
    return _db.transaction(() async {
      final current = await _require(id);
      _expectStatus(current, allowed);
      return body(current);
    });
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

/// `PLAN_APPROVED` audit payload'i: tasdiqlangan qadamlar hash'i bilan — server tasdiqni aynan shu qadamlarga bog'laydi
/// (ADR-0014; tasdiqdan keyin qadamlar almashtirilsa, imzolangan hodisa mos kelmaydi).
Map<String, Object?> planApprovalPayload(IsolationPlanRow plan) => {
  'id': plan.id,
  'graph_snapshot_hash': plan.graphSnapshotHash,
  'steps_sha256': sha256Hex(utf8.encode(canonicalJson(plan.steps))),
};

/// `PLAN_STEP_DONE` audit payload'i (hash shu xaritadan).
Map<String, Object?> stepPayload(String planId, PlanStep step, StepConfirmation c) => {
  'plan_id': planId,
  'order': step.order,
  'kind': step.kind.code,
  'confirmation': c.toJson(),
};

String _escapeLike(String s) => s.replaceAll(r'\', r'\\').replaceAll('%', r'\%').replaceAll('_', r'\_');
