import 'dart:async';

import 'package:epiradar/app.dart';
import 'package:epiradar/data/models.dart';
import 'package:epiradar/state/app_state.dart';
import 'package:epiradar/ui/event_detail_screen.dart';
import 'package:epiradar/util/format.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_engine.dart';

Future<AppState> pumpApp(WidgetTester tester, FakeEngine engine) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final state = AppState(engine);
  await tester.pumpWidget(EpiRadarApp(state: state));
  await state.init();
  await tester.pumpAndSettle();
  return state;
}

/// Ko'rinib turgan (onstage) eng yuqori sahifadagi asosiy vertikal skroll.
Finder _scroll() => find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).last;

void main() {
  group('modellar (haqiqiy yadro chiqishi)', () {
    test('snapshot va katalog o\'qiladi', () {
      final s = Snapshot.fromJson(fixture('snapshot.json'));
      expect(s.country, 'UZB');
      expect(s.countryName, "O'zbekiston");
      expect(s.personal.level, 'ADVISORY');
      expect(s.global.level, 'EMERGENCY');
      expect(s.events, isNotEmpty);
      final ebola = s.events.first;
      expect(ebola.diseaseId, 'ebola');
      expect(ebola.sources, containsAll(['WHO_DON', 'ECDC', 'CDC_TRAVEL']));
      expect(ebola.reasons, isNotEmpty);
      expect(s.trends.map((t) => t.country), contains('KAZ'));
      expect(s.sources.every((x) => x.ok), isTrue);

      final c = Catalog.fromJson(fixture('catalog.json'));
      expect(c.disease('cchf')!.name, contains('Qrim-Kongo'));
      expect(c.countryName('KAZ'), "Qozog'iston");
      expect(c.levels.map((l) => l.level), Level.order);
    });

    test('sozlamalar JSON aylanmasi', () {
      const s = Settings(country: 'KAZ', watchCountries: ['TUR'], alertThreshold: 'WARNING', lightTheme: true);
      final back = Settings.fromJson(s.toJson());
      expect(back.country, 'KAZ');
      expect(back.watchCountries, ['TUR']);
      expect(back.alertThreshold, 'WARNING');
      expect(back.lightTheme, isTrue);
    });
  });

  group('formatlash', () {
    test('sana va sonlar', () {
      expect(formatInt(6234), '6 234');
      expect(formatInt(123), '123');
      expect(formatInt(1234567), '1 234 567');
      expect(formatShortDate(DateTime(2026, 10, 23)), '23-oktabr');
      final now = DateTime(2026, 10, 31, 12);
      expect(timeAgo(now.subtract(const Duration(minutes: 5)), now: now), '5 daqiqa oldin');
      expect(timeAgo(now.subtract(const Duration(days: 8)), now: now), '8 kun oldin');
    });

    test('tarjima havolasi https va kodlangan', () {
      final url = translateUrl("Ebola & Marburg: what's new?");
      expect(url, startsWith('https://translate.google.com/'));
      expect(Uri.parse(url).queryParameters['text'], "Ebola & Marburg: what's new?");
      expect(Uri.parse(url).queryParameters['tl'], 'uz');
    });
  });

  testWidgets('birinchi ishga tushish: onboarding → ruxsat → yangilash', (tester) async {
    final engine = FakeEngine(settings: const Settings(), withSnapshot: false);
    await pumpApp(tester, engine);
    await tester.scrollUntilVisible(find.text('Boshlash'), 300, scrollable: _scroll());
    expect(find.text("O'zbekiston"), findsOneWidget);
    await tester.tap(find.text('Boshlash'));
    await tester.pumpAndSettle();
    expect(engine.calls, containsAllInOrder(['permission', 'refresh:UZB']));
    expect(engine.saved.last.onboardingDone, isTrue);
    expect(find.text('Radar'), findsOneWidget);
    expect(find.text("O'zbekiston uchun xavf darajasi"), findsOneWidget);
  });

  testWidgets('bosh ekran: shkala, eng muhim hodisa, shoshilinch qo\'ng\'iroq', (tester) async {
    final engine = FakeEngine();
    await pumpApp(tester, engine);
    expect(find.text('Ogohlik'), findsWidgets);
    expect(find.textContaining('Ebola virusi kasalligi'), findsWidgets);
    await tester.scrollUntilVisible(find.byIcon(Icons.call), 300, scrollable: _scroll());
    expect(find.text('Tez tibbiy yordam — 103'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.call));
    expect(engine.calls, contains('dial:103'));

    await tester.scrollUntilVisible(find.text('JSST — Kasallik avj olishi xabarlari (DON)'), 300, scrollable: _scroll());
    expect(find.text('JSST — Kasallik avj olishi xabarlari (DON)'), findsOneWidget);
  });

  testWidgets('signallar: filtr, tafsilot, manba va tarjima', (tester) async {
    final engine = FakeEngine();
    await pumpApp(tester, engine);
    await tester.tap(find.text('Signallar'));
    await tester.pumpAndSettle();
    expect(find.textContaining('ta hodisa ·'), findsOneWidget);

    await tester.tap(find.text('Ogohlik va yuqori'));
    await tester.pumpAndSettle();
    expect(find.text('1 ta hodisa · Siz uchun xavf'), findsOneWidget);

    await tester.tap(find.textContaining('Ebola virusi kasalligi').first);
    await tester.pumpAndSettle();
    expect(find.text('Nega bu daraja?'), findsOneWidget);
    expect(find.textContaining('JSST xalqaro ahamiyatdagi favqulodda holat'), findsWidgets);
    expect(find.textContaining('CDC sayohat darajasi 4/4'), findsOneWidget);

    await tester.scrollUntilVisible(find.text('Manbani ochish'), 400, scrollable: _scroll());
    await tester.tap(find.text('Manbani ochish').first);
    await tester.ensureVisible(find.text("O'zbekchaga tarjima").first);
    await tester.pumpAndSettle();
    await tester.tap(find.text("O'zbekchaga tarjima").first);
    expect(engine.opened.first, startsWith('https://'));
    expect(engine.opened.last, startsWith('https://translate.google.com/'));

    await tester.tap(find.byTooltip('Ulashish'));
    expect(engine.calls, contains('share'));
  });

  testWidgets('qidiruv mamlakat bo\'yicha ishlaydi', (tester) async {
    await pumpApp(tester, FakeEngine());
    await tester.tap(find.text('Signallar'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Rossiya');
    await tester.pumpAndSettle();
    expect(find.text('1 ta hodisa · Siz uchun xavf'), findsOneWidget);
    expect(find.text("Sababi noma'lum kasallik («X kasalligi») — Rossiya"), findsOneWidget);
  });

  testWidgets('trendlar va ma\'lumotnoma', (tester) async {
    await pumpApp(tester, FakeEngine());
    await tester.tap(find.text('Trendlar'));
    await tester.pumpAndSettle();
    expect(find.text("Qozog'iston"), findsWidgets);
    expect(find.text("Me'yorda"), findsOneWidget);
    expect(find.text("Ma'lumot yetarli emas"), findsWidgets);

    await tester.tap(find.text('Kasalliklar'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'Qrim');
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('Qrim-Kongo').first);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Qachon darhol shifokorga'), 300, scrollable: _scroll());
    await tester.scrollUntilVisible(find.textContaining('Markaziy Osiyoda, jumladan'), 300, scrollable: _scroll());
  });

  testWidgets('tayyorgarlik ro\'yxati sozlamalarda saqlanadi', (tester) async {
    final engine = FakeEngine();
    final state = await pumpApp(tester, engine);
    await tester.tap(find.text('Tayyorgarlik'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Oila tayyorgarligi: 0 /'), findsOneWidget);
    await tester.tap(find.textContaining('Ichimlik suvi'));
    await tester.pumpAndSettle();
    expect(state.settings.checklistDone, ['water']);
    expect(engine.saved.last.checklistDone, ['water']);
    expect(find.textContaining('Oila tayyorgarligi: 1 /'), findsOneWidget);
  });

  testWidgets('sozlamalar: chegara va mavzu', (tester) async {
    final engine = FakeEngine();
    await pumpApp(tester, engine);
    await tester.tap(find.byTooltip('Sozlamalar').first);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Xavf va undan yuqori'), 300);
    await tester.tap(find.text('Xavf va undan yuqori'));
    await tester.pumpAndSettle();
    expect(engine.saved.last.alertThreshold, 'WARNING');

    await tester.scrollUntilVisible(find.text("Yorug' mavzu"), 300);
    await tester.tap(find.text("Yorug' mavzu"));
    await tester.pumpAndSettle();
    expect(engine.saved.last.lightTheme, isTrue);
    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(app.themeMode, ThemeMode.light);
  });

  test('mamlakat sinxronlash paytida almashtirilsa, yangi sozlama bilan yana yangilanadi', () async {
    final engine = FakeEngine();
    final state = AppState(engine);
    await state.init();
    engine.calls.clear();
    engine.refreshGate = Completer<void>();
    final first = state.refresh();
    await Future<void>.delayed(Duration.zero);
    expect(state.refreshing, isTrue);
    final change = state.updateSettings(state.settings.copyWith(country: 'KAZ'));
    engine.refreshGate!.complete();
    await Future.wait([first, change]);
    expect(engine.calls.where((c) => c.startsWith('refresh')), ['refresh:UZB', 'refresh:KAZ']);
    expect(state.refreshing, isFalse);
  });

  testWidgets('sozlamalar o\'qilmasa onboarding emas, xato ekrani ko\'rsatiladi', (tester) async {
    final engine = FakeEngine()..failSettings = true;
    await pumpApp(tester, engine);
    expect(find.text('Boshlash'), findsNothing);
    expect(find.text('Qayta urinish'), findsOneWidget);
    engine.failSettings = false;
    await tester.tap(find.text('Qayta urinish'));
    await tester.pumpAndSettle();
    expect(find.text('Radar'), findsOneWidget);
    expect(engine.saved, isEmpty, reason: 'saqlangan sozlamalar ustiga yozilmadi');
  });
}
