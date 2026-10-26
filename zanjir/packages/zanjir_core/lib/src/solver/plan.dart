import '../model/enums.dart';

/// Qadam turlari — 5 ta texnik tadbir tartibida (prompt 5.3, 7-band).
enum StepKind {
  stopPvAc('STOP_PV_AC'),
  stopPvDc('STOP_PV_DC'),
  stopGenerator('STOP_GENERATOR'),
  stopUps('STOP_UPS'),
  stopBattery('STOP_BATTERY'),
  openDevice('OPEN_DEVICE'),
  lockAndTag('LOCK_AND_TAG'),
  verifyNoVoltage('VERIFY_NO_VOLTAGE'),
  applyEarthing('APPLY_EARTHING'),
  fenceAndSign('FENCE_AND_SIGN');

  const StepKind(this.code);
  final String code;
}

enum WarningKind {
  unverifiedNode('UNVERIFIED_NODE'),
  capacitorInZone('CAPACITOR_IN_ZONE'),
  cableDischarge('CABLE_DISCHARGE'),
  pvDcSide('PV_DC_SIDE'),
  penConductor('PEN_CONDUCTOR'),
  contactorOrAtsInCut('CONTACTOR_ATS_IN_CUT'),
  noSourceReachable('NO_SOURCE_REACHABLE'),
  earthingSystemUnknown('EARTHING_SYSTEM_UNKNOWN');

  const WarningKind(this.code);
  final String code;
}

enum BlockReason {
  /// Manbadan zonaga kommutatsiya apparatisiz yo'l bor (oqim = ∞).
  noSwitchingDevice('no_switching_device'),

  /// Zona ichida manba (kondensatordan tashqari) — reja avtomatik tuzilmaydi.
  sourceInZone('source_in_zone'),

  /// Mustaqil BFS kesimdan keyin ham yo'l topdi (solver xatosi).
  verificationFailed('verification_failed');

  const BlockReason(this.code);
  final String code;
}

class CutDevice {
  const CutDevice({required this.nodeId, required this.kind, required this.cost, required this.label});
  final String nodeId;
  final NodeKind kind;
  final int cost;
  final String label;

  Map<String, Object?> toJson() => {'node_id': nodeId, 'kind': kind.code, 'cost': cost, 'label': label};
}

/// Zonaga kuchlanish kelishi mumkin bo'lgan tomon. `outsideNodeId == null` — manba topilmagan, zona tugunining o'zi.
class EntryPoint {
  const EntryPoint(this.zoneNodeId, this.outsideNodeId);
  final String zoneNodeId;
  final String? outsideNodeId;

  Map<String, Object?> toJson() => {'zone_node_id': zoneNodeId, 'outside_node_id': outsideNodeId};
}

/// Reja qadami. Barcha qadamlar majburiy; "kuchlanish yo'qligini tekshirish" ni o'tkazib yuborib,
/// yashirib yoki avtomatik belgilab bo'lmaydi (CLAUDE.md, 2-qoida) — bajarilish holati UI'da faqat qo'lda.
class PlanStep {
  const PlanStep({required this.order, required this.kind, required this.nodeIds, this.params = const {}});
  final int order;
  final StepKind kind;
  final List<String> nodeIds;
  final Map<String, Object?> params;

  bool get mandatory => true;

  Map<String, Object?> toJson() => {
    'order': order,
    'kind': kind.code,
    'node_ids': nodeIds,
    'mandatory': mandatory,
    'params': params,
  };
}

class PlanWarning {
  const PlanWarning(this.kind, this.nodeIds, [this.params = const {}]);
  final WarningKind kind;
  final List<String> nodeIds;
  final Map<String, Object?> params;

  Map<String, Object?> toJson() => {'kind': kind.code, 'node_ids': nodeIds, 'params': params};
}

sealed class IsolationResult {
  const IsolationResult({
    required this.solverVersion,
    required this.targetNodeIds,
    required this.graphSnapshotHash,
    required this.warnings,
  });
  final String solverVersion;
  final List<String> targetNodeIds;

  /// Kanonik grafning SHA-256 hash'i; graf o'zgarsa reja STALE bo'ladi.
  final String graphSnapshotHash;
  final List<PlanWarning> warnings;

  Map<String, Object?> toJson();
}

/// Tavsiya etilgan ajratish rejasi. Ilova "ishlash xavfsiz" demaydi — javobgarlik naryad beruvchi
/// va ish rahbari zimmasida (CLAUDE.md, 1-qoida).
final class IsolationPlan extends IsolationResult {
  const IsolationPlan({
    required super.solverVersion,
    required super.targetNodeIds,
    required super.graphSnapshotHash,
    required super.warnings,
    required this.cut,
    required this.cost,
    required this.reachableSources,
    required this.entryPoints,
    required this.steps,
  });
  final List<CutDevice> cut;
  final int cost;
  final List<String> reachableSources;
  final List<EntryPoint> entryPoints;
  final List<PlanStep> steps;

  @override
  Map<String, Object?> toJson() => {
    'status': 'PLAN',
    'solver_version': solverVersion,
    'target_node_ids': targetNodeIds,
    'graph_snapshot_hash': graphSnapshotHash,
    'cost': cost,
    'cut': [for (final c in cut) c.toJson()],
    'reachable_sources': reachableSources,
    'entry_points': [for (final e in entryPoints) e.toJson()],
    'steps': [for (final s in steps) s.toJson()],
    'warnings': [for (final w in warnings) w.toJson()],
  };
}

final class IsolationBlocked extends IsolationResult {
  const IsolationBlocked({
    required super.solverVersion,
    required super.targetNodeIds,
    required super.graphSnapshotHash,
    required super.warnings,
    required this.reason,
    required this.path,
  });
  final BlockReason reason;

  /// Muammoli yo'l: manbadan zonagacha (yoki zona ichidagi manba).
  final List<String> path;

  @override
  Map<String, Object?> toJson() => {
    'status': 'BLOCKED',
    'solver_version': solverVersion,
    'target_node_ids': targetNodeIds,
    'graph_snapshot_hash': graphSnapshotHash,
    'reason': reason.code,
    'path': path,
    'warnings': [for (final w in warnings) w.toJson()],
  };
}
