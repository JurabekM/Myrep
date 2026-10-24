import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

// Savol muharriri: bitta sessiyada bir nechta maydon yozilganda oldingilari
// yo'qolmasligi. Oldin muharrir build vaqtidagi nusxadan o'qirdi — bitta
// maydon yozilgach, boshqasi uni jim o'chirardi (release sinovi, OPEN 113-115).

Future<void> reveal(WidgetTester tester, Finder f) async {
  final scrollable = find.byType(Scrollable).first;
  if (f.evaluate().isEmpty) {
    await tester.scrollUntilVisible(f, 200, scrollable: scrollable);
  }
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

Future<void> typeIn(WidgetTester tester, Finder f, String text) async {
  await reveal(tester, f);
  await tester.enterText(f, text);
  await tester.pump();
}

/// Ijara kelishuvi yaratiladi (2 tomon) va uning ro'yxat ekrani ochiq turadi.
Future<void> openRentAgreement(WidgetTester tester) async {
  final env = await pumpBarakaApp(tester);
  env.container.read(appRouterProvider).go(AppRoutes.agreements);
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const Key('ag-new')));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const Key('ag-new-rent')));
  await tester.pumpAndSettle();
  await typeIn(tester, find.byKey(const Key('ag-new-title')), 'Doʻkon ijarasi');
  await typeIn(tester, find.byKey(const Key('ag-new-me')), 'Akmal');
  await typeIn(tester, find.byKey(const Key('ag-new-other')), 'Bahodir');
  await tester.tap(find.byKey(const Key('ag-new-ok')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('savol 7: qiymat va toʻlov bitta sessiyada birga saqlanadi', (
    tester,
  ) async {
    await openRentAgreement(tester);
    await tapIn(tester, find.byKey(const Key('ag-q-7')));
    await typeIn(
      tester,
      find.byKey(const Key('ag-exit-valuation')),
      'Bozor narxi',
    );
    await typeIn(tester, find.byKey(const Key('ag-exit-payout')), 'Naqd pul');
    await tapIn(tester, find.byKey(const Key('ag-q-save')));
    expect(find.textContaining('Bozor narxi · Naqd pul'), findsOneWidget);
  });

  testWidgets('savol 6: matn yozilgach taraf tanlansa, matn yoʻqolmaydi', (
    tester,
  ) async {
    await openRentAgreement(tester);
    await tapIn(tester, find.byKey(const Key('ag-q-6')));
    await typeIn(tester, find.byKey(const Key('ag-custody-where')), 'Naqd');
    await tapIn(tester, find.byKey(const Key('ag-custody-keeper')));
    await tapIn(tester, find.text('Akmal').last);
    await tapIn(tester, find.byKey(const Key('ag-q-save')));
    expect(find.textContaining('Naqd · Akmal'), findsOneWidget);
  });

  testWidgets('savol 4: ikki sherik ulushi bitta sessiyada saqlanadi', (
    tester,
  ) async {
    await openRentAgreement(tester);
    await tapIn(tester, find.byKey(const Key('ag-q-4')));
    await typeIn(tester, find.byKey(const Key('ag-profit-0')), '60');
    await typeIn(tester, find.byKey(const Key('ag-profit-1')), '40');
    await tapIn(tester, find.byKey(const Key('ag-q-save')));
    expect(find.textContaining('Akmal 60 %, Bahodir 40 %'), findsOneWidget);
  });
}
