import 'package:drift/drift.dart' show Value;
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

void main() {
  late ZanjirDatabase db;
  late Org org;
  late SmallSite s;
  late MeasurementSessionRow session;
  setUp(() async {
    db = memoryDb();
    org = await Org.create(db, 'A');
    s = await SmallSite.create(org);
    session = await org.repos.sessions.start(
      siteId: s.site.id,
      kind: SessionKind.davriy,
      engineerId: org.user.id,
      ambientTempC: 21.5,
      humidityPct: 60,
    );
  });
  tearDown(() => db.close());

  Future<MeasurementRow> record(
    Map<String, Object?> values, {
    String? nodeId,
    MeasurementType? type,
    String? supersedesId,
    String? sessionId,
  }) => org.repos.measurements.record(
    sessionId: sessionId ?? session.id,
    nodeId: nodeId ?? s.sock1.id,
    type: type ?? MeasurementType.loopImpedance,
    instrumentId: s.instrument.id,
    values: values,
    enteredVia: EnteredVia.manual,
    normSetVersion: '0.2.0',
    supersedesId: supersedesId,
  );

  test('o\'lchov baholanadi, saqlanadi va audit zanjiriga yoziladi', () async {
    final m = await record({'pair': 'L1-PE', 'zs_ohm': 0.84});
    expect(m.verdict, Verdict.pass);
    expect(m.normId, 'LOOP-TN-FINAL');
    expect(m.normSetVersion, '0.2.0');
    expect(m.evalDetail['strictest_norm_id'], 'LOOP-TN-FINAL');
    expect(m.values, {'pair': 'L1-PE', 'zs_ohm': 0.84});
    final events = await org.repos.audit.events();
    final added = events.where((e) => e.eventType == 'MEASUREMENT_ADDED').single;
    expect(added.entityId, m.id);
    expect(added.payloadHash, payloadHash(measurementAuditPayload(m)));
    expect((await org.repos.audit.verify()).ok, isTrue);
  });

  test('tugun bo\'yicha tarix — eng yangisi birinchi, boshqa tashkilot ko\'rinmaydi', () async {
    final a = await record({'pair': 'L1-PE', 'zs_ohm': 0.84});
    final b = await record({'pair': 'L1-PE', 'zs_ohm': 0.9});
    expect((await org.repos.measurements.forNode(s.sock1.id)).map((m) => m.id), [b.id, a.id]);
    expect(await org.repos.measurements.forNode(s.cab1.id), isEmpty);
  });

  test('FAIL va NEEDS_REVIEW ham saqlanadi (PASS standart emas)', () async {
    expect((await record({'pair': 'L1-PE', 'zs_ohm': 1.5})).verdict, Verdict.fail);
    expect((await record({'pair': 'L1-PE'})).verdict, Verdict.needsReview);
  });

  test('sessiya harorati izolyatsiya baholashiga uzatiladi', () async {
    final noTemp = await org.repos.sessions.start(siteId: s.site.id, kind: SessionKind.davriy, engineerId: org.user.id);
    final values = {
      'test_voltage_v': 1000,
      'pairs': [
        {'pair': 'L1-PE', 'mohm': 100.0},
      ],
    };
    final a = await record(values, nodeId: s.cab1.id, type: MeasurementType.insulation, sessionId: noTemp.id);
    expect((a.verdict, a.evalDetail['reason']), (Verdict.needsReview, 'missing_ambient_temp'));
    final b = await record(values, nodeId: s.cab1.id, type: MeasurementType.insulation);
    expect(b.verdict, Verdict.pass);
  });

  test('xato o\'lchov o\'chirilmaydi — supersedes_id bilan almashtiriladi', () async {
    final wrong = await record({'pair': 'L1-PE', 'zs_ohm': 8.4});
    final fixed = await record({'pair': 'L1-PE', 'zs_ohm': 0.84}, supersedesId: wrong.id);
    expect(fixed.supersedesId, wrong.id);
    expect((await org.repos.measurements.forSession(session.id)).map((m) => m.id), [fixed.id]);
    expect((await org.repos.measurements.forSession(session.id, includeSuperseded: true)).map((m) => m.id), [
      wrong.id,
      fixed.id,
    ]);
    expect(await org.repos.measurements.get(wrong.id), isNotNull);
    await expectLater(
      record({'pair': 'L1-PE', 'zs_ohm': 0.9}, supersedesId: wrong.id),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'already_superseded')),
    );
    await expectLater(
      record({'pair': 'L1-PE', 'zs_ohm': 0.9}, supersedesId: fixed.id, nodeId: s.cab1.id),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'supersede_mismatch')),
    );
    await expectLater(record({'pair': 'L1-PE', 'zs_ohm': 0.9}, supersedesId: 'yoq'), throwsA(isA<NotFoundException>()));
  });

  test('yopilgan sessiyaga o\'lchov qo\'shilmaydi; shartlarni faqat ochiq sessiyada o\'zgartirish mumkin', () async {
    final updated = await org.repos.sessions.updateConditions(
      session.id,
      ambientTempC: const Value(18.0),
      humidityPct: const Value(null),
    );
    expect((updated.ambientTempC, updated.humidityPct), (18.0, null));
    final closed = await org.repos.sessions.close(session.id);
    expect(closed.closedAt, isNotNull);
    await expectLater(
      record({'pair': 'L1-PE', 'zs_ohm': 0.84}),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'session_closed')),
    );
    await expectLater(org.repos.sessions.close(session.id), throwsA(isA<DataRuleException>()));
    await expectLater(
      org.repos.sessions.updateConditions(session.id, ambientTempC: const Value(20.0)),
      throwsA(isA<DataRuleException>()),
    );
    expect((await org.repos.sessions.forSite(s.site.id)).map((x) => x.id), [session.id]);
  });

  test('tugun, asbob va normalar to\'plami tekshiriladi', () async {
    final other = await org.repos.sites.create(name: 'Boshqa');
    final foreign = await org.repos.graph.addNode(siteId: other.id, kind: NodeKind.load, label: 'M');
    await expectLater(
      record({'r_ohm': 0.01}, nodeId: foreign.id, type: MeasurementType.continuityBonding),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'node_not_in_site')),
    );
    await expectLater(
      org.repos.measurements.record(
        sessionId: session.id,
        nodeId: s.sock1.id,
        type: MeasurementType.loopImpedance,
        instrumentId: 'yoq',
        values: const {},
        enteredVia: EnteredVia.manual,
        normSetVersion: '0.2.0',
      ),
      throwsA(isA<NotFoundException>()),
    );
    await expectLater(
      org.repos.measurements.record(
        sessionId: session.id,
        nodeId: s.sock1.id,
        type: MeasurementType.loopImpedance,
        instrumentId: s.instrument.id,
        values: const {},
        enteredVia: EnteredVia.manual,
        normSetVersion: '9.9.9',
      ),
      throwsA(isA<NotFoundException>()),
    );
    await expectLater(record(const {}, sessionId: 'yoq'), throwsA(isA<NotFoundException>()));
    await expectLater(
      org.repos.sessions.start(siteId: 'yoq', kind: SessionKind.davriy, engineerId: org.user.id),
      throwsA(isA<NotFoundException>()),
    );
  });

  test('o\'chirilgan (soft delete) tugun o\'lchanmaydi', () async {
    await org.repos.graph.softDeleteNode(s.sock1.id);
    await expectLater(record({'pair': 'L1-PE', 'zs_ohm': 0.84}), throwsA(isA<DataRuleException>()));
  });

  group('InstrumentRepository', () {
    test('qiyoslash muddati (oxirgi kun ham amal qiladi)', () async {
      final r = org.repos.instruments;
      expect(r.isVerificationValid(s.instrument, DateTime.utc(2027, 3, 1, 23, 59)), isTrue);
      expect(r.isVerificationValid(s.instrument, DateTime.utc(2027, 3, 2)), isFalse);
      final noDate = await r.create(kind: 'MEGGER', model: 'X', serialNo: '2');
      expect(r.isVerificationValid(noDate, DateTime.utc(2026)), isFalse, reason: 'muddat kiritilmagan — yaroqsiz');
      final up = await r.update(noDate.copyWith(verifiedUntil: Value(DateTime.utc(2030))));
      expect(r.isVerificationValid(up, DateTime.utc(2026)), isTrue);
      expect((await r.list()).length, 2);
      await r.softDelete(noDate.id);
      expect((await r.list()).length, 1);
    });
  });
}
