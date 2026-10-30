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

  group('AuditRepository', () {
    test('zanjir: seq 1 dan, prev_hash bog\'langan, imzolar to\'g\'ri', () async {
      final a = org.repos.audit;
      final e1 = await a.append(eventType: 'SETTINGS_CHANGED', entityId: null, payload: {'k_corr': 0.8});
      final e2 = await a.append(eventType: 'SITE_CREATED', entityId: 's-1', payload: {'name': 'X'});
      expect((e1.seq, e1.prevHash), (1, genesisHash));
      expect((e2.seq, e2.prevHash), (2, e1.eventHash));
      expect(e1.eventAt, matches(RegExp(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$')));
      expect(e1.sigAlg, sigAlgEd25519);
      expect((await a.events()).map((e) => e.seq), [1, 2]);
      expect((await a.verify()).ok, isTrue);
      final core = a.toCore(e2);
      expect(core.eventHash, e2.eventHash);
    });

    test('qurilma kaliti mos emas yoki qurilma bekor qilingan — yozilmaydi', () async {
      final wrongSigner = await Ed25519Signer.fromSeed(List.filled(32, 99));
      final wrong = AuditRepository(org.ctx, signer: wrongSigner, deviceId: org.device.id, actorId: org.user.id);
      await expectLater(
        wrong.append(eventType: 'X', entityId: null, payload: const {}),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'device_key_mismatch')),
      );
      await org.repos.devices.revoke(org.device.id);
      await expectLater(
        org.repos.audit.append(eventType: 'X', entityId: null, payload: const {}),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'device_revoked')),
      );
      final missing = AuditRepository(org.ctx, signer: org.signer, deviceId: 'yoq', actorId: org.user.id);
      await expectLater(
        missing.append(eventType: 'X', entityId: null, payload: const {}),
        throwsA(isA<NotFoundException>()),
      );
    });

    test('ikkinchi qurilma — alohida zanjir', () async {
      final signer2 = await Ed25519Signer.fromSeed(List.filled(32, 2));
      final d2 = await org.repos.devices.register(
        userId: org.user.id,
        publicKeyHex: signer2.publicKeyHex,
        sigAlg: signer2.sigAlg,
      );
      final audit2 = AuditRepository(org.ctx, signer: signer2, deviceId: d2.id, actorId: org.user.id);
      await org.repos.audit.append(eventType: 'A', entityId: null, payload: const {});
      final e = await audit2.append(eventType: 'B', entityId: null, payload: const {});
      expect((e.seq, e.prevHash), (1, genesisHash));
      expect((await audit2.verify()).ok, isTrue);
      expect(await org.repos.devices.get(d2.id), isNotNull);
    });
  });

  group('NormSetRepository', () {
    test('import: tekshiriladi, sha256 saqlanadi, takroriy import idempotent', () async {
      final r = org.repos.normSets;
      final row = await r.import(v0Yaml);
      expect(row.version, '0.3.0');
      expect(row.sha256, hasLength(64));
      expect(row.reviewedBy, isNull, reason: 'v0 tekshirilmagan');
      expect((await r.import(v0Yaml)).id, row.id);
      final set = await r.load('0.3.0');
      expect(set.norms, hasLength(21));
      await expectLater(r.load('9.9.9'), throwsA(isA<NotFoundException>()));
      await expectLater(r.import('schema_version: 1'), throwsA(isA<NormFormatException>()));
      final changed = v0Yaml.replaceFirst('margin_pct: 0', 'margin_pct: 5');
      await expectLater(
        r.import(changed),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'norm_set_version_conflict')),
      );
    });

    test('bazadagi YAML o\'zgartirilsa — sha256 mos emas, yuklanmaydi', () async {
      final row = await org.repos.normSets.import(v0Yaml);
      await db.customUpdate(
        "update norm_set set yaml = replace(yaml, 'value: 0.5', 'value: 0.05') where id = '${row.id}'",
      );
      await expectLater(
        org.repos.normSets.load('0.3.0'),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'norm_set_tampered')),
      );
    });
  });

  group('ProtocolRepository', () {
    // Imzolash va bloklash shartlari — protocol_sign_test.dart.
    test('raqam tashkilot ichida yagona (DB cheklovi)', () async {
      final s = await SmallSite.create(org);
      final session = await org.repos.sessions.start(
        siteId: s.site.id,
        kind: SessionKind.davriy,
        engineerId: org.user.id,
      );
      Future<void> insert(String number, String qr) => db
          .into(db.protocols)
          .insert(
            ProtocolsCompanion.insert(
              id: qr,
              orgId: org.ctx.orgId,
              sessionId: session.id,
              number: number,
              payloadSha256: 'a' * 64,
              pdfSha256: 'b' * 64,
              signedBy: org.user.id,
              deviceId: org.device.id,
              signature: 'c' * 128,
              sigAlg: sigAlgEd25519,
              qrToken: qr,
              createdAt: DateTime.utc(2026),
              updatedAt: DateTime.utc(2026),
            ),
          );
      await insert('P-1', 'qr-1');
      await expectLater(insert('P-1', 'qr-2'), throwsA(anything));
      await expectLater(insert('P-2', 'qr-1'), throwsA(anything), reason: 'qr_token ham yagona');
      await expectLater(org.repos.protocols.status('yoq'), throwsA(isA<NotFoundException>()));
    });
  });
}
