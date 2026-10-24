import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump_app.dart';

void main() {
  const privateTitles = {
    AppRoutes.home: 'Bosh sahifa',
    AppRoutes.incomeNew: 'Yangi daromad',
    AppRoutes.expenses: 'Shu oyning xarajatlari',
    AppRoutes.expenseNew: 'Yangi xarajat',
    AppRoutes.obligations: 'Majburiyatlar',
    AppRoutes.nasiya: 'Nasiya daftari',
    AppRoutes.whoseMoney: 'Kimning puli?',
    AppRoutes.members: 'Oila aʼzolari',
    AppRoutes.settings: 'Sozlamalar',
    AppRoutes.vault: 'Kelajagim',
    AppRoutes.vaultRule: 'Ulush sozlamalari',
    AppRoutes.vaultWithdraw: 'Kelajagimdan pul olish',
    AppRoutes.vaultLumpSum: 'Katta summa tushdi',
    AppRoutes.audit: 'Oylik audit',
    AppRoutes.content: 'Boblar',
    AppRoutes.categories: 'Kategoriyalar va toifalar',
    AppRoutes.templates: 'Shablonlar',
    AppRoutes.havas: 'Havas va odatlar',
    AppRoutes.subscriptions: 'Obunalar va avtotoʻlovlar',
    AppRoutes.envelopes: 'Konvertlar',
    AppRoutes.rescue: 'Qutqarilgan pul',
    AppRoutes.prices: 'Narx daftari',
    AppRoutes.mouse: 'Inflyatsiya taʼsiri',
    AppRoutes.debts: 'Qarzlar',
    AppRoutes.debtNew: 'Qarz qoʻshish',
    AppRoutes.debtPlan: 'Qarzdan chiqish rejasi',
    AppRoutes.debtRecovery: 'Qarzdan chiqish rejimi',
    AppRoutes.sellables: 'Sotiladigan buyumlar',
    AppRoutes.ceremonies: 'Marosimlar',
    AppRoutes.partnerships: 'Sheriklik',
    AppRoutes.partnershipNew: 'Shartnoma tuzish',
    AppRoutes.ideas: 'Hunardan ishga',
    AppRoutes.ideaNew: 'Gʻoya hisobi',
    AppRoutes.offerCheck: 'Taklifni tekshirish',
    AppRoutes.backup: 'Zaxira nusxa',
    AppRoutes.agreements: 'Kelishuvlar',
    AppRoutes.agreementOral: 'Ogʻzaki kelishuvni yozib olish',
    // Onboarding tugagan foydalanuvchi bosh sahifaga qaytariladi.
    AppRoutes.onboarding: 'Bosh sahifa',
  };

  test('har bir marshrut hisobga olingan', () {
    expect(
      {...privateTitles.keys, ...AppRoutes.public},
      unorderedEquals(AppRoutes.all),
    );
  });

  testWidgets('ilova qulf ekranidan boshlanadi', (tester) async {
    await pumpBarakaApp(tester, unlock: false);
    expect(find.text('PIN kodni kiriting'), findsOneWidget);
  });

  for (final MapEntry(key: route, value: title) in privateTitles.entries) {
    testWidgets('$route placeholder ekranni ochadi', (tester) async {
      final env = await pumpBarakaApp(tester);
      env.container.read(appRouterProvider).go(route);
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, title), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('bosh sahifa → boʻlimlar va orqaga', (tester) async {
    await pumpBarakaApp(tester);
    expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);

    for (final route in [
      AppRoutes.vault,
      AppRoutes.expenses,
      AppRoutes.obligations,
      AppRoutes.nasiya,
      AppRoutes.audit,
      AppRoutes.whoseMoney,
      AppRoutes.content,
    ]) {
      await tapNav(tester, route);
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, privateTitles[route]!), findsOne);
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
    }
  });
}
