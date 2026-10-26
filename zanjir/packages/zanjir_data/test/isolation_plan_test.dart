import 'package:drift/drift.dart' show Value;
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

void main() {
  late ZanjirDatabase db;
  late Org org;
  late SmallSite s;
  setUp(() async {
    db = memoryDb();
    org = await Org.create(db, 'A');
    s = await SmallSite.create(org);
  });
  tearDown(() => db.close());

  Future<IsolationPlanRow> draft() async {
    final g = await org.repos.graph.loadGraph(s.site.id);
    final plan = planIsolation(g, {s.cab1.id, s.sock1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
    return org.repos.isolationPlans.save(siteId: s.site.id, plan: plan);
  }

  test('DRAFT → APPROVED → EXECUTED; qadamlar va ogohlantirishlar saqlanadi', () async {
    final p = await draft();
    expect(p.status, 'DRAFT');
    expect(p.solverVersion, solverVersion);
    expect(p.targetNodeIds.toSet(), {s.cab1.id, s.sock1.id});
    expect((p.steps.firstWhere((x) => (x! as Map)['kind'] == 'VERIFY_NO_VOLTAGE')! as Map)['mandatory'], isTrue);
    final approved = await org.repos.isolationPlans.approve(p.id, approvedBy: org.user.id);
    expect((approved.status, approved.approvedBy), ('APPROVED', org.user.id));
    expect((await org.repos.isolationPlans.execute(p.id)).status, 'EXECUTED');
    await expectLater(
      org.repos.isolationPlans.cancel(p.id),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'invalid_transition')),
    );
  });

  test('graf o\'zgarsa — STALE; eskirgan rejani tasdiqlab bo\'lmaydi', () async {
    final p = await draft();
    final p2 = await draft();
    await org.repos.graph.updateNode(s.qf1.copyWith(label: 'QF1.1'));
    // Holat (state) o'zgarishi rejani eskirtirmaydi — u rejani bajarishning o'zi.
    final p3 = await draft();
    await org.repos.graph.updateNode(
      (await org.repos.graph.nodes(s.site.id))
          .firstWhere((n) => n.id == s.qf1.id)
          .copyWith(state: const Value(SwitchState.open)),
    );
    expect(await org.repos.isolationPlans.refreshStale(s.site.id), unorderedEquals([p.id, p2.id]));
    expect((await org.repos.isolationPlans.get(p.id))!.status, 'STALE');
    expect((await org.repos.isolationPlans.get(p3.id))!.status, 'DRAFT');
    await expectLater(
      org.repos.isolationPlans.approve(p.id, approvedBy: org.user.id),
      throwsA(isA<DataRuleException>()),
    );
    // p3 dan keyin graf o'zgarmagan — tasdiqlanadi.
    expect((await org.repos.isolationPlans.approve(p3.id, approvedBy: org.user.id)).status, 'APPROVED');
  });

  test('tasdiqlash paytida graf o\'zgargan bo\'lsa — reja STALE bo\'ladi va xato', () async {
    final p = await draft();
    await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.load, label: 'M9');
    await expectLater(
      org.repos.isolationPlans.approve(p.id, approvedBy: org.user.id),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'plan_stale')),
    );
    expect((await org.repos.isolationPlans.get(p.id))!.status, 'STALE');
  });

  test('faqat LEAD/ADMIN tasdiqlaydi; bekor qilish', () async {
    final eng = await org.repos.users.create(fullName: 'Muhandis', phone: '+998901111111', role: 'ENGINEER');
    final p = await draft();
    await expectLater(
      org.repos.isolationPlans.approve(p.id, approvedBy: eng.id),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'forbidden_role')),
    );
    await expectLater(org.repos.isolationPlans.approve(p.id, approvedBy: 'yoq'), throwsA(isA<NotFoundException>()));
    expect((await org.repos.isolationPlans.cancel(p.id)).status, 'CANCELLED');
    await expectLater(org.repos.isolationPlans.execute(p.id), throwsA(isA<DataRuleException>()));
    await expectLater(org.repos.isolationPlans.get('yoq'), completion(isNull));
    await expectLater(org.repos.isolationPlans.cancel('yoq'), throwsA(isA<NotFoundException>()));
  });

  test('eskirgan grafdan tuzilgan reja saqlanmaydi', () async {
    final g = await org.repos.graph.loadGraph(s.site.id);
    final plan = planIsolation(g, {s.cab1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
    await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.load, label: 'M9');
    await expectLater(
      org.repos.isolationPlans.save(siteId: s.site.id, plan: plan),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'plan_stale')),
    );
  });

  test('yerga ulash tizimi o\'zgarsa ham STALE', () async {
    final p = await draft();
    await org.repos.sites.update(s.site.copyWith(earthingSystem: const Value(EarthingSystem.tnC)));
    expect(await org.repos.isolationPlans.refreshStale(s.site.id), [p.id]);
  });
}
