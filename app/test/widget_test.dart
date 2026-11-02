import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rostor2/ui/call_screen.dart';
import 'package:rostor2/ui/check_screen.dart';
import 'package:rostor2/ui/home_screen.dart';
import 'package:rostor2/ui/learn_screen.dart';
import 'package:rostor2/ui/theme.dart';

Future<void> pumpPhone(WidgetTester tester, Widget w) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.75;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(theme: buildTheme(), home: w));
  await tester.pump();
}

void main() {
  // Regressiya: "Ulashish" orqali kelgan matn initState'da FocusScope.of(context) ni chaqirib
  // ekranni qizil xato bilan yiqitardi (emulyatorda topilgan).
  testWidgets('CheckScreen ulashilgan matn bilan ochiladi', (tester) async {
    await pumpPhone(tester, const CheckScreen(initialText: "Kartangiz bloklandi. SMS kodni bizga ayting. Zudlik bilan!"));
    expect(tester.takeException(), isNull);
    expect(find.text('Xavfli'), findsOneWidget);
    expect(find.text("SMS kodni so'rash"), findsOneWidget);
  });

  testWidgets('CheckScreen tugma orqali tekshiradi', (tester) async {
    await pumpPhone(tester, const CheckScreen());
    await tester.enterText(find.byType(TextField), 'http://click.uz@evil.top/login');
    await tester.tap(find.text('Tekshirish'));
    await tester.pump();
    expect(find.text('Manzil aldamchi tuzilgan'), findsOneWidget);
  });

  testWidgets('Bosh ekran va bo\'limlar ko\'rinadi', (tester) async {
    await pumpPhone(tester, const HomeScreen());
    for (final t in ['Qurilmani tekshirish', 'APK faylni tekshirish', 'Havola yoki xabarni tekshirish', 'Qurilma auditi']) {
      expect(find.text(t), findsOneWidget, reason: t);
    }
    await tester.scrollUntilVisible(find.text("Qo'ng'iroq Qalqoni"), 200);
    expect(find.text("Qo'ng'iroq Qalqoni"), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Firibgarlik turlari'), 200);
    expect(find.text('Firibgarlik turlari'), findsOneWidget);
  });

  testWidgets("Firibgarlik turlari ekrani", (tester) async {
    await pumpPhone(tester, const LearnScreen());
    expect(tester.takeException(), isNull);
    expect(find.text('Asosiy qoida'), findsOneWidget);
  });

  testWidgets("Qo'ng'iroq Qalqoni: holat, raqam tekshiruvi va bloklash", (tester) async {
    final kv = <String, String>{};
    const ch = MethodChannel('uz.rostor.rostor2/native');
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(ch, (call) async {
      final a = (call.arguments as Map?) ?? const {};
      switch (call.method) {
        case 'callStatus':
          return {'supported': true, 'roleHeld': true, 'notifications': true, 'notificationsAskable': false, 'sdkInt': 36};
        case 'kvGet':
          return kv[a['key']];
        case 'kvSet':
          kv[a['key'] as String] = a['value'] as String;
          return null;
        case 'checkPhone':
          return {
            'normalized': '+79123456789',
            'display': '+79123456789',
            'severity': 'medium',
            'findings': [
              {'code': 'call.international', 'severity': 'medium', 'title': 'Xorijiy raqam (Rossiya)', 'explain': 'x', 'evidence': null},
            ],
            'official': [],
          };
      }
      return null;
    });
    addTearDown(() => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(ch, null));
    await pumpPhone(tester, const CallScreen());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.text('Qalqon yoqilgan'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '+7 912 345 67 89');
    await tester.tap(find.text('Tekshirish'));
    await tester.pumpAndSettle();
    expect(find.text('Xorijiy raqam (Rossiya)'), findsOneWidget);
    await tester.tap(find.text('Bu raqamni bloklash'));
    await tester.pumpAndSettle();
    expect(kv['call_blocklist'], '["+79123456789"]');
    expect(find.text('Blokdan chiqarish'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('BLOKLANGAN RAQAMLAR (1)'), 200, scrollable: find.byType(Scrollable).first);
    expect(find.text('BLOKLANGAN RAQAMLAR (1)'), findsOneWidget);
  });
}
