import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rostor2/core/db.dart';
import 'package:rostor2/core/report_draft.dart';
import 'package:rostor2/engine/text_rules.dart';
import 'package:rostor2/ui/check_screen.dart';
import 'package:rostor2/ui/quiz_screen.dart';
import 'package:rostor2/ui/report_screen.dart';
import 'package:rostor2/ui/theme.dart';

RostorDb loadDb() {
  final raw = File('../registry/registry.json').readAsStringSync();
  return RostorDb.fromPayload(raw, (jsonDecode(raw) as Map)['db_version'] as int);
}

Future<void> pumpPhone(WidgetTester tester, Widget w) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.75;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(theme: buildTheme(), home: w));
  await tester.pump();
}

void main() {
  final db = loadDb();

  group('Hisobot qoralamasi (F3)', () {
    test('vishing SMS: raqam, tashkilot va tur oldindan to\'ldiriladi', () {
      final r = analyzeText("Hurmatli mijoz! Uzcard kartangiz bloklandi. Tiklash uchun 90 123 45 67 raqamiga qo'ng'iroq qiling.", db);
      final d = draftFromText(r);
      expect(d.category, 'T2');
      expect(d.targetType, 'phone');
      expect(d.targetValue, '+998 90 123 45 67');
      expect(d.claimedOrg, 'Uzcard');
      expect(d.evidence.first.kind, 'sms_text');
      expect(d.findings.map((f) => f['code']), contains('text.phone_not_official'));
      expect(d.findings.map((f) => f['title']), contains("Uzcard nomidan rasmiy bo'lmagan raqam"));
      expect(d.findings.map((f) => f['code']), isNot(contains('text.no_signal')));
    });
    test('OLX havolasi: link va T5', () {
      final r = analyzeText("Pulni o'tkazdim. Pulni olish uchun karta ma'lumotini kiriting: http://olx-uz.delivery-safe.top/pay", db);
      final d = draftFromText(r);
      expect(d.category, 'T5');
      expect(d.targetType, 'link');
      expect(d.targetValue, 'olx-uz.delivery-safe.top');
      expect(d.evidence.map((e) => e.kind), containsAll(['sms_text', 'url']));
    });
    test("qo'ng'iroq tarixidan", () {
      final d = draftFromCall({'number': '+79123456789', 'display': '+79123456789', 'title': 'Xorijiy raqam (Rossiya)', 'code': 'call.international'}, '01.11.2026 13:35');
      expect(d.targetValue, '+79123456789');
      expect(d.evidence.single.value, contains('Xorijiy raqam'));
    });
  });

  testWidgets('Firibgar SMS tekshiruvidan hisobot tugmasi chiqadi', (tester) async {
    await pumpPhone(tester, const CheckScreen(initialText: "Kartangiz bloklandi. SMS kodni bizga ayting. Zudlik bilan!"));
    await tester.scrollUntilVisible(find.text('Firibgarlik haqida hisobot yaratish'), 200, scrollable: find.byType(Scrollable).first);
    expect(find.text('Firibgarlik haqida hisobot yaratish'), findsOneWidget);
  });

  testWidgets("Forma: imzolash va tayyor hisobot ko'rinishi", (tester) async {
    const ch = MethodChannel('uz.rostor.rostor2/native');
    Map<String, dynamic>? sent;
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(ch, (call) async {
      switch (call.method) {
        case 'createReport':
          sent = Map<String, dynamic>.from(call.arguments as Map);
          return {'name': 'R2-00112233AABB', 'readable': 'ROSTOR-2 FIRIBGARLIK HISOBOTI', 'deviceId': 'ab'};
        case 'readReport':
          return {'ok': true, 'error': null, 'readable': 'ROSTOR-2 FIRIBGARLIK HISOBOTI\nFiribgar — Telefon raqami: +998 90 123 45 67'};
      }
      return null;
    });
    addTearDown(() => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(ch, null));
    final draft = ReportDraft(category: 'T2', targetValue: '90 123 45 67', claimedOrg: 'Uzcard', evidence: [EvidenceItem('sms_text', 'Kartangiz bloklandi')]);
    await pumpPhone(tester, ReportFormScreen(draft: draft));
    expect(tester.takeException(), isNull);
    final btn = find.text('Hisobotni yaratish va imzolash');
    await tester.scrollUntilVisible(btn, 300, scrollable: find.byType(Scrollable).first);
    await tester.tap(btn);
    await tester.pumpAndSettle();
    expect(sent!['category'], 'T2');
    expect(sent!['targetValue'], '90 123 45 67');
    expect((sent!['evidence'] as List).single, {'kind': 'sms_text', 'value': 'Kartangiz bloklandi'});
    expect(find.text('Hisobot tayyor va imzolangan'), findsOneWidget);
    expect(find.text('Yuborish'), findsOneWidget);
  });

  testWidgets('Forma: turi tanlanmasa xato', (tester) async {
    await pumpPhone(tester, ReportFormScreen(draft: ReportDraft()));
    final btn = find.text('Hisobotni yaratish va imzolash');
    await tester.scrollUntilVisible(btn, 300, scrollable: find.byType(Scrollable).first);
    await tester.tap(btn);
    await tester.pump();
    expect(find.text('Firibgarlik turini tanlang'), findsOneWidget);
  });

  testWidgets("O'zingizni sinang: to'liq o'tish", (tester) async {
    await pumpPhone(tester, const QuizScreen());
    for (final q in quizQuestions) {
      await tester.tap(find.text(q.options[q.correct]));
      await tester.pump();
      expect(find.text("To'g'ri!"), findsOneWidget);
      final next = find.textContaining(RegExp('Keyingi savol|Natija'));
      await tester.scrollUntilVisible(next, 200, scrollable: find.byType(Scrollable).first);
      await tester.tap(next);
      await tester.pump();
    }
    expect(find.text('${quizQuestions.length} / ${quizQuestions.length}'), findsOneWidget);
  });
}
