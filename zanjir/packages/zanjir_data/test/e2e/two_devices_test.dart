@Tags(['e2e'])
library;

import 'dart:io';
import 'dart:math';

import 'package:drift/drift.dart' show Variable;
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../support/harness.dart';

/// E2E (8-faza mezoni): ikki qurilma oflayn ishlaydi → sinxronlash → o'lchovlar yo'qolmaydi va takrorlanmaydi;
/// audit zanjiri buzilsa server rad etadi. Haqiqiy FastAPI + PostgreSQL (`tools/e2e/run.sh`).
final String baseUrl = Platform.environment['ZANJIR_E2E_URL'] ?? 'http://127.0.0.1:18080';
const password = 'E2e-maxfiy-parol-1';
final _rnd = Random.secure();

String phone() => '+99890${List.generate(7, (_) => _rnd.nextInt(10)).join()}';

/// Bitta qurilma: o'z SQLite bazasi, kaliti, repozitoriylari va server mijozi.
class Device {
  Device._(this.db, this.api, this.signer);
  final ZanjirDatabase db;
  final ServerApi api;
  final Ed25519Signer signer;
  late Repositories repos;
  late String userId;
  late String deviceId;
  late final engine = SyncEngine(db, api, maxOps: 40);

  static Future<Device> create() async {
    final signer = await Ed25519Signer.fromSeed(List.generate(32, (_) => _rnd.nextInt(256)));
    return Device._(memoryDb(), ServerApi(baseUrl, tokens: MemoryTokenStore()), signer);
  }

  void bind(String orgId, String user, String device) {
    userId = user;
    deviceId = device;
    repos = Repositories(
      DataContext(db: db, orgId: orgId),
      signer: signer,
      deviceId: device,
      actorId: user,
    );
  }

  Future<int> count(String table, [String where = '1=1']) async =>
      (await db.customSelect('SELECT count(*) AS n FROM $table WHERE $where').getSingle()).read<int>('n');

  Future<Set<String>> ids(String table) async => {
    for (final r in await db.customSelect('SELECT id FROM $table').get()) r.read<String>('id'),
  };

  Future<void> close() async {
    api.close();
    await db.close();
  }
}

/// Server javobini "yo'qotadi": so'rov serverga yetadi, mijoz xato oladi.
class LossyTransport implements SyncTransport {
  LossyTransport(this.inner);
  final SyncTransport inner;

  @override
  Future<PullPage> pull(int since, {int? limit}) => inner.pull(since, limit: limit);

  @override
  Future<Map<String, String>> push(List<Map<String, Object?>> ops) async {
    await inner.push(ops);
    throw const ServerException(0, 'timeout');
  }
}

