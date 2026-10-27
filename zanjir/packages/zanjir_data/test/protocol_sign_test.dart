import 'dart:convert';
import 'dart:typed_data';

import 'package:drift/drift.dart' show Value;
import 'package:sqlite3/sqlite3.dart' show SqliteException;
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

import 'support/harness.dart';

Matcher blockedBy(String code) => throwsA(
  isA<DataRuleException>()
      .having((e) => e.code, 'code', 'protocol_blocked')
      .having((e) => e.detail, 'detail', contains(code)),
);

Matcher ruleError(String code, [String? detail]) => throwsA(
  isA<DataRuleException>()
      .having((e) => e.code, 'code', code)
      .having((e) => e.detail, 'detail', detail == null ? anything : contains(detail)),
);

List<String> codes(ProtocolDraft d) => [for (final b in d.blockers) b.code];

void main() {
  late ZanjirDatabase db;
  late Org org;
  final fonts = testFonts();
  var token = 0;
  String nextToken() => (++token).toRadixString(16).padLeft(32, '0');

  /// Boshqa foydalanuvchi (rol) yoki soat bilan — shu qurilma va kalit.
  Future<Repositories> reposAs({String? role, DateTime Function()? clock}) async {
    var actor = org.user.id;
    if (role != null) {
      actor = (await org.repos.users.create(
        fullName: '$role F.I.Sh.',
        phone: '+998',
        role: role,
        safetyGroup: 'IV',
      )).id;
    }
    final ctx = DataContext(db: db, orgId: org.ctx.orgId, clock: clock ?? steppingClock(DateTime.utc(2026, 10, 27)));
    return Repositories(ctx, signer: org.signer, deviceId: org.device.id, actorId: actor, newQrToken: nextToken);
  }

  setUp(() async {
    db = memoryDb();
    org = await Org.create(db, 'A');
  });
  tearDown(() => db.close());

  group('imzolash', () {
    test('to\'liq oqim: payload → deterministik PDF → imzo → hujjat va audit', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final draft = await repos.protocols.prepare(sessionId: s.session.id, verifyBaseUrl: 'https://example.test/v/');
      expect(draft.blockers, isEmpty);
      final p = draft.payload;
      expect(p['schema'], protocolPayloadSchema);
      final protocol = p['protocol']! as Map;
      final dev = org.device.id.replaceAll('-', '').toUpperCase();
      expect(protocol['number'], '2026-${dev.substring(dev.length - 6)}-001');
      expect(protocol['verify_url'], 'https://example.test/v/${protocol['qr_token']}');
      expect(protocol['qr_token'], matches(RegExp(r'^[0-9a-f]{32}$')));
      expect((p['measurements']! as List).single, containsPair('verdict', 'PASS'));
      expect((p['measurements']! as List).single, containsPair('node_label', 'XS1'));
      expect((p['measurements']! as List).single, containsPair('norm_id', isNotNull));
      expect((p['measurements']! as List).single, containsPair('limit', isA<num>()));
      expect(p['summary'], {'total': 1, 'PASS': 1, 'FAIL': 0, 'NEEDS_REVIEW': 0, 'NOT_APPLICABLE': 0});
      expect((p['instruments']! as List).single, containsPair('cert_no', 'QV-2026/123'));
      expect(p['norm_set'], containsPair('version', reviewedTestVersion));

      final signed = await repos.protocols.sign(draft, fonts);
      final row = signed.protocol;
      expect(row.payloadSha256, draft.payloadSha256);
      expect(row.pdfSha256, sha256Hex(signed.document.pdf));
      expect(row.signedBy, org.user.id);
      expect(row.deviceId, org.device.id);
      expect(row.sigAlg, sigAlgEd25519);
      expect(pdfDocumentId(signed.document.pdf), row.payloadSha256);
      expect(await repos.protocols.verify(row.id), isNull);
      expect(await repos.protocols.status(row.id), ProtocolStatus.active);
      expect((await repos.protocols.forSession(s.session.id)).single.id, row.id);
      expect((await repos.protocols.byQrToken(row.qrToken))?.id, row.id);
      expect(await repos.protocols.byQrToken('yoq'), isNull);

      // Saqlangan payload'dan qayta render — baytma-bayt bir xil (ADR-0010).
      final stored = (jsonDecode(signed.document.payloadJson) as Map).cast<String, Object?>();
      expect(await renderProtocolPdf(stored, fonts), equals(signed.document.pdf));

      final event = (await repos.audit.forEntity(row.id, eventType: 'PROTOCOL_SIGNED')).single;
      expect(
        event.payloadHash,
        sha256Hex(
          canonicalJsonBytes({
            'id': row.id,
            'session_id': row.sessionId,
            'number': row.number,
            'payload_sha256': row.payloadSha256,
            'pdf_sha256': row.pdfSha256,
            'signature': row.signature,
            'sig_alg': row.sigAlg,
            'qr_token': row.qrToken,
          }),
        ),
      );
      expect((await repos.audit.verify()).ok, isTrue);
    });

    test('bekor qilingandan keyin qayta imzolanadi — keyingi raqam', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final first = await repos.protocols.sign(await repos.protocols.prepare(sessionId: s.session.id), fonts);
      expect(codes(await repos.protocols.prepare(sessionId: s.session.id)), ['already_signed']);
      await repos.protocols.revoke(first.protocol.id, reason: 'Obyekt nomi xato');
      expect(await repos.protocols.status(first.protocol.id), ProtocolStatus.revoked);
      final second = await repos.protocols.sign(await repos.protocols.prepare(sessionId: s.session.id), fonts);
      expect(second.protocol.number, endsWith('-002'));
      expect(await repos.protocols.forSession(s.session.id), hasLength(2));
    });

    test('ruscha protokol', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final signed = await repos.protocols.sign(
        await repos.protocols.prepare(sessionId: s.session.id, language: 'ru'),
        fonts,
      );
      expect(await repos.protocols.verify(signed.protocol.id), isNull);
      await expectLater(
        repos.protocols.prepare(sessionId: s.session.id, language: 'en'),
        ruleError('unsupported_language'),
      );
    });
  });

  group('bloklash shartlari (CLAUDE.md, 6-qoida)', () {
    test('ochiq sessiya', () async {
      final s = await SignableSession.create(org, close: false);
      final draft = await (await reposAs()).protocols.prepare(sessionId: s.session.id);
      expect(codes(draft), ['session_open']);
      await expectLater((await reposAs()).protocols.sign(draft, fonts), blockedBy('session_open'));
    });

    test('o\'lchovsiz sessiya', () async {
      final s = await SignableSession.create(org);
      final empty = await org.repos.sessions.start(
        siteId: s.site.site.id,
        kind: SessionKind.davriy,
        engineerId: org.user.id,
      );
      await org.repos.sessions.close(empty.id);
      final draft = await (await reposAs()).protocols.prepare(sessionId: empty.id);
      expect(codes(draft), ['no_measurements']);
      expect(draft.payload['summary'], containsPair('total', 0));
    });

    test('qiyoslash muddati o\'tgan asbob bilan olingan o\'lchov', () async {
      final s = await SignableSession.create(org, close: false);
      final old = await org.repos.instruments.create(
        kind: 'MULTIFUNCTION',
        model: 'Eski',
        serialNo: 'SN-OLD',
        verifiedUntil: DateTime.utc(2026, 1, 1),
      );
      final noCert = await org.repos.instruments.create(kind: 'MULTIFUNCTION', model: 'Guvohnomasiz', serialNo: 'SN-0');
      final m1 = await recordLoop(org, s.session.id, s.site, zs: 0.5, instrumentId: old.id);
      final m2 = await recordLoop(org, s.session.id, s.site, zs: 0.6, instrumentId: noCert.id);
      await org.repos.sessions.close(s.session.id);
      final draft = await (await reposAs()).protocols.prepare(sessionId: s.session.id);
      expect(draft.blockers, [
        ProtocolBlocker('instrument_expired', [m1.id, m2.id]),
      ]);
      // O'chirilgan asbob ham tekshiriladi va protokolda ko'rsatiladi.
      await org.repos.instruments.softDelete(old.id);
      final again = await (await reposAs()).protocols.prepare(sessionId: s.session.id);
      expect(again.blockers, [
        ProtocolBlocker('instrument_expired', [m1.id, m2.id]),
      ]);
      expect([
        for (final i in again.payload['instruments']! as List) (i as Map)['id'],
      ], containsAll([old.id, noCert.id]));
    });

    test('o\'lchov kuni amal qilgan guvohnoma — keyin muddati o\'tsa ham imzolanadi', () async {
      final s = await SignableSession.create(org);
      final later = steppingClock(DateTime.utc(2027, 6, 1));
      final draft = await (await reposAs(clock: later)).protocols.prepare(sessionId: s.session.id);
      expect(draft.blockers, isEmpty, reason: 'guvohnoma 2027-03-01 gacha, o\'lchov 2026-10-26 da');
    });

    test('muhandis tekshirmagan normalar va aralash to\'plamlar', () async {
      final s = await SignableSession.create(org, close: false);
      await recordLoop(org, s.session.id, s.site, zs: 0.5, normSetVersion: '0.1.0');
      await org.repos.sessions.close(s.session.id);
      final draft = await (await reposAs()).protocols.prepare(sessionId: s.session.id);
      expect(codes(draft), ['mixed_norm_sets', 'norms_not_reviewed']);
      expect(draft.blockers.first.ids, ['0.1.0', reviewedTestVersion]);
    });

    test('NEEDS_REVIEW: faqat LEAD va faqat izoh bilan', () async {
      final s = await SignableSession.create(org, close: false);
      final nr = await recordLoop(org, s.session.id, s.site, zs: 0.5, pair: 'L1-N');
      expect(nr.verdict, Verdict.needsReview);
      await org.repos.sessions.close(s.session.id);

      final engineer = await reposAs(role: 'ENGINEER');
      final byEngineer = await engineer.protocols.prepare(sessionId: s.session.id, leadComment: 'Izoh');
      expect(byEngineer.blockers, [
        ProtocolBlocker('needs_review_requires_lead', [nr.id]),
      ]);

      final lead = await reposAs();
      for (final comment in [null, '', '   ']) {
        final d = await lead.protocols.prepare(sessionId: s.session.id, leadComment: comment);
        expect(d.blockers, [
          ProtocolBlocker('lead_comment_required', [nr.id]),
        ], reason: '"$comment"');
      }
      final ok = await lead.protocols.prepare(
        sessionId: s.session.id,
        leadComment: '  L1-N juftligi qayta o\'lchanadi.  ',
      );
      expect(ok.blockers, isEmpty);
      expect(ok.payload['lead_comment'], 'L1-N juftligi qayta o\'lchanadi.');
      final signed = await lead.protocols.sign(ok, fonts);
      expect(await lead.protocols.verify(signed.protocol.id), isNull);
    });

    test('ENGINEER faqat NEEDS_REVIEW bo\'lmaganda imzolaydi; VIEWER va ADMIN — yo\'q', () async {
      final s = await SignableSession.create(org);
      final engineer = await reposAs(role: 'ENGINEER');
      expect((await engineer.protocols.prepare(sessionId: s.session.id)).blockers, isEmpty);
      for (final role in ['VIEWER', 'ADMIN']) {
        final d = await (await reposAs(role: role)).protocols.prepare(sessionId: s.session.id);
        expect(d.blockers, [
          ProtocolBlocker('forbidden_role', [role]),
        ]);
      }
    });

    test('litsenziya yo\'q yoki muddati o\'tgan', () async {
      final s = await SignableSession.create(org);
      final lab = org.repos.settings;
      await lab.updateLab(
        byUserId: org.user.id,
        name: 'Lab',
        licenseNo: 'EL-1',
        licenseValidUntil: DateTime.utc(2026, 10, 1),
      );
      expect(codes(await (await reposAs()).protocols.prepare(sessionId: s.session.id)), ['license_expired']);
      await lab.updateLab(byUserId: org.user.id, name: 'Lab', licenseNo: ' ', licenseValidUntil: DateTime.utc(2030));
      expect(codes(await (await reposAs()).protocols.prepare(sessionId: s.session.id)), ['license_missing']);
      await lab.updateLab(byUserId: org.user.id, name: 'Lab', licenseNo: 'EL-1');
      expect(codes(await (await reposAs()).protocols.prepare(sessionId: s.session.id)), ['license_missing']);
      // Oxirgi kun hali amal qiladi.
      await lab.updateLab(
        byUserId: org.user.id,
        name: 'Lab',
        licenseNo: 'EL-1',
        licenseValidUntil: DateTime.utc(2026, 10, 27),
      );
      expect((await (await reposAs()).protocols.prepare(sessionId: s.session.id)).blockers, isEmpty);
    });

    test('bekor qilingan qurilma', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final draft = await repos.protocols.prepare(sessionId: s.session.id);
      await org.repos.devices.revoke(org.device.id);
      expect(codes(await repos.protocols.prepare(sessionId: s.session.id)), ['device_not_trusted']);
      await expectLater(repos.protocols.sign(draft, fonts), blockedBy('device_not_trusted'));
      expect(await db.select(db.protocols).get(), isEmpty);
    });
  });

  group('qoralama eskirishi', () {
    test('qoralamadan keyin ma\'lumot o\'zgarsa — draft_stale, hech narsa yozilmaydi', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final draft = await repos.protocols.prepare(sessionId: s.session.id);
      await org.repos.settings.updateLab(
        byUserId: org.user.id,
        name: 'Boshqa nom',
        licenseNo: 'EL-0042',
        licenseValidUntil: DateTime.utc(2027, 12, 31),
      );
      await expectLater(repos.protocols.sign(draft, fonts), ruleError('draft_stale', 'changed'));
      expect(await db.select(db.protocols).get(), isEmpty);
      expect(await db.select(db.protocolDocuments).get(), isEmpty);
    });

    test('qo\'lda o\'zgartirilgan payload imzolanmaydi', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final draft = await repos.protocols.prepare(sessionId: s.session.id);
      final forged = ProtocolDraft(
        sessionId: draft.sessionId,
        payload: {
          ...draft.payload,
          'summary': {...(draft.payload['summary']! as Map), 'FAIL': 0, 'PASS': 99},
        },
        blockers: const [],
      );
      await expectLater(repos.protocols.sign(forged, fonts), ruleError('draft_stale', 'changed'));
    });

    test('15 daqiqadan eski qoralama', () async {
      final s = await SignableSession.create(org);
      var now = DateTime.utc(2026, 10, 27, 9);
      final repos = await reposAs(clock: () => now);
      final draft = await repos.protocols.prepare(sessionId: s.session.id);
      now = now.add(const Duration(minutes: 16));
      await expectLater(repos.protocols.sign(draft, fonts), ruleError('draft_stale', 'expired'));
      now = now.subtract(const Duration(minutes: 2));
      expect((await repos.protocols.sign(draft, fonts)).protocol.number, endsWith('-001'));
    });
  });

  group('saqlash va tekshirish', () {
    test('hujjat append-only; buzilgan PDF yoki payload aniqlanadi', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final id = (await repos.protocols.sign(
        await repos.protocols.prepare(sessionId: s.session.id),
        fonts,
      )).protocol.id;
      await expectLater(db.customUpdate('update protocol_document set pdf = x\'00\''), throwsA(isA<SqliteException>()));
      await expectLater(db.customUpdate('delete from protocol_document'), throwsA(isA<SqliteException>()));

      // Trigger'ni chetlab o'tgan buzg'unchi (masalan, root qurilma) — tekshiruv baribir aniqlaydi.
      await db.customStatement('drop trigger protocol_document_append_only_update');
      final doc = (await repos.protocols.document(id))!;
      final pdf = Uint8List.fromList(doc.pdf);
      pdf[pdf.length ~/ 2] ^= 1;
      await (db.update(
        db.protocolDocuments,
      )..where((d) => d.id.equals(doc.id))).write(ProtocolDocumentsCompanion(pdf: Value(pdf)));
      expect(await repos.protocols.verify(id), 'pdf_hash_mismatch');

      final payload = (jsonDecode(doc.payloadJson) as Map).cast<String, Object?>()..['lead_comment'] = 'qo\'shilgan';
      await (db.update(db.protocolDocuments)..where((d) => d.id.equals(doc.id))).write(
        ProtocolDocumentsCompanion(pdf: Value(doc.pdf), payloadJson: Value(canonicalJson(payload))),
      );
      expect(await repos.protocols.verify(id), 'payload_hash_mismatch');
    });

    test('bekor qilish — faqat LEAD/ADMIN va sabab bilan; boshqa tashkilot ko\'rmaydi', () async {
      final s = await SignableSession.create(org);
      final repos = await reposAs();
      final id = (await repos.protocols.sign(
        await repos.protocols.prepare(sessionId: s.session.id),
        fonts,
      )).protocol.id;
      await expectLater(
        (await reposAs(role: 'ENGINEER')).protocols.revoke(id, reason: 'x'),
        ruleError('forbidden_role'),
      );
      await expectLater(repos.protocols.revoke(id, reason: '  '), ruleError('reason_required'));
      await (await reposAs(role: 'ADMIN')).protocols.revoke(id, reason: 'Xato');
      await expectLater(repos.protocols.revoke(id, reason: 'Yana'), ruleError('already_revoked'));

      final other = await Org.create(db, 'B');
      expect(await other.repos.protocols.get(id), isNull);
      expect(await other.repos.protocols.document(id), isNull);
      expect(await other.repos.protocols.byQrToken((await repos.protocols.get(id))!.qrToken), isNull);
      await expectLater(other.repos.protocols.verify(id), throwsA(isA<NotFoundException>()));
      await expectLater(other.repos.protocols.prepare(sessionId: s.session.id), throwsA(isA<NotFoundException>()));
    });
  });
}
