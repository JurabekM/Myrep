import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'context.dart';
import 'site_repository.dart';

/// Obyekt grafi: tugunlar va qirralar. `loadGraph` — zanjir_core `Graph` (baholash va solver uchun).
class GraphRepository {
  GraphRepository(this._ctx) : _sites = SiteRepository(_ctx);
  final DataContext _ctx;
  final SiteRepository _sites;
  ZanjirDatabase get _db => _ctx.db;

  Future<NodeRow> addNode({
    required String siteId,
    required NodeKind kind,
    required String label,
    Map<String, Object?> attrs = const {},
    bool verified = false,
    String? panelId,
    SwitchState? state,
    double? x,
    double? y,
  }) async {
    await _sites.require(siteId);
    _checkState(kind, state);
    if (panelId != null) await _requireInSite(siteId, panelId);
    final now = _ctx.now();
    return _db
        .into(_db.nodes)
        .insertReturning(
          NodesCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            siteId: siteId,
            kind: kind,
            label: label,
            panelId: Value(panelId),
            state: Value(state),
            attrs: Value(attrs),
            verified: Value(verified),
            x: Value(x),
            y: Value(y),
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<NodeRow?> getNode(String id) => (_db.select(
    _db.nodes,
  )..where((n) => n.id.equals(id) & n.orgId.equals(_ctx.orgId) & n.deleted.equals(false))).getSingleOrNull();

  Future<NodeRow> updateNode(NodeRow changed) async {
    final old = await getNode(changed.id) ?? (throw NotFoundException('node', changed.id));
    if (changed.siteId != old.siteId) throw const DataRuleException('site_change');
    _checkState(changed.kind, changed.state);
    final panelId = changed.panelId;
    if (panelId != null) await _requireInSite(old.siteId, panelId);
    final row = changed.copyWith(
      orgId: _ctx.orgId,
      createdAt: old.createdAt,
      updatedAt: _ctx.now(),
      rev: old.rev + 1,
      deleted: false,
    );
    await _db.update(_db.nodes).replace(row);
    return row;
  }

  /// Tugunni va unga ulangan qirralarni soft delete qiladi.
  Future<void> softDeleteNode(String id) => _db.transaction(() async {
    final old = await getNode(id) ?? (throw NotFoundException('node', id));
    final now = _ctx.now();
    await _db.update(_db.nodes).replace(old.copyWith(deleted: true, updatedAt: now, rev: old.rev + 1));
    final incident =
        await (_db.select(_db.edges)..where(
              (e) =>
                  e.orgId.equals(_ctx.orgId) & e.deleted.equals(false) & (e.aNodeId.equals(id) | e.bNodeId.equals(id)),
            ))
            .get();
    for (final e in incident) {
      await _db.update(_db.edges).replace(e.copyWith(deleted: true, updatedAt: now, rev: e.rev + 1));
    }
  });

  Future<EdgeRow> addEdge({
    required String siteId,
    required String aNodeId,
    required String bNodeId,
    required String conductors,
  }) async {
    await _sites.require(siteId);
    if (aNodeId == bNodeId) throw const DataRuleException('self_loop');
    await _requireInSite(siteId, aNodeId);
    await _requireInSite(siteId, bNodeId);
    final now = _ctx.now();
    return _db
        .into(_db.edges)
        .insertReturning(
          EdgesCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            siteId: siteId,
            aNodeId: aNodeId,
            bNodeId: bNodeId,
            conductors: conductors,
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<void> softDeleteEdge(String id) async {
    final old =
        await (_db.select(
          _db.edges,
        )..where((e) => e.id.equals(id) & e.orgId.equals(_ctx.orgId) & e.deleted.equals(false))).getSingleOrNull() ??
        (throw NotFoundException('edge', id));
    await _db.update(_db.edges).replace(old.copyWith(deleted: true, updatedAt: _ctx.now(), rev: old.rev + 1));
  }

  Future<List<NodeRow>> nodes(String siteId) =>
      (_db.select(_db.nodes)
            ..where((n) => n.siteId.equals(siteId) & n.orgId.equals(_ctx.orgId) & n.deleted.equals(false))
            ..orderBy([(n) => OrderingTerm(expression: n.label), (n) => OrderingTerm(expression: n.id)]))
          .get();

  Future<List<EdgeRow>> edges(String siteId) =>
      (_db.select(_db.edges)
            ..where((e) => e.siteId.equals(siteId) & e.orgId.equals(_ctx.orgId) & e.deleted.equals(false))
            ..orderBy([(e) => OrderingTerm(expression: e.id)]))
          .get();

  Future<Graph> loadGraph(String siteId) async {
    await _sites.require(siteId);
    final nodes = await this.nodes(siteId);
    final edges = await this.edges(siteId);
    return Graph(
      [
        for (final n in nodes)
          Node(
            id: n.id,
            siteId: n.siteId,
            kind: n.kind,
            label: n.label,
            attrs: n.attrs,
            verified: n.verified,
            state: n.state,
            panelId: n.panelId,
          ),
      ],
      [
        for (final e in edges)
          Edge(id: e.id, siteId: e.siteId, aNodeId: e.aNodeId, bNodeId: e.bNodeId, conductors: e.conductors),
      ],
    );
  }

  /// Apparatni nusxalash (QF1 → QF2). Nusxa tasdiqlanmagan va ulanmagan — dalada tekshiriladi.
  Future<NodeRow> duplicateNode(String id) async {
    final src = await getNode(id) ?? (throw NotFoundException('node', id));
    final labels = {for (final n in await nodes(src.siteId)) n.label};
    return addNode(
      siteId: src.siteId,
      kind: src.kind,
      label: nextLabel(src.label, labels),
      attrs: src.attrs,
      panelId: src.panelId,
      state: src.state,
    );
  }

  void _checkState(NodeKind kind, SwitchState? state) {
    if (state != null && !kind.isSwitching) throw DataRuleException('state_on_non_switching', kind.code);
  }

  Future<void> _requireInSite(String siteId, String nodeId) async {
    final n = await getNode(nodeId);
    if (n == null || n.siteId != siteId) throw DataRuleException('node_not_in_site', nodeId);
  }
}

final _trailingNumber = RegExp(r'^(.*?)(\d+)$');

/// Keyingi bo'sh yorliq: `QF1` → `QF2`, `QF09` → `QF10`, raqamsiz `SHR` → `SHR-2`.
String nextLabel(String label, Set<String> existing) {
  final m = _trailingNumber.firstMatch(label);
  final prefix = m == null ? '$label-' : m.group(1)!;
  final width = m == null ? 1 : m.group(2)!.length;
  var n = m == null ? 2 : int.parse(m.group(2)!) + 1;
  while (true) {
    final candidate = '$prefix${n.toString().padLeft(width, '0')}';
    if (!existing.contains(candidate)) return candidate;
    n++;
  }
}
