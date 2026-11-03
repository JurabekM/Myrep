import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:havoradar/app.dart';
import 'package:havoradar/data/models.dart';
import 'package:havoradar/state/app_state.dart';
import 'package:havoradar/util/format.dart';

import 'fake_engine.dart';

Future<AppState> pumpApp(WidgetTester tester, FakeEngine engine) async {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final state = AppState(engine);
  await tester.pumpWidget(HavoRadarApp(state: state));
  await state.init();
  await tester.pumpAndSettle();
  return state;
}

/// Ko'rinib turgan (onstage) eng yuqori sahifadagi asosiy vertikal skroll.
Finder _scroll() => find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).last;

/// Ro'yxat dangasa quriladi: element ko'rinmaguncha aylantiramiz.
Future<void> reveal(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 200, scrollable: _scroll());
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> tapVisible(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  group('modellar (haqiqiy yadro chiqishi)', () {
    test("snapshot va katalog o'qiladi", () {
      final s = Snapshot.fromJson(fixture('snapshot.json'));
      expect(s.profile, ['ELDERLY']);
      expect(s.places.map((p) => p.id), ['tashkent', 'termez']);
      final tash = s.main!;
      expect(tash.localNow, DateTime(2026, 7, 15, 9));
      expect(tash.today!.level, 'EMERGENCY');
      expect(tash.days, hasLength(7));
      expect(tash.hours, hasLength(48));
      final today = tash.todayReport!;
      expect(today.tempMax, 41.5);
      expect(today.heatRisk!.base.level, 'WARNING');
      expect(today.heatRisk!.personal.level, 'EMERGENCY');
      expect(today.heatRisk!.reasons, isNotEmpty);
      expect(today.heatRisk!.advice.any((a) => a.contains('103')), isTrue);
      expect(today.uv!.name, 'Juda yuqori');
      expect(tash.days.last.airRisk, isNull, reason: 'CAMS prognozi 5 kun');
      expect(tash.hoursOn(DateTime(2026, 7, 15)), hasLength(15));
      expect(s.place('termez')!.days, isEmpty);
      expect(s.sources.map((x) => x.id), ['WEATHER', 'AIR']);

      final c = Catalog.fromJson(fixture('catalog.json'));
      expect(c.placeName('termez'), 'Termiz');
      expect(c.levels.map((l) => l.level), Level.order);
      expect(c.vulnerabilities.map((v) => v.id), contains('LUNG'));
      expect(c.guide.first.id, 'heat_stroke');
      expect(c.guide.every((g) => g.sources.every((s) => s.url.startsWith('https://'))), isTrue);
    });

    test('sozlamalar JSON aylanmasi', () {
      const s = Settings(placeId: 'samarkand', extraPlaces: ['mecca'], profile: ['LUNG'], alertThreshold: 'ADVISORY', quietHours: false);
      final back = Settings.fromJson(s.toJson());
      expect(back.placeId, 'samarkand');
      expect(back.extraPlaces, ['mecca']);
      expect(back.profile, ['LUNG']);
      expect(back.alertThreshold, 'ADVISORY');
      expect(back.quietHours, isFalse);
      expect(back.allPlaces, ['samarkand', 'mecca']);
    });
  });

  group('formatlash', () {
    test('kun va daraja yorliqlari', () {
      final today = DateTime(2026, 7, 15, 9);
      expect(dayLabel(DateTime(2026, 7, 15), today), 'Bugun');
      expect(dayLabel(DateTime(2026, 7, 16), today), 'Ertaga');
      expect(dayLabel(DateTime(2026, 7, 17), today), 'Juma');
      expect(deg(41.46), '41°');
      expect(deg(null), '—');
      expect(hourLabel(7), '07:00');
      expect(formatShortDate(DateTime(2026, 7, 15)), '15-iyul');
    });
  });

  testWidgets('birinchi ishga tushish: onboarding → profil → ruxsat → yangilash', (tester) async {
    final engine = FakeEngine(settings: const Settings(), withSnapshot: false);
    await pumpApp(tester, engine);
    expect(find.text('HavoRadar'), findsOneWidget);
    await reveal(tester, find.text('Toshkent'));

    await tapVisible(tester, find.text('Astma yoki surunkali o\'pka kasalligi'));
    expect(engine.saved.last.profile, ['LUNG']);

    await tapVisible(tester, find.text('Boshlash'));
    expect(engine.calls, containsAllInOrder(['permission', 'refresh:tashkent']));
    expect(engine.saved.last.onboardingDone, isTrue);
    expect(find.text('Radar'), findsOneWidget);
    expect(find.text('Bugun'), findsWidgets);
  });

  testWidgets("Radar: bugungi xavf, kartalar va kun tafsiloti", (tester) async {
    final engine = FakeEngine();
    await pumpApp(tester, engine);
    expect(find.text('Toshkent'), findsWidgets);
    expect(find.text('Bugungi xavf — profilingiz hisobga olingan'), findsOneWidget);
    // Issiqlik kartasi → kun tafsiloti.
    await tapVisible(tester, find.textContaining('Eng yuqori 42°C'));
    expect(find.text('Nega bu daraja?'), findsWidgets);
    expect(find.text('Harorat (soatlik)'), findsOneWidget);
    expect(find.textContaining('Umumiy aholi uchun: Xavfli'), findsOneWidget);
    await reveal(tester, find.text('Havo sifati'));
    await tapVisible(tester, find.text('Yaqinlarga ulashish'));
    expect(engine.calls.last, startsWith('share:Toshkent, 15-iyul:'));
  });

  testWidgets("joylar o'rtasida almashish va shoshilinch qo'ng'iroq", (tester) async {
    final engine = FakeEngine();
    final state = await pumpApp(tester, engine);
    await tester.tap(find.widgetWithText(ChoiceChip, 'Termiz'));
    await tester.pumpAndSettle();
    expect(state.viewed!.id, 'termez');
    expect(find.text("Bugun uchun prognoz yo'q"), findsOneWidget);

    await tapVisible(tester, find.byIcon(Icons.call));
    expect(engine.calls.last, 'dial:103');
  });

  testWidgets('bildirishnomadan ochilganda tegishli joy ko\'rsatiladi', (tester) async {
    final state = await pumpApp(tester, FakeEngine(launchPlaceId: 'termez'));
    expect(state.viewed!.id, 'termez');
  });

  testWidgets("prognoz va ma'lumotnoma", (tester) async {
    final engine = FakeEngine();
    await pumpApp(tester, engine);
    await tester.tap(find.text('Prognoz'));
    await tester.pumpAndSettle();
    expect(find.text('Keyingi 48 soat'), findsOneWidget);
    await reveal(tester, find.text('Ertaga'));

    await tester.tap(find.text("Ma'lumotnoma"));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Issiq urishi'));
    await tester.pumpAndSettle();
    expect(find.text('Belgilari'), findsOneWidget);
    await tester.tap(find.textContaining('103 — tez yordam'));
    expect(engine.calls.last, 'dial:103');
    await tapVisible(tester, find.textContaining('CDC NIOSH'));
    expect(engine.opened.last, startsWith('https://www.cdc.gov/niosh/'));
  });

  testWidgets('sozlamalar: profil, chegara, qo\'shimcha joy olib tashlash', (tester) async {
    final engine = FakeEngine();
    await pumpApp(tester, engine);
    await tester.tap(find.byTooltip('Sozlamalar'));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Olib tashlash'));
    await tester.pumpAndSettle();
    expect(engine.saved.last.extraPlaces, isEmpty);
    expect(engine.calls.last, 'refresh:tashkent', reason: "joylar o'zgarsa — yangilanadi");

    await tapVisible(tester, find.text('Qandli diabet'));
    expect(engine.saved.last.profile, containsAll(['ELDERLY', 'DIABETES']));

    await tapVisible(tester, find.widgetWithText(ChoiceChip, 'Ehtiyot'));
    expect(engine.saved.last.alertThreshold, 'ADVISORY');
  });

  testWidgets("internet bo'lmasa — xato banneri, eski ma'lumot qoladi", (tester) async {
    final engine = FakeEngine()..failRefresh = true;
    final state = await pumpApp(tester, engine);
    await state.refresh();
    await tester.pumpAndSettle();
    expect(find.textContaining("Yangilab bo'lmadi"), findsOneWidget);
    await reveal(tester, find.text('Issiqlik'));
  });

  testWidgets("yorug' mavzu ixtiyoriy, standart — qorong'i", (tester) async {
    await pumpApp(tester, FakeEngine());
    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(app.themeMode, ThemeMode.dark);
  });
}
