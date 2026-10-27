import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart' show OrderingTerm, Variable;
import 'package:test/test.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/fake_server.dart';
import 'support/harness.dart';

Future<List<(String, String)>> outbox(ZanjirDatabase db) async => [
  for (final r in await (db.select(db.syncOutbox)..orderBy([(o) => OrderingTerm(expression: o.id)])).get())
    (r.tableName_, r.rowId),
];

/// Serverda ro'yxatdan o'tish natijasi: tashkilot, foydalanuvchi, qurilma (haqiqiy serverda — API orqali).
Future<void> seedApiRows(FakeServer server, ZanjirDatabase db) async {
  for (final t in ['organization', 'app_user', 'device']) {
    for (final r in await db.customSelect('SELECT * FROM $t').get()) {
      server.seed(t, rowToWire(wireColumns(db, t), r.data));
    }
  }
}

Future<int> count(ZanjirDatabase db, String table) async =>
    (await db.customSelect('SELECT count(*) AS n FROM $table').getSingle()).read<int>('n');

void main() {
  group('sinxronlash sxemasi shartnomasi (tools/vectors/sync_schema.json)', () {
    test('lokal jadvallar server ustunlariga mos (nom, tur, null)', () {
      final spec = jsonDecode(File('../../tools/vectors/sync_schema.json').readAsStringSync()) as Map<String, Object?>;
      final db = memoryDb();
      addTearDown(db.close);
      final tables = (spec['tables']! as List).cast<Map<String, Object?>>();
      expect([for (final t in tables) t['name']], syncTables);
      const types = {
        'text': WireType.text,
        'int': WireType.int,
        'real': WireType.real,
        'bool': WireType.bool,
        'datetime': WireType.datetime,
        'json_map': WireType.jsonMap,
        'json_list': WireType.jsonList,
        'base64': WireType.base64,
      };
      for (final t in tables) {
        final name = t['name']! as String;
        final local = wireColumns(db, name);
        final server = {
          for (final c in (t['columns']! as List).cast<Map<String, Object?>>()) c['name']! as String: types[c['type']]!,
        };
        expect(local, server, reason: name);
        expect(apiOnlyTables.contains(name), !(t['pushable']! as bool), reason: name);
        expect(appendOnlyTables.contains(name), t['append_only'], reason: name);
        final drift = db.allTables.firstWhere((x) => x.actualTableName == name);
        for (final c in (t['columns']! as List).cast<Map<String, Object?>>()) {
          final col = drift.$columns.firstWhere((x) => x.name == c['name']);
          expect(col.$nullable, c['nullable'], reason: '$name.${c['name']}');
        }
      }
    });
  });

  group('navbat (outbox)', () {
    late ZanjirDatabase db;
    late Org org;
    setUp(() async {
      db = memoryDb();
      org = await Org.create(db, 'A');
    });
    tearDown(() => db.close());

    test('yozuvlar navbatga tushadi; o\'zgarish yozuvni almashtiradi; app_user/device tushmaydi', () async {
      final before = await outbox(db);
      expect(before.map((e) => e.$1).toSet(), {'organization'});
      final site = await org.repos.sites.create(name: 'Obyekt');
      final first = (await db.select(db.syncOutbox).get()).last;
      await org.repos.sites.update(site.copyWith(name: 'Yangi'));
      final rows = await db.select(db.syncOutbox).get();
      final siteRows = rows.where((r) => r.rowId == site.id).toList();
      expect(siteRows, hasLength(1));
      expect(siteRows.single.opId, isNot(first.opId));
      expect(siteRows.single.opId, matches(RegExp(r'^[0-9a-f]{32}$')));
      expect((await outbox(db)).map((e) => e.$1), isNot(contains('app_user')));
    });

    test('o\'lchov: qator va audit hodisasi navbatda', () async {
      final s = await SignableSession.create(org);
      final tables = (await outbox(db)).map((e) => e.$1).toList();
      expect(tables, containsAll(['measurement', 'audit_event', 'measurement_session', 'node', 'norm_set']));
      expect(tables.where((t) => t == 'measurement'), hasLength(1));
      expect(s.measurement.id, isNotEmpty);
    });
  });

  group('SyncEngine (xotiradagi server bilan)', () {
    late ZanjirDatabase a;
    late Org orgA;
    late FakeServer server;
    setUp(() async {
      a = memoryDb();
      orgA = await Org.create(a, 'A');
      server = FakeServer();
      await seedApiRows(server, a);
    });
    tearDown(() => a.close());

    test('ikkinchi qurilma: push → pull → bir xil ma\'lumot; qayta sync — o\'zgarishsiz', () async {
      final s = await SignableSession.create(orgA);
      final engineA = SyncEngine(a, server, maxOps: 7);
      final pending = await engineA.pendingCount();
      final report = await engineA.run();
      expect(report.pushed + report.stale, pending, reason: 'tashkilot qatori serverda allaqachon bor (stale)');
      expect(await engineA.pendingCount(), 0);

      final b = memoryDb();
      addTearDown(b.close);
      final engineB = SyncEngine(b, server);
      final r2 = await engineB.run();
      expect(r2.pushed, 0);
      expect(await engineB.pendingCount(), 0, reason: 'serverdan kelgan qatorlar navbatga tushmaydi');
      for (final t in syncTables) {
        expect(await count(b, t), await count(a, t), reason: t);
      }
      final m = await MeasurementRepository(
        DataContext(db: b, orgId: orgA.ctx.orgId),
        audit: orgA.repos.audit,
        normSets: NormSetRepository(DataContext(db: b, orgId: orgA.ctx.orgId)),
      ).get(s.measurement.id);
      expect(m!.values, s.measurement.values);
      expect(m.verdict, s.measurement.verdict);
      expect(m.evalDetail, s.measurement.evalDetail);
      // Qayta sinxronlash — hech narsa o'zgarmaydi.
      expect((await engineA.run()).pushed, 0);
      expect((await engineB.run()).pulled, 0);
    });

    test('javob yo\'qolsa — qayta yuborish takror sifatida, ikki marta yozilmaydi', () async {
      await SignableSession.create(orgA);
      final engine = SyncEngine(a, server);
      final pending = await engine.pendingCount();
      server.dropNextResponse = true;
      await expectLater(engine.run(), throwsA(isA<ServerException>()));
      expect(await engine.pendingCount(), pending, reason: 'navbat saqlanadi');
      final report = await engine.run();
      expect(report.duplicates, pending);
      expect(report.pushed, 0);
      expect(report.stale, 0);
      expect(server.table('measurement'), hasLength(1));
    });

    test('rad etilgan paket — navbat saqlanadi, pull baribir bajariladi, qotgan yozuv aniqlanadi', () async {
      final engineA = SyncEngine(a, server);
      await engineA.run();
      final b = memoryDb();
      addTearDown(b.close);
      final engineB = SyncEngine(b, server);
      await engineB.run();
      final mine = await SiteRepository(DataContext(db: b, orgId: orgA.ctx.orgId)).create(name: 'B obyekti');
      final theirs = await orgA.repos.sites.create(name: 'A obyekti');
      await engineA.run();

      final op = (await (b.select(b.syncOutbox)..where((o) => o.rowId.equals(mine.id))).getSingle()).opId;
      server.rejectNext = ServerException(422, 'push_rejected', reason: 'audit_chain:bad_signature', opId: op);
      final n = await engineB.pendingCount();
      await expectLater(
        engineB.run(),
        throwsA(
          isA<SyncRejected>()
              .having((e) => e.reason, 'reason', 'audit_chain:bad_signature')
              .having((e) => e.table, 'table', 'site')
              .having((e) => e.rowId, 'rowId', mine.id),
        ),
      );
      expect(await engineB.pendingCount(), n, reason: 'navbat saqlanadi');
      expect(await SiteRepository(DataContext(db: b, orgId: orgA.ctx.orgId)).get(theirs.id), isNotNull);
      // Tarmoq xatosi — pull ham bajarilmaydi, xato o'zgarishsiz.
      server.rejectNext = const ServerException(0, 'unavailable');
      await expectLater(engineB.run(), throwsA(isNot(isA<SyncRejected>())));
    });

    test('LWW: yangiroq o\'zgarish ikkala qurilmada yutadi; eskisi navbatdan olinadi', () async {
      final site = await orgA.repos.sites.create(name: 'Asl');
      await SyncEngine(a, server).run();
      final b = memoryDb();
      addTearDown(b.close);
      final engineB = SyncEngine(b, server);
      await engineB.run();
      // A eski vaqt bilan, B yangi vaqt bilan o'zgartiradi (offline).
      await orgA.repos.sites.update(site.copyWith(name: 'A nomi', updatedAt: DateTime.utc(2026, 10, 26, 9), rev: 2));
      await b.customStatement(
        "UPDATE site SET name = 'B nomi', updated_at = '2026-10-26T10:00:00.000Z', rev = 2 WHERE id = ?",
        [site.id],
      );
      final rb = await engineB.run();
      expect(rb.pushed, 1);
      final ra = await SyncEngine(a, server).run();
      expect(ra.stale, 1, reason: 'A ning eski o\'zgarishi serverda rad etildi (LWW)');
      expect(ra.pulled, greaterThanOrEqualTo(1));
      final name =
          (await a.customSelect('SELECT name FROM site WHERE id = ?', variables: [Variable(site.id)]).getSingle())
              .read<String>('name');
      expect(name, 'B nomi');
      expect(await SyncEngine(a, server).pendingCount(), 0);
    });

    test('paketlar: audit birinchi, protokol hujjati bilan birga, chegara ≤ maxOps', () async {
      final s = await SignableSession.create(orgA);
      final draft = await orgA.repos.protocols.prepare(sessionId: s.session.id);
      await orgA.repos.protocols.sign(draft, testFonts());
      final calls = <List<Map<String, Object?>>>[];
      final engine = SyncEngine(a, _Recording(server, calls), maxOps: 3);
      await engine.run();
      final flat = [for (final c in calls) ...c];
      expect(calls.every((c) => c.length <= 4), isTrue, reason: 'protokol+hujjat birligi bo\'linmaydi');
      final firstNonAudit = flat.indexWhere((o) => o['table'] != 'audit_event');
      expect(flat.skip(firstNonAudit).any((o) => o['table'] == 'audit_event'), isFalse);
      final batchOfProtocol = calls.firstWhere((c) => c.any((o) => o['table'] == 'protocol'));
      expect(batchOfProtocol.any((o) => o['table'] == 'protocol_document'), isTrue);
      final seqs = [
        for (final o in flat)
          if (o['table'] == 'audit_event') ((o['row']! as Map)['seq']! as int),
      ];
      expect(seqs, [for (var i = 1; i <= seqs.length; i++) i]);
      final doc = flat.firstWhere((o) => o['table'] == 'protocol_document')['row']! as Map;
      expect(base64Decode(doc['pdf']! as String).take(5), utf8.encode('%PDF-'));
    });
  });
}

class _Recording implements SyncTransport {
  _Recording(this.inner, this.calls);
  final SyncTransport inner;
  final List<List<Map<String, Object?>>> calls;

  @override
  Future<PullPage> pull(int since, {int? limit}) => inner.pull(since, limit: limit);

  @override
  Future<Map<String, String>> push(List<Map<String, Object?>> ops) {
    calls.add(ops);
    return inner.push(ops);
  }
}
