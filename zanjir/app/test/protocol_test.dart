import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

import 'support/harness.dart';

/// Imzolashga tayyor: tekshirilgan (test) normalar, litsenziya, o'lchovlar, yopilgan sessiya.
Future<(TestEnv, DemoSite, String)> signableSession(
  WidgetTester tester, {
  String role = 'LEAD',
  bool needsReview = false,
  bool close = true,
  bool license = true,
  bool reviewedNorms = true,
}) async {
  final (env, demo, sessionId) = await startWithSession(tester, role: role);
  final repos = await env.repos(tester);
  final norms = reviewedNorms ? await env.io(tester, reviewedTestNorms) : null;
  await env.io(tester, () async {
    final version = norms == null ? '0.3.0' : (await repos.normSets.import(norms)).version;
    if (license) {
      final lead = role == 'LEAD' || role == 'ADMIN'
          ? env.profile!.userId
          : (await repos.users.create(fullName: 'Rahbar', phone: '+998', role: 'LEAD')).id;
      await repos.settings.updateLab(
        byUserId: lead,
        name: 'Elektrolab',
        licenseNo: 'EL-0042',
        licenseValidUntil: DateTime.utc(2027, 12, 31),
      );
    }
    Future<void> loop(String pair) => repos.measurements.record(
      sessionId: sessionId,
      nodeId: demo.xs1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: demo.instrument.id,
      values: {'pair': pair, 'zs_ohm': 0.84},
      enteredVia: EnteredVia.manual,
      normSetVersion: version,
    );
    await loop('L1-PE');
    if (needsReview) await loop('L1-N');
    if (close) await repos.sessions.close(sessionId);
  });
  return (env, demo, sessionId);
}

Future<void> tapAndSettle(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await settle(tester, frames: 40);
}

