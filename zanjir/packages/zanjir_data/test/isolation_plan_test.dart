import 'dart:convert';

import 'package:drift/drift.dart' show Value;
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

const verified = StepConfirmation(done: true, indicatorTestedOnLive: true, noVoltageConfirmed: true);
const ok = StepConfirmation(done: true);

Matcher rule(String code) => throwsA(isA<DataRuleException>().having((e) => e.code, 'code', code));

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

  IsolationPlanRepository plans([Repositories? r]) => (r ?? org.repos).isolationPlans;

  /// Shu qurilmada boshqa foydalanuvchi (rol bo'yicha).
  Future<Repositories> as(String role) async {
    final u = await org.repos.users.create(fullName: role, phone: '+99890${role.length}000000', role: role);
    return Repositories(org.ctx, signer: org.signer, deviceId: org.device.id, actorId: u.id);
  }

  Future<IsolationPlanRow> draft([Repositories? r]) async {
    final g = await org.repos.graph.loadGraph(s.site.id);
    final plan = planIsolation(g, {s.cab1.id, s.sock1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
    return plans(r).save(siteId: s.site.id, plan: plan);
  }

  /// Barcha qadamlarni ketma-ket bajaradi (kuchlanish tekshiruvi — ikkala tasdiq bilan).
  Future<void> completeAll(IsolationPlanRow p, [Repositories? r]) async {
    for (final step in plans(r).steps(p)) {
      await plans(r).completeStep(p.id, step.order, step.kind == StepKind.verifyNoVoltage ? verified : ok);
    }
  }

  test('DRAFT → APPROVED → qadamlar → EXECUTED; qadamlar, ogohlantirishlar, audit', () async {
    final p = await draft();
    expect(p.status, 'DRAFT');
    expect(p.solverVersion, solverVersion);
    expect(p.targetNodeIds.toSet(), {s.cab1.id, s.sock1.id});
    final steps = plans().steps(p);
    expect(steps.where((x) => x.kind == StepKind.verifyNoVoltage), isNotEmpty);
    expect(steps.every((x) => x.mandatory), isTrue);
    expect(plans().warnings(p).map((w) => w.kind), contains(WarningKind.cableDischarge));
    await expectLater(plans().completeStep(p.id, 1, ok), rule('invalid_transition'));
    final approved = await plans().approve(p.id);
    expect((approved.status, approved.approvedBy), ('APPROVED', org.user.id));
    // Tasdiq hodisasi aynan shu qadamlarga bog'langan (server tekshiradi, ADR-0014).
    final ev = (await org.repos.audit.events()).lastWhere((e) => e.eventType == 'PLAN_APPROVED');
    expect(ev.payloadHash, payloadHash(planApprovalPayload(approved)));
    expect(planApprovalPayload(approved)['steps_sha256'], sha256Hex(utf8.encode(canonicalJson(p.steps))));
    await expectLater(plans().execute(p.id), rule('steps_incomplete'));
    await completeAll(p);
    final done = await plans().doneSteps(p.id);
    expect(done.keys.toSet(), {for (final x in steps) x.order});
    expect(done.values.every((r) => r.actorId == org.user.id), isTrue);
    expect((await plans().execute(p.id)).status, 'EXECUTED');
    await expectLater(plans().cancel(p.id), rule('invalid_transition'));
    final types = (await org.repos.audit.events()).map((e) => e.eventType).toList();
    expect(types, containsAllInOrder(['PLAN_CREATED', 'PLAN_APPROVED', 'PLAN_STEP_DONE', 'PLAN_EXECUTED']));
    expect(types.where((t) => t == 'PLAN_STEP_DONE'), hasLength(steps.length));
    expect((await org.repos.audit.verify()).ok, isTrue);
  });

  test('kuchlanish yo\'qligini tekshirish: o\'tkazib yuborib ham, tasdiqsiz ham bo\'lmaydi', () async {
    final p = await plans().approve((await draft()).id);
    final steps = plans().steps(p);
    final verify = steps.firstWhere((x) => x.kind == StepKind.verifyNoVoltage);
    final after = steps.firstWhere((x) => x.order > verify.order);
    for (final x in steps.where((x) => x.order < verify.order)) {
      await plans().completeStep(p.id, x.order, ok);
    }
    await expectLater(plans().completeStep(p.id, after.order, ok), rule('out_of_order'));
    await expectLater(plans().completeStep(p.id, verify.order, ok), rule('indicator_pretest_required'));
    await expectLater(
      plans().completeStep(p.id, verify.order, const StepConfirmation(done: true, indicatorTestedOnLive: true)),
      rule('no_voltage_confirmation_required'),
    );
    await expectLater(
      plans().completeStep(p.id, verify.order, const StepConfirmation()),
      rule('confirmation_required'),
    );
    expect((await plans().doneSteps(p.id)).containsKey(verify.order), isFalse);
    await plans().completeStep(p.id, verify.order, verified);
    await expectLater(plans().completeStep(p.id, verify.order, verified), rule('already_done'));
    await expectLater(plans().completeStep(p.id, 99, ok), rule('unknown_step'));
    await plans().completeStep(p.id, after.order, ok);
  });

  test('graf o\'zgarsa — STALE; eskirgan rejani tasdiqlab ham, bajarib ham bo\'lmaydi', () async {
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
    expect(await plans().refreshStale(s.site.id), unorderedEquals([p.id, p2.id]));
    expect((await plans().get(p.id))!.status, 'STALE');
    expect((await plans().get(p3.id))!.status, 'DRAFT');
    await expectLater(plans().approve(p.id), rule('invalid_transition'));
    final approved = await plans().approve(p3.id);
    await plans().completeStep(p3.id, 1, ok);
    // Bajarish paytida graf o'zgardi — keyingi qadam rad etiladi, reja STALE.
    await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.load, label: 'M9');
    await expectLater(plans().completeStep(approved.id, 2, ok), rule('plan_stale'));
    expect((await plans().get(p3.id))!.status, 'STALE');
    await expectLater(plans().execute(p3.id), rule('invalid_transition'));
  });

  test('tasdiqlash paytida graf o\'zgargan bo\'lsa — reja STALE bo\'ladi va xato', () async {
    final p = await draft();
    await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.load, label: 'M9');
    await expectLater(plans().approve(p.id), rule('plan_stale'));
    expect((await plans().get(p.id))!.status, 'STALE');
  });

  test('rollar: LEAD/ADMIN tasdiqlaydi; ENGINEER tuzadi va bajaradi; VIEWER hech narsa qilmaydi', () async {
    final eng = await as('ENGINEER');
    final viewer = await as('VIEWER');
    final p = await draft(eng);
    await expectLater(plans(eng).approve(p.id), rule('forbidden_role'));
    await expectLater(draft(viewer), rule('forbidden_role'));
    final admin = await as('ADMIN');
    await plans(admin).approve(p.id);
    await expectLater(plans(viewer).completeStep(p.id, 1, ok), rule('forbidden_role'));
    await completeAll(p, eng);
    expect((await plans(eng).execute(p.id)).status, 'EXECUTED');
    final done = await plans().doneSteps(p.id);
    expect(done.values.map((r) => r.actorId).toSet(), {eng.audit.actorId});

    final p2 = await draft();
    await expectLater(plans(viewer).cancel(p2.id), rule('forbidden_role'));
    expect((await plans().cancel(p2.id)).status, 'CANCELLED');
    await expectLater(plans().get('yoq'), completion(isNull));
    await expectLater(plans().cancel('yoq'), throwsA(isA<NotFoundException>()));
    expect((await plans().forSite(s.site.id)).map((x) => x.id), [p2.id, p.id]);
  });

  test('eskirgan grafdan tuzilgan reja saqlanmaydi', () async {
    final g = await org.repos.graph.loadGraph(s.site.id);
    final plan = planIsolation(g, {s.cab1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
    await org.repos.graph.addNode(siteId: s.site.id, kind: NodeKind.load, label: 'M9');
    await expectLater(plans().save(siteId: s.site.id, plan: plan), rule('plan_stale'));
  });

  test('yerga ulash tizimi o\'zgarsa ham STALE', () async {
    final p = await draft();
    await org.repos.sites.update(s.site.copyWith(earthingSystem: const Value(EarthingSystem.tnC)));
    expect(await plans().refreshStale(s.site.id), [p.id]);
  });

  test('boshqa qurilmada bajarilgan qadam sinxronlangan audit orqali ko\'rinadi', () async {
    final p = await plans().approve((await draft()).id);
    await plans().completeStep(p.id, 1, ok);
    final ev = (await org.repos.audit.forEntity('${p.id}#1')).single;
    expect(ev.payloadHash, sha256Hex(canonicalJsonBytes(stepPayload(p.id, plans().steps(p).first, ok))));
    // "_" va "%" ID ichida LIKE shabloni sifatida ishlamaydi.
    expect(await plans().doneSteps('${p.id.substring(0, 8)}%'), isEmpty);
  });
}
