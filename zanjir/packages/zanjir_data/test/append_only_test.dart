import 'package:drift/native.dart';
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'support/harness.dart';

/// CLAUDE.md, 5-qoida: measurement, protocol, audit_event — UPDATE va DELETE yo'q.
void main() {
  test('append-only jadvallarda UPDATE/DELETE trigger bilan rad etiladi', () async {
    final db = memoryDb();
    addTearDown(db.close);
    final org = await Org.create(db, 'A');
    final s = await SmallSite.create(org);
    final session = await org.repos.sessions.start(
      siteId: s.site.id,
      kind: SessionKind.davriy,
      engineerId: org.user.id,
      ambientTempC: 20,
    );
    final m = await org.repos.measurements.record(
      sessionId: session.id,
      nodeId: s.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: s.instrument.id,
      values: {'pair': 'L1-PE', 'zs_ohm': 0.84},
      enteredVia: EnteredVia.manual,
      normSetVersion: '0.1.0',
    );
    await org.repos.protocols.insert(
      sessionId: session.id,
      number: 'P-1',
      payloadSha256: 'a' * 64,
      pdfSha256: 'b' * 64,
      signedBy: org.user.id,
      signature: 'c' * 128,
      sigAlg: sigAlgEd25519,
      qrToken: 'qr-1',
    );

    for (final (table, id) in [('measurement', m.id), ('protocol', null), ('audit_event', null)]) {
      final where = id == null ? '' : " where id = '$id'";
      await expectLater(
        db.customUpdate('update $table set rev = rev + 1$where'),
        throwsA(isA<SqliteException>().having((e) => e.message, 'message', contains('append_only: $table'))),
        reason: table,
      );
      await expectLater(
        db.customUpdate('delete from $table$where'),
        throwsA(isA<SqliteException>().having((e) => e.message, 'message', contains('append_only: $table'))),
        reason: table,
      );
    }
    // Ma'lumot joyida.
    expect(await org.repos.measurements.get(m.id), isNotNull);
    expect((await org.repos.audit.verify()).ok, isTrue);
  });
}