void main() {
  late Device a; // LEAD, laboratoriyani oflayn yaratgan
  late Device b; // ENGINEER, taklif bilan qo'shilgan
  late SmallSite site;
  late String leadPhone;

  setUpAll(() async {
    // --- A: oflayn profil (ilovadagi kabi), keyin serverda ro'yxatdan o'tish ---
    a = await Device.create();
    final orgId = await OrganizationRepository(a.db).create(name: 'E2E laboratoriya');
    final ctx = DataContext(db: a.db, orgId: orgId);
    leadPhone = phone();
    final lead = await UserRepository(ctx)
        .create(fullName: 'Rahbar E2E', phone: leadPhone, role: 'LEAD', safetyGroup: 'V');
    final dev = await DeviceRepository(ctx)
        .register(userId: lead.id, publicKeyHex: a.signer.publicKeyHex, sigAlg: a.signer.sigAlg);
    a.bind(orgId, lead.id, dev.id);
    await a.repos.normSets.import(reviewedTestYaml);
    await a.repos.settings.update(byUserId: lead.id, activeNormSetVersion: reviewedTestVersion);
    final licenseUntil = DateTime.utc(2027, 12, 31);
    await a.repos.settings.updateLab(
      byUserId: lead.id,
      name: 'E2E laboratoriya',
      licenseNo: 'EL-E2E',
      licenseValidUntil: licenseUntil,
    );
    site = await SmallSite.createWith(a.repos);
    final prefs = LocalPrefRepository(a.db);
    await prefs.set(LocalPrefRepository.orgId, orgId);
    await prefs.set(LocalPrefRepository.userId, lead.id);
    await prefs.set(LocalPrefRepository.deviceId, dev.id);
    // Ilovadagi "Laboratoriyani serverda ro'yxatdan o'tkazish" — o'z ID lari bilan, keyin to'liq push.
    final first = await ServerAccount(a.db, a.api).registerLab(password: password, publicKeyHex: a.signer.publicKeyHex);
    expect(first.pushed, greaterThan(10));
    expect(await a.engine.pendingCount(), 0);
    final org = await a.repos.settings.organization();
    expect((org.licenseNo, org.licenseValidUntil), ('EL-E2E', licenseUntil), reason: 'pull litsenziyani o\'chirmaydi');
    expect((await a.api.me()).id, lead.id);

    // --- B: taklif kodi, yangi qurilma, to'liq pull (ilovadagi `ServerAccount.join`) ---
    final code = await a.api.createInvite('ENGINEER');
    b = await Device.create();
    final joined = await ServerAccount(b.db, b.api).join(
      code: code,
      fullName: 'Muhandis E2E',
      phone: phone(),
      password: password,
      publicKeyHex: b.signer.publicKeyHex,
    );
    b.bind(joined.orgId, joined.userId, joined.deviceId);
    expect((await b.api.me()).role, 'ENGINEER');
    for (final t in ['site', 'node', 'edge', 'instrument', 'norm_set', 'org_setting', 'audit_event']) {
      expect(await b.count(t), await a.count(t), reason: t);
    }
  });

  tearDownAll(() async {
    await a.close();
    await b.close();
  });

  test('ikki qurilma oflayn → sync: o\'lchovlar yo\'qolmaydi va takrorlanmaydi', () async {
    // Ikkalasi oflayn: har biri o'z sessiyasida o'lchaydi, B bittasini qayta o'lchaydi (supersede).
    final sa = await a.repos.sessions.start(
      siteId: site.site.id,
      kind: SessionKind.davriy,
      engineerId: a.userId,
      ambientTempC: 18,
    );
    final sb = await b.repos.sessions.start(
      siteId: site.site.id,
      kind: SessionKind.davriy,
      engineerId: b.userId,
      ambientTempC: 21,
    );
    Future<MeasurementRow> loop(Device d, String session, double zs, {String? supersedes}) =>
        d.repos.measurements.record(
          sessionId: session,
          nodeId: site.sock1.id,
          type: MeasurementType.loopImpedance,
          instrumentId: site.instrument.id,
          values: {'pair': 'L1-PE', 'zs_ohm': zs},
          enteredVia: EnteredVia.manual,
          normSetVersion: reviewedTestVersion,
          supersedesId: supersedes,
        );
    for (final zs in [0.41, 0.52, 0.63]) {
      await loop(a, sa.id, zs);
    }
    final wrong = await loop(b, sb.id, 9.9);
    await loop(b, sb.id, 0.77, supersedes: wrong.id);
    await loop(b, sb.id, 0.88);

    // Sinxronlash: B, A, keyin yana B (A ning o'lchovlarini olish uchun).
    await b.engine.run();
    await a.engine.run();
    await b.engine.run();

    final aIds = await a.ids('measurement');
    final bIds = await b.ids('measurement');
    expect(aIds, hasLength(6));
    expect(bIds, aIds, reason: 'ikkala qurilmada bir xil to\'plam');
    expect(await a.count('measurement', "supersedes_id = '${wrong.id}'"), 1);

    // Server ham aynan shuni ko'radi (takrorlarsiz).
    final page = await a.api.pull(0, limit: 500);
    final serverIds = [
      for (final c in page.changes)
        if (c.table == 'measurement') c.row['id'],
    ];
    expect(serverIds.toSet(), aIds);
    expect(serverIds, hasLength(serverIds.toSet().length));

    // Yana sinxronlash — hech narsa yuborilmaydi va olinmaydi.
    for (final d in [a, b]) {
      final r = await d.engine.run();
      expect((r.pushed, r.pulled), (0, 0));
    }
    // Audit zanjirlari ikkala qurilmada ham to'g'ri.
    expect((await a.repos.audit.verify()).ok, isTrue);
    expect((await b.repos.audit.verify()).ok, isTrue);
  });

  test('javob yo\'qolsa: qayta yuborish ikki marta yozmaydi', () async {
    final s = await a.repos.sessions.start(
      siteId: site.site.id,
      kind: SessionKind.davriy,
      engineerId: a.userId,
      ambientTempC: 18,
    );
    await a.repos.measurements.record(
      sessionId: s.id,
      nodeId: site.cab1.id,
      type: MeasurementType.continuityBonding,
      instrumentId: site.instrument.id,
      values: {'r_ohm': 0.03},
      enteredVia: EnteredVia.manual,
      normSetVersion: reviewedTestVersion,
    );
    final before = await a.count('measurement');
    final pending = await a.engine.pendingCount();
    await expectLater(SyncEngine(a.db, LossyTransport(a.api)).run(), throwsA(isA<ServerException>()));
    expect(await a.engine.pendingCount(), pending);
    final r = await a.engine.run();
    expect(r.duplicates, pending, reason: 'server avval qabul qilgan — hammasi takror');
    expect(r.pushed, 0);
    await b.engine.run();
    expect(await b.count('measurement'), before);
  });

  test('LWW: kechroq o\'zgarish ikkala qurilmada yutadi', () async {
    final row = (await a.repos.sites.get(site.site.id))!;
    await a.repos.sites.update(row.copyWith(name: 'A nomi'));
    await Future<void>.delayed(const Duration(milliseconds: 20));
    final rowB = (await b.repos.sites.get(site.site.id))!;
    await b.repos.sites.update(rowB.copyWith(name: 'B nomi'));
    await a.engine.run();
    final rb = await b.engine.run();
    expect(rb.pushed, 1);
    final ra = await a.engine.run();
    expect(ra.pulled, greaterThanOrEqualTo(1));
    expect((await a.repos.sites.get(site.site.id))!.name, 'B nomi');
    expect((await b.repos.sites.get(site.site.id))!.name, 'B nomi');
  });

  test('buzilgan audit zanjiri — server paketni to\'liq rad etadi, hech narsa saqlanmaydi', () async {
    final s = await b.repos.sessions.start(
      siteId: site.site.id,
      kind: SessionKind.davriy,
      engineerId: b.userId,
      ambientTempC: 20,
    );
    final m = await b.repos.measurements.record(
      sessionId: s.id,
      nodeId: site.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: site.instrument.id,
      values: {'pair': 'L1-PE', 'zs_ohm': 0.5},
      enteredVia: EnteredVia.manual,
      normSetVersion: reviewedTestVersion,
    );
    // Qurilmadagi buzg'unchi (root): trigger o'chirilib, hodisa o'zgartiriladi.
    final original =
        (await b.db
                .customSelect('SELECT payload_hash FROM audit_event WHERE entity_id = ?', variables: [Variable(m.id)])
                .getSingle())
            .read<String>('payload_hash');
    await b.db.customStatement('DROP TRIGGER audit_event_append_only_update');
    await b.db.customStatement("UPDATE audit_event SET payload_hash = '${'0' * 64}' WHERE entity_id = ?", [m.id]);
    final pending = await b.engine.pendingCount();
    await expectLater(
      b.engine.run(),
      throwsA(
        isA<ServerException>()
            .having((e) => e.code, 'code', 'push_rejected')
            .having((e) => e.reason, 'reason', startsWith('audit_chain:')),
      ),
    );
    expect(await b.engine.pendingCount(), pending, reason: 'navbat saqlanadi');
    final page = await a.api.pull(0, limit: 500);
    expect(page.changes.where((c) => c.row['id'] == m.id || c.row['id'] == s.id), isEmpty);

    // Asl qiymat tiklansa — xuddi shu navbat qabul qilinadi (hech narsa yo'qolmagan).
    await b.db.customStatement('UPDATE audit_event SET payload_hash = ? WHERE entity_id = ?', [original, m.id]);
    final r = await b.engine.run();
    expect(r.pushed, pending);
    await a.engine.run();
    expect(await a.count('measurement', "id = '${m.id}'"), 1);
  });

  test('yangi qurilmada kirish: hamma narsa serverdan; boshqa profil ustiga kirib bo\'lmaydi', () async {
    final c = await Device.create();
    addTearDown(c.close);
    final ids = await ServerAccount(
      c.db,
      c.api,
    ).login(phone: leadPhone, password: password, publicKeyHex: c.signer.publicKeyHex);
    expect((ids.orgId, ids.userId), (a.repos.ctx.orgId, a.userId));
    expect(ids.deviceId, isNot(a.deviceId));
    expect(await c.ids('measurement'), await a.ids('measurement'));
    await expectLater(
      ServerAccount(b.db, b.api).login(phone: leadPhone, password: password, publicKeyHex: b.signer.publicKeyHex),
      throwsA(isA<StateError>().having((e) => e.message, 'message', 'profile_mismatch')),
    );
    await expectLater(
      c.api.login(phone: leadPhone, password: 'noto\'g\'ri-parol-123'),
      throwsA(isA<ServerException>().having((e) => e.code, 'code', 'invalid_credentials')),
    );
  });

  test('protokol: A imzolaydi → server qabul qiladi → ochiq sahifa va PDF → B tekshiradi', () async {
    final s = await a.repos.sessions.start(
      siteId: site.site.id,
      kind: SessionKind.davriy,
      engineerId: a.userId,
      ambientTempC: 19,
    );
    await a.repos.measurements.record(
      sessionId: s.id,
      nodeId: site.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: site.instrument.id,
      values: {'pair': 'L1-PE', 'zs_ohm': 0.84},
      enteredVia: EnteredVia.manual,
      normSetVersion: reviewedTestVersion,
    );
    await a.repos.sessions.close(s.id);
    final draft = await a.repos.protocols.prepare(sessionId: s.id, verifyBaseUrl: '$baseUrl/v/');
    expect(draft.blockers, isEmpty);
    final signed = await a.repos.protocols.sign(draft, testFonts());
    await a.engine.run();

    final page = await a.api.getPublic('v/${signed.protocol.qrToken}');
    expect(page.statusCode, 200);
    expect(page.body, contains(signed.protocol.number));
    expect(page.body, contains(signed.protocol.pdfSha256));
    expect(page.body, contains('id="signature" class="ok"'));
    final pdf = await a.api.getPublic('v/${signed.protocol.qrToken}/pdf');
    expect(pdf.bodyBytes, signed.document.pdf);

    await b.engine.run();
    expect(await b.repos.protocols.verify(signed.protocol.id), isNull, reason: 'B da A ning imzosi tekshiriladi');

    // LEAD bekor qiladi → sahifa holati.
    await a.repos.protocols.revoke(signed.protocol.id, reason: 'E2E');
    await a.engine.run();
    final revoked = await a.api.getPublic('v/${signed.protocol.qrToken}');
    expect(revoked.body, contains('Bekor qilingan'));
    await b.engine.run();
    expect(await b.repos.protocols.status(signed.protocol.id), ProtocolStatus.revoked);
  });
}
