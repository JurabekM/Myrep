import 'package:drift/drift.dart' show Value;
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

void main() {
  late ZanjirDatabase db;
  late Org org;
  setUp(() async {
    db = memoryDb();
    org = await Org.create(db, 'A');
  });
  tearDown(() => db.close());

  group('SiteRepository', () {
    test('yaratish, yangilash (rev + updated_at), ro\'yxat, soft delete', () async {
      final r = org.repos.sites;
      final s = await r.create(
        name: 'Savdo markazi',
        address: 'Toshkent',
        customer: 'MChJ',
        earthingSystem: EarthingSystem.tnCS,
        u0Volts: 220,
      );
      expect(s.orgId, org.ctx.orgId);
      expect(s.rev, 1);
      expect(s.createdAt.isUtc, isTrue);
      final updated = await r.update(s.copyWith(name: 'Savdo markazi 2', u0Volts: const Value(230)));
      expect(updated.name, 'Savdo markazi 2');
      expect(updated.u0Volts, 230);
      expect(updated.rev, 2);
      expect(updated.updatedAt.isAfter(s.updatedAt), isTrue);
      expect(updated.createdAt, s.createdAt);
      expect((await r.list()).map((x) => x.id), [s.id]);
      await r.softDelete(s.id);
      expect(await r.list(), isEmpty);
      expect(await r.get(s.id), isNull);
      await expectLater(r.update(updated), throwsA(isA<NotFoundException>()));
      await expectLater(r.softDelete(s.id), throwsA(isA<NotFoundException>()));
    });

    test('toCore', () async {
      final s = await org.repos.sites.create(name: 'X', earthingSystem: EarthingSystem.tt, u0Volts: 220);
      final core = org.repos.sites.toCore(s);
      expect((core.id, core.name, core.earthingSystem, core.u0Volts), (s.id, 'X', EarthingSystem.tt, 220.0));
    });
  });

  group('GraphRepository', () {
    test('tugun va qirralar, loadGraph — zanjir_core Graph', () async {
      final s = await SmallSite.create(org);
      final g = await org.repos.graph.loadGraph(s.site.id);
      expect(g.nodes.map((n) => n.id).toSet(), {s.grid.id, s.qf1.id, s.cab1.id, s.sock1.id});
      expect(g.neighbors(s.qf1.id).toSet(), {s.grid.id, s.cab1.id});
      final qf = g.node(s.qf1.id)!;
      expect((qf.kind, qf.label, qf.state, qf.verified), (NodeKind.breaker, 'QF1', SwitchState.closed, true));
      expect(qf.attrs, {'in_a': 16, 'curve': 'C'});
      // Graf solver bilan ishlaydi.
      final plan = planIsolation(g, {s.cab1.id, s.sock1.id}) as IsolationPlan;
      expect(plan.cut.single.nodeId, s.qf1.id);
    });

    test('tugunni o\'chirish qo\'shni qirralarni ham o\'chiradi', () async {
      final s = await SmallSite.create(org);
      await org.repos.graph.softDeleteNode(s.cab1.id);
      final g = await org.repos.graph.loadGraph(s.site.id);
      expect(g.node(s.cab1.id), isNull);
      expect(g.edges, hasLength(1));
      expect(await org.repos.graph.edges(s.site.id), hasLength(1));
    });

    test('tugunni yangilash; state faqat kommutatsiya apparatida', () async {
      final s = await SmallSite.create(org);
      final n = await org.repos.graph.updateNode(
        s.qf1.copyWith(state: const Value(SwitchState.open), attrs: {'in_a': 20, 'curve': 'C'}),
      );
      expect((n.state, n.attrs['in_a'], n.rev), (SwitchState.open, 20, 2));
      await expectLater(
        org.repos.graph.updateNode(s.cab1.copyWith(state: const Value(SwitchState.open))),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'state_on_non_switching')),
      );
      await expectLater(
        org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.load, label: 'M1', state: SwitchState.closed),
        throwsA(isA<DataRuleException>()),
      );
      await expectLater(
        org.repos.graph.updateNode(s.qf1.copyWith(siteId: 'boshqa')),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'site_change')),
      );
    });

    test('shit (panel_id) shu obyektda bo\'lishi kerak; xato matnlari', () async {
      final s = await SmallSite.create(org);
      final panel = await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.panel, label: 'SHR-1');
      final inPanel = await org.repos.graph.updateNode(s.qf1.copyWith(panelId: Value(panel.id)));
      expect(inPanel.panelId, panel.id);
      final other = await org.repos.sites.create(name: 'Boshqa');
      final foreignPanel = await org.repos.graph.addNode(siteId: other.id, kind: NodeKind.panel, label: 'SHR-9');
      await expectLater(
        org.repos.graph.updateNode(inPanel.copyWith(panelId: Value(foreignPanel.id))),
        throwsA(isA<DataRuleException>().having((e) => e.toString(), 'toString', contains('node_not_in_site'))),
      );
      expect(const DataRuleException('session_closed').toString(), 'DataRuleException: session_closed');
      expect(const NotFoundException('site', 'x').toString(), 'NotFoundException: site x');
    });

    test('qirra qoidalari: o\'z-o\'ziga, boshqa obyekt, o\'chirilgan tugun', () async {
      final s = await SmallSite.create(org);
      final other = await org.repos.sites.create(name: 'Boshqa');
      final foreign = await org.repos.graph.addNode(siteId: other.id, kind: NodeKind.load, label: 'M');
      Future<void> bad(String a, String b, String code) => expectLater(
        org.repos.graph.addEdge(siteId: s.site.id, aNodeId: a, bNodeId: b, conductors: 'PE'),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', code)),
      );
      await bad(s.qf1.id, s.qf1.id, 'self_loop');
      await bad(s.qf1.id, foreign.id, 'node_not_in_site');
      await org.repos.graph.softDeleteNode(s.sock1.id);
      await bad(s.cab1.id, s.sock1.id, 'node_not_in_site');
      await expectLater(
        org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.breaker, label: 'QF9', panelId: foreign.id),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'node_not_in_site')),
      );
      await expectLater(
        org.repos.graph.addNode(siteId: 'yoq', kind: NodeKind.load, label: 'M'),
        throwsA(isA<NotFoundException>()),
      );
      final e = (await org.repos.graph.edges(s.site.id)).first;
      await org.repos.graph.softDeleteEdge(e.id);
      expect(await org.repos.graph.edges(s.site.id), hasLength(1));
      await expectLater(org.repos.graph.softDeleteEdge(e.id), throwsA(isA<NotFoundException>()));
    });

    test('apparatni nusxalash: QF1 → QF2, tasdiqlanmagan, ulanmagan', () async {
      final s = await SmallSite.create(org);
      final copy = await org.repos.graph.duplicateNode(s.qf1.id);
      expect(copy.label, 'QF2');
      expect(copy.attrs, s.qf1.attrs);
      expect(copy.kind, NodeKind.breaker);
      expect(copy.verified, isFalse);
      final copy2 = await org.repos.graph.duplicateNode(s.qf1.id);
      expect(copy2.label, 'QF3');
      final w = await org.repos.graph.duplicateNode(s.cab1.id);
      expect(w.label, 'W2');
      final noDigits = await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.panel, label: 'SHR');
      expect((await org.repos.graph.duplicateNode(noDigits.id)).label, 'SHR-2');
      expect((await org.repos.graph.loadGraph(s.site.id)).neighbors(copy.id), isEmpty);
    });

    test('nextLabel', () {
      expect(nextLabel('QF1', {'QF1'}), 'QF2');
      expect(nextLabel('QF1', {'QF1', 'QF2', 'QF3'}), 'QF4');
      expect(nextLabel('QF9', {'QF9'}), 'QF10');
      expect(nextLabel('1QF09', {'1QF09'}), '1QF10');
      expect(nextLabel('SHR', {'SHR', 'SHR-2'}), 'SHR-3');
    });
  });
}
