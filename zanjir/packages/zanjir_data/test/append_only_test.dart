import 'package:drift/native.dart';
import 'package:test/test.dart';

import 'support/harness.dart';

/// CLAUDE.md, 5-qoida: measurement, protocol (+ protocol_document), audit_event — UPDATE va DELETE yo'q.
void main() {
  test('append-only jadvallarda UPDATE/DELETE trigger bilan rad etiladi', () async {
    final db = memoryDb();
    addTearDown(db.close);
    final org = await Org.create(db, 'A');
    final signable = await SignableSession.create(org);
    final m = signable.measurement;
    final draft = await org.repos.protocols.prepare(sessionId: signable.session.id);
    await org.repos.protocols.sign(draft, testFonts());

    for (final (table, id) in [
      ('measurement', m.id),
      ('protocol', null),
      ('protocol_document', null),
      ('audit_event', null),
    ]) {
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