void main() {
  testWidgets('imzolash: FLAG_SECURE, tasdiqlash, QR, hash, tekshiruv, ulashish, bekor qilish', (tester) async {
    final (env, _, sessionId) = await signableSession(tester);
    await goTo(tester, '/sessions/$sessionId/protocol');
    expect(env.secureScreen.enabled, isTrue, reason: 'imzolash ekranida ekranshot taqiqlangan');
    expect(find.text('Bloklovchi shart yo\'q — imzolash mumkin.'), findsOneWidget);

    await tapAndSettle(tester, find.byKey(const Key('protocol.sign')));
    expect(
      find.text(
        'Imzolangan protokolni o\'zgartirib bo\'lmaydi — faqat sabab bilan bekor qilinadi. '
        'Ma\'lumotlar to\'g\'riligini tasdiqlaysizmi?',
      ),
      findsOneWidget,
    );
    await tapAndSettle(tester, find.byKey(const Key('protocol.confirmSign')));

    final repos = await env.repos(tester);
    final row = (await env.io(tester, () => repos.protocols.forSession(sessionId))).single;
    final doc = (await env.io(tester, () => repos.protocols.document(row.id)))!;
    expect(row.number, matches(RegExp(r'^2026-[0-9A-F]{6}-001$')));
    expect(find.text('№ ${row.number}'), findsOneWidget);
    expect(find.text('Amalda'), findsOneWidget);
    expect(find.byType(QrImageView), findsOneWidget);
    final payload = jsonDecode(doc.payloadJson) as Map<String, Object?>;
    final url = (payload['protocol']! as Map)['verify_url']! as String;
    expect(url, 'zanjir://app/v/${row.qrToken}');
    expect(find.text(url), findsOneWidget);
    expect(find.text(row.payloadSha256), findsOneWidget);
    expect(find.text(row.pdfSha256), findsOneWidget);
    expect(find.text('Imzo va hash\'lar to\'g\'ri'), findsOneWidget);
    expect(find.byKey(const Key('protocol.sign')), findsNothing, reason: 'amaldagi protokol bor');
    expect(pdfDocumentId(doc.pdf), row.payloadSha256);
    expect(payload['lead_comment'], isNull);
    expect((payload['protocol']! as Map)['language'], 'uz');

    await tapAndSettle(tester, find.byKey(const Key('protocol.share')));
    expect(env.pdfActions.shared.single.$1, 'ZANJIR-${row.number}.pdf');
    expect(sha256Hex(env.pdfActions.shared.single.$2), row.pdfSha256);
    await tapAndSettle(tester, find.byKey(const Key('protocol.print')));
    expect(env.pdfActions.printed, ['ZANJIR-${row.number}']);

    await tapAndSettle(tester, find.byKey(const Key('protocol.revoke')));
    await tester.enterText(find.byKey(const Key('protocol.revokeReason')), 'Obyekt manzili xato');
    await tapAndSettle(tester, find.widgetWithText(FilledButton, 'Protokolni bekor qilish'));
    expect(await env.io(tester, () => repos.protocols.status(row.id)), ProtocolStatus.revoked);
    expect(find.text('Bekor qilingan'), findsOneWidget);
    expect(find.byKey(const Key('protocol.sign')), findsOneWidget, reason: 'qayta imzolash mumkin');

    await goTo(tester, '/');
    expect(env.secureScreen.enabled, isFalse);
    expect(env.secureScreen.calls, ['enable', 'disable']);
    await env.dispose(tester);
  });

  testWidgets('bloklovchi shartlar ko\'rsatiladi, tugma o\'chiq', (tester) async {
    final (env, _, sessionId) = await signableSession(tester, close: false, license: false, reviewedNorms: false);
    await goTo(tester, '/sessions/$sessionId/protocol');
    for (final code in ['session_open', 'license_missing']) {
      expect(find.byKey(Key('protocol.blocker.$code')), findsOneWidget, reason: code);
    }
    // Tekshirilmagan normalar imzolashni to'xtatmaydi (ADR-0019) — faqat ogohlantirish.
    expect(find.byKey(const Key('protocol.blocker.norms_not_reviewed')), findsNothing);
    expect(find.byKey(const Key('protocol.normsUnreviewed')), findsOneWidget);
    expect(find.text('Normalar to\'plami 0.3.0 litsenziyali muhandis tomonidan tekshirilmagan'), findsOneWidget);
    expect(tester.widget<ButtonStyleButton>(find.byKey(const Key('protocol.sign'))).onPressed, isNull);
    await env.dispose(tester);
  });

  testWidgets('NEEDS_REVIEW: LEAD izohisiz imzolay olmaydi; izoh PDF payload\'iga yoziladi; ruscha', (tester) async {
    final (env, _, sessionId) = await signableSession(tester, needsReview: true);
    await goTo(tester, '/sessions/$sessionId/protocol');
    expect(find.byKey(const Key('protocol.blocker.lead_comment_required')), findsOneWidget);
    expect(tester.widget<ButtonStyleButton>(find.byKey(const Key('protocol.sign'))).onPressed, isNull);

    await tester.enterText(find.byKey(const Key('protocol.comment')), 'L1-N qayta o\'lchanadi');
    await settle(tester);
    expect(find.byKey(const Key('protocol.blocker.lead_comment_required')), findsNothing);
    await tapAndSettle(tester, find.text('Русский'));
    await tapAndSettle(tester, find.byKey(const Key('protocol.sign')));
    await tapAndSettle(tester, find.byKey(const Key('protocol.confirmSign')));

    final repos = await env.repos(tester);
    final row = (await env.io(tester, () => repos.protocols.forSession(sessionId))).single;
    final doc = (await env.io(tester, () => repos.protocols.document(row.id)))!;
    final payload = jsonDecode(doc.payloadJson) as Map<String, Object?>;
    expect(payload['lead_comment'], 'L1-N qayta o\'lchanadi');
    expect((payload['protocol']! as Map)['language'], 'ru');
    expect(payload['summary'], containsPair('NEEDS_REVIEW', 1));
    await env.dispose(tester);
  });

  testWidgets('QR havola zanjir://app/v/<token>: topilgan va topilmagan protokol', (tester) async {
    final (env, _, sessionId) = await signableSession(tester);
    final repos = await env.repos(tester);
    final signed = await env.io(tester, () async {
      final fonts = ProtocolFonts(
        regular: await assetBytes('assets/fonts/NotoSans-Regular.ttf'),
        bold: await assetBytes('assets/fonts/NotoSans-Bold.ttf'),
        symbols: await assetBytes('assets/fonts/NotoSansMath-Regular.ttf'),
      );
      return repos.protocols.sign(await repos.protocols.prepare(sessionId: sessionId), fonts);
    });
    await goTo(tester, '/v/${signed.protocol.qrToken}');
    expect(find.text('Protokolni tekshirish'), findsOneWidget);
    expect(find.text('№ ${signed.protocol.number}'), findsOneWidget);
    expect(find.text('Imzo va hash\'lar to\'g\'ri'), findsOneWidget);
    await goTo(tester, '/v/yoq');
    expect(find.textContaining('Bu qurilmada bunday protokol topilmadi'), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('sozlamalar: laboratoriya litsenziyasini LEAD kiritadi', (tester) async {
    final (env, _, _) = await startWithSession(tester);
    await goTo(tester, '/settings');
    await tapAndSettle(tester, find.byKey(const Key('settings.editLab')));
    await tester.enterText(find.byKey(const Key('lab.license')), 'EL-77');
    await tester.enterText(find.byKey(const Key('lab.until')), '2027-02-30');
    await tapAndSettle(tester, find.byKey(const Key('lab.save')));
    expect(find.text('Sana YYYY-MM-DD formatida'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('lab.until')), '2027-02-28');
    await tapAndSettle(tester, find.byKey(const Key('lab.save')));
    final repos = await env.repos(tester);
    final org = await env.io(tester, repos.settings.organization);
    expect((org.licenseNo, org.licenseValidUntil), ('EL-77', DateTime.utc(2027, 2, 28)));
    expect(find.textContaining('EL-77'), findsOneWidget);
    await env.dispose(tester);
  });
}
