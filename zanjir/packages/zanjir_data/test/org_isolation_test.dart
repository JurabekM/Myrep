import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

/// CLAUDE.md, 7-qoida (ilova tomoni): har bir so'rov `org_id` bilan filtrlanadi.
void main() {
  test('A tashkiloti B ning ma\'lumotini ko\'rmaydi va unga bog\'lana olmaydi', () async {
    final db = memoryDb();
    addTearDown(db.close);
    final a = await Org.create(db, 'A');
    final b = await Org.create(db, 'B');
    final sb = await SmallSite.create(b);
    final sessionB = await b.repos.sessions.start(
      siteId: sb.site.id,
      kind: SessionKind.davriy,
      engineerId: b.user.id,
      ambientTempC: 20,
    );
    final mB = await b.repos.measurements.record(
      sessionId: sessionB.id,
      nodeId: sb.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: sb.instrument.id,
      values: {'pair': 'L1-PE', 'zs_ohm': 0.84},
      enteredVia: EnteredVia.manual,
      normSetVersion: '0.2.0',
    );

    final r = a.repos;
    expect(await r.sites.list(), isEmpty);
    expect(await r.sites.get(sb.site.id), isNull);
    expect(await r.graph.nodes(sb.site.id), isEmpty);
    expect(await r.instruments.list(), isEmpty);
    expect(await r.measurements.get(mB.id), isNull);
    expect(await r.measurements.forSession(sessionB.id), isEmpty);
    expect(await r.sessions.get(sessionB.id), isNull);
    expect(await r.users.get(b.user.id), isNull);
    expect(await r.devices.get(b.device.id), isNull);
    expect(await r.audit.events(), isEmpty);
    await expectLater(r.normSets.load('0.2.0'), throwsA(isA<NotFoundException>()));
    await expectLater(r.graph.loadGraph(sb.site.id), throwsA(isA<NotFoundException>()));
    await expectLater(
      r.graph.addNode(siteId: sb.site.id, kind: NodeKind.load, label: 'X'),
      throwsA(isA<NotFoundException>()),
    );
    await expectLater(r.sites.update(sb.site), throwsA(isA<NotFoundException>()));
    await expectLater(r.graph.updateNode(sb.qf1), throwsA(isA<NotFoundException>()));
    await expectLater(r.sessions.close(sessionB.id), throwsA(isA<NotFoundException>()));
    await expectLater(r.devices.revoke(b.device.id), throwsA(isA<NotFoundException>()));
    await expectLater(
      r.sessions.start(siteId: sb.site.id, kind: SessionKind.davriy, engineerId: a.user.id),
      throwsA(isA<NotFoundException>()),
    );
    await expectLater(
      r.sessions.start(siteId: (await SmallSite.create(a)).site.id, kind: SessionKind.davriy, engineerId: b.user.id),
      throwsA(isA<NotFoundException>()),
      reason: 'boshqa tashkilot muhandisi',
    );
    await expectLater(
      r.devices.register(userId: b.user.id, publicKeyHex: 'aa', sigAlg: 'Ed25519'),
      throwsA(isA<NotFoundException>()),
    );
    // B o'z ma'lumotini ko'radi.
    expect((await b.repos.sites.list()).single.id, sb.site.id);
    expect((await b.repos.audit.verify()).ok, isTrue);
  });
}
