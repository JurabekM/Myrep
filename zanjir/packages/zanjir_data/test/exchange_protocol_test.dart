import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/exchange_support.dart';
import 'support/harness.dart';

const verified = StepConfirmation(done: true, indicatorTestedOnLive: true, noVoltageConfirmed: true);
const ok = StepConfirmation(done: true);

void main() {
  late DateTime Function() clock;
  late Phone lead;
  late Phone engineer;
  late SmallSite s;

  setUp(() async {
    clock = steppingClock();
    lead = await Phone.lead(clock);
    final user = await lead.repos.staff.addUser(fullName: 'Muhandis', role: 'ENGINEER');
    await lead.repos.normSets.import(reviewedTestYaml);
    await lead.repos.settings.updateLab(
      byUserId: lead.userId,
      name: 'Elektrolab',
      licenseNo: 'EL-0042',
      licenseValidUntil: DateTime.utc(2027, 12, 31),
    );
    final (bytes, password) = await lead.invite(user.id);
    engineer = await Phone.join(bytes, password, 2, clock);
    s = await SmallSite.createWith(engineer.repos);
  });

  /// Muhandis telefonida imzolangan protokol.
  Future<SignedProtocol> signOnEngineer() async {
    final r = engineer.repos;
    final session = await r.sessions.start(
      siteId: s.site.id,
      kind: SessionKind.davriy,
      engineerId: engineer.userId,
      ambientTempC: 18,
    );
    await r.measurements.record(
      sessionId: session.id,
      nodeId: s.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: s.instrument.id,
      values: const {'pair': 'L1-PE', 'zs_ohm': 0.84},
      enteredVia: EnteredVia.manual,
      normSetVersion: reviewedTestVersion,
    );
    await r.sessions.close(session.id);
    final draft = await r.protocols.prepare(sessionId: session.id);
    expect(draft.blockers, isEmpty);
    return r.protocols.sign(draft, testFonts());
  }

  group('protokol', () {
    test('imzolangan protokol LEAD telefoniga o\'tadi va u yerda tekshiriladi', () async {
      final signed = await signOnEngineer();
      final r = await lead.import(await engineer.export());
      expect(r.inserted['protocol'], 1);
      expect(await lead.repos.protocols.verify(signed.protocol.id), isNull);
      expect(await lead.repos.protocols.status(signed.protocol.id), ProtocolStatus.active);
      // LEAD bekor qiladi — muhandis telefonida ham bekor.
      await lead.repos.protocols.revoke(signed.protocol.id, reason: 'Xato obyekt');
      await engineer.import(await lead.export());
      expect(await engineer.repos.protocols.status(signed.protocol.id), ProtocolStatus.revoked);
    });

    test('PDF almashtirildi — pdf_hash_mismatch', () async {
      await signOnEngineer();
      final file = await tamper(engineer, await engineer.export(), (b) {
        final d = rows(b, 'protocol_document').single;
        d['pdf'] = 'JVBERi0xLjQK';
      });
      await expectLater(lead.import(file), rule('pdf_hash_mismatch'));
    });

    test('hujjatsiz protokol — protocol_document_required', () async {
      await signOnEngineer();
      final file = await tamper(engineer, await engineer.export(), (b) => rows(b, 'protocol_document').clear());
      await expectLater(lead.import(file), rule('protocol_document_required'));
    });

    test('protokol raqami o\'zgartirildi — PROTOCOL_SIGNED hodisasiga mos emas', () async {
      await signOnEngineer();
      final file = await tamper(engineer, await engineer.export(), (b) {
        rows(b, 'protocol').single['number'] = '2026-ABCDEF-001';
      });
      // Raqam audit payload'ida ham — avval hodisa mos kelmaydi.
      await expectLater(lead.import(file), rule('missing_audit_event'));
    });

    test('protokol o\'lchovlari olib tashlandi — protocol_rule:no_measurements', () async {
      final signed = await signOnEngineer();
      final file = await tamper(engineer, await engineer.export(), (b) {
        // Imzolangan payload'ni o'zgartirib bo'lmaydi (hash) — hujumchi bazadagi o'lchovni olib tashlaydi.
        rows(b, 'measurement').clear();
      });
      expect(signed.protocol.sessionId, isNotEmpty);
      await expectLater(lead.import(file), rule('protocol_rule:no_measurements'));
    });
  });

  group('ajratish rejasi', () {
    Future<IsolationPlanRow> draft(Phone p) async {
      final g = await p.repos.graph.loadGraph(s.site.id);
      final plan = planIsolation(g, {s.cab1.id, s.sock1.id}, earthingSystem: EarthingSystem.tnCS) as IsolationPlan;
      return p.repos.isolationPlans.save(siteId: s.site.id, plan: plan);
    }

    test('muhandis rejasi → LEAD tasdiqlaydi → muhandis bajaradi → hammasi LEAD da', () async {
      final p = await draft(engineer);
      await lead.import(await engineer.export());
      await lead.repos.isolationPlans.approve(p.id);
      await engineer.import(await lead.export());
      final plans = engineer.repos.isolationPlans;
      final approved = (await plans.get(p.id))!;
      expect(approved.status, 'APPROVED');
      for (final step in plans.steps(approved)) {
        await plans.completeStep(p.id, step.order, step.kind == StepKind.verifyNoVoltage ? verified : ok);
      }
      await plans.execute(p.id);
      await lead.import(await engineer.export());
      expect((await lead.repos.isolationPlans.get(p.id))!.status, 'EXECUTED');
    });

    test('muhandis rejani o\'zi "tasdiqlaydi" — approval_requires_lead', () async {
      final p = await draft(engineer);
      final file = await tamper(engineer, await engineer.export(), (b) {
        final r = rows(b, 'isolation_plan').single;
        r['status'] = 'APPROVED';
        r['approved_by'] = engineer.userId;
      });
      await expectLater(lead.import(file), rule('approval_requires_lead'));
      expect(p.status, 'DRAFT');
    });

    test('tasdiqlangan reja qadamlarini o\'zgartirib bo\'lmaydi — plan_immutable', () async {
      final p = await draft(engineer);
      await lead.import(await engineer.export());
      await lead.repos.isolationPlans.approve(p.id);
      await engineer.import(await lead.export());
      final file = await tamper(engineer, await engineer.export(), (b) {
        final r = rows(b, 'isolation_plan').single;
        r['steps'] = (r['steps']! as List).sublist(1);
        r['updated_at'] = isoUtcMillis(clock());
      });
      await expectLater(lead.import(file), rule('plan_immutable'));
    });

    test('qadamlarsiz "bajarildi" — plan_steps_incomplete', () async {
      final p = await draft(engineer);
      await lead.import(await engineer.export());
      await lead.repos.isolationPlans.approve(p.id);
      await engineer.import(await lead.export());
      final file = await tamper(engineer, await engineer.export(), (b) {
        final r = rows(b, 'isolation_plan').single;
        r['status'] = 'EXECUTED';
        r['updated_at'] = isoUtcMillis(clock());
      });
      await expectLater(lead.import(file), rule('plan_steps_incomplete'));
    });

    test('bekor qilingan reja yakuniy — eski "APPROVED" uni qaytarmaydi', () async {
      final p = await draft(engineer);
      await lead.import(await engineer.export());
      await lead.repos.isolationPlans.approve(p.id);
      await engineer.import(await lead.export());
      await engineer.repos.isolationPlans.cancel(p.id);
      final engineerFile = await engineer.export();
      await lead.import(engineerFile);
      expect((await lead.repos.isolationPlans.get(p.id))!.status, 'CANCELLED');
    });
  });
}
