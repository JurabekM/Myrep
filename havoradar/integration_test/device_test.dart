// Haqiqiy qurilma/emulyatorda to'liq oqim: Flutter UI → MethodChannel → Kotlin yadro → jonli Open-Meteo.
// Ishga tushirish: flutter test integration_test/device_test.dart -d <qurilma>  (CI: tool/emulator_test.sh)
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:havoradar/app.dart';
import 'package:havoradar/data/engine_api.dart';
import 'package:havoradar/state/app_state.dart';
import 'package:integration_test/integration_test.dart';

Finder _scroll() => find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).last;

/// Tarmoq/yadro javobini kutish: kadrlarni chizib turib, shart bajarilguncha (ko'pi bilan [seconds]).
Future<void> waitFor(WidgetTester tester, bool Function() done, {int seconds = 120, String what = ''}) async {
  for (var i = 0; i < seconds * 2; i++) {
    if (done()) {
      await tester.pumpAndSettle();
      return;
    }
    await tester.pump(const Duration(milliseconds: 500));
  }
  fail('Kutish vaqti tugadi: $what');
}

/// Android'ning tizim «orqaga» tugmasi (foydalanuvchi aynan shuni bosadi).
Future<void> goBack(WidgetTester tester) async {
  await tester.binding.handlePopRoute();
  await tester.pumpAndSettle();
}

/// Dangasa ro'yxatda element ko'rinmaguncha aylantirib, bosish.
Future<void> tapVisible(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 200, scrollable: _scroll());
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets("to'liq oqim: radar → kun → prognoz → ma'lumotnoma → profil → shahar", (tester) async {
    final engine = ChannelEngine();
    final permission = await engine.notificationStatus();
    // Android 13+ da ruxsat oynasi tizim dialogi — test uni bosa olmaydi, shuning uchun onboarding
    // faqat ruxsat talab qilinmaydigan qurilmalarda UI orqali o'tiladi.
    if (permission != 'granted') {
      final s = await engine.settings();
      await engine.saveSettings(s.copyWith(onboardingDone: true, placeId: 'tashkent', extraPlaces: [], profile: []));
    }
    final state = AppState(engine);
    await tester.pumpWidget(HavoRadarApp(state: state));
    // init() tarmoqni ham kutadi — kadrlarni chizish uchun await qilmaymiz.
    final initDone = state.init();
    await waitFor(tester, () => state.ready, what: 'init');

    if (!state.settings.onboardingDone) {
      debugPrint('HAVORADAR-IT: onboarding UI orqali (ruxsat: $permission)');
      await tapVisible(tester, find.text('Boshlash'));
    }
    await initDone;
    await waitFor(tester, () => state.snapshot != null && !state.refreshing, what: 'birinchi sinxronlash');

    final snap = state.snapshot!;
    for (final s in snap.sources) {
      debugPrint('HAVORADAR-IT:   ${s.id} ok=${s.ok} ${s.error ?? ''}');
    }
    // Open-Meteo bepul limiti IP bo'yicha: umumiy CI IP'sida 429 bo'lsa — UI xatoni ko'rsatishi tekshiriladi xolos.
    if (snap.sources.every((s) => !s.ok && (s.error ?? '').contains('429'))) {
      debugPrint('HAVORADAR-IT: Open-Meteo limiti (HTTP 429) — jonli oqim o\'tkazib yuborildi');
      expect(find.textContaining("Prognozni yangilab bo'lmadi"), findsOneWidget);
      return;
    }
    expect(snap.sources.every((s) => s.ok), isTrue, reason: snap.sources.map((s) => '${s.id}:${s.error}').join('; '));
    final main = snap.main!;
    final today = main.todayReport!;
    debugPrint('HAVORADAR-IT: ${main.name}: bugun ${main.today?.score} (${main.today?.name}), '
        'issiq ${today.heatRisk?.base.score}, havo ${today.airRisk?.base.score}, ${main.days.length} kun');
    expect(today.heatRisk, isNotNull);
    expect(today.airRisk, isNotNull);
    expect(state.error, isNull);

    // Radar → issiqlik kartasi → kun tafsiloti.
    expect(find.text('Toshkent'), findsWidgets);
    await tapVisible(tester, find.text('Issiqlik').first);
    expect(find.text('Nega bu daraja?'), findsWidgets);
    await goBack(tester);

    // Prognoz: 48 soat grafigi va ertangi kun.
    await tester.tap(find.text('Prognoz'));
    await tester.pumpAndSettle();
    expect(find.text('Keyingi 48 soat'), findsOneWidget);
    await tapVisible(tester, find.text('Ertaga').first);
    expect(find.text('Nega bu daraja?'), findsWidgets);
    await goBack(tester);

    // Ma'lumotnoma: issiq urishi.
    await tester.tap(find.text("Ma'lumotnoma"));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Issiq urishi'));
    await tester.pumpAndSettle();
    expect(find.text('Belgilari'), findsOneWidget);
    await goBack(tester);

    // Sozlamalar: profil Kotlin SharedPreferences'ga saqlanadi, shahar almashsa prognoz yangilanadi.
    await tester.tap(find.text('Radar'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Sozlamalar').first);
    await tester.pumpAndSettle();
    await tapVisible(tester, find.text('Qandli diabet'));
    expect((await engine.settings()).profile, contains('DIABETES'));

    await tester.scrollUntilVisible(find.text('Asosiy joy'), -200, scrollable: _scroll());
    await tester.tap(find.text('Toshkent').first);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Samar');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Samarqand'));
    await waitFor(tester, () => state.snapshot?.main?.id == 'samarkand' && !state.refreshing, what: 'shahar almashishi');
    debugPrint('HAVORADAR-IT: Samarqand: bugun ${state.snapshot!.main!.today?.score} (${state.snapshot!.main!.today?.name})');
    await goBack(tester);
    expect(find.text('Samarqand'), findsWidgets);

    // Asl holatga qaytarish (keyingi qadam — ilovani ishga tushirib ekranni olish — Toshkent bilan).
    await state.updateSettings(state.settings.copyWith(placeId: 'tashkent', profile: []));
    await waitFor(tester, () => state.snapshot?.main?.id == 'tashkent' && !state.refreshing, what: 'qaytarish');
    debugPrint('HAVORADAR-IT: OK');
  });
}
