// Haqiqiy qurilma/emulyatorda to'liq oqim: Flutter UI → MethodChannel → Kotlin yadro → jonli internet.
// Ishga tushirish: flutter test integration_test/device_test.dart -d <qurilma>  (CI: tool/emulator_test.sh)
import 'package:epiradar/app.dart';
import 'package:epiradar/data/engine_api.dart';
import 'package:epiradar/state/app_state.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

Finder _scroll() => find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).last;

/// Tarmoq/yadro javobini kutish: kadrlarni chizib turib, shart bajarilguncha (ko'pi bilan [seconds]).
Future<void> waitFor(WidgetTester tester, bool Function() done, {int seconds = 150, String what = ''}) async {
  for (var i = 0; i < seconds * 2; i++) {
    if (done()) {
      await tester.pumpAndSettle();
      return;
    }
    await tester.pump(const Duration(milliseconds: 500));
  }
  fail('Kutish vaqti tugadi: $what');
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('to\'liq oqim: onboarding/radar → signallar → kasalliklar → tayyorgarlik → mamlakat', (tester) async {
    final engine = ChannelEngine();
    final permission = await engine.notificationStatus();
    // Android 13+ da ruxsat oynasi tizim dialogi — test uni bosa olmaydi, shuning uchun onboarding
    // faqat ruxsat talab qilinmaydigan qurilmalarda UI orqali o'tiladi.
    if (permission != 'granted') {
      final s = await engine.settings();
      await engine.saveSettings(s.copyWith(onboardingDone: true, country: 'UZB'));
    }
    final state = AppState(engine);
    await tester.pumpWidget(EpiRadarApp(state: state));
    // init() tarmoqni ham kutadi — kadrlarni chizish uchun await qilmaymiz.
    final initDone = state.init();
    await waitFor(tester, () => state.ready, what: 'init');

    if (!state.settings.onboardingDone) {
      debugPrint('EPIRADAR-IT: onboarding UI orqali (ruxsat: $permission)');
      await tester.scrollUntilVisible(find.text('Boshlash'), 300, scrollable: _scroll());
      await tester.tap(find.text('Boshlash'));
    }
    await initDone;
    await waitFor(tester, () => state.snapshot != null && !state.refreshing, what: 'birinchi sinxronlash');

    final snap = state.snapshot!;
    final ok = snap.sources.where((s) => s.ok).length;
    debugPrint('EPIRADAR-IT: ${snap.countryName}: ${snap.personal.score} (${snap.personal.name}), dunyo ${snap.global.score}; '
        'manbalar ok=$ok/${snap.sources.length}; hodisalar=${snap.events.length}');
    for (final e in snap.events.take(5)) {
      debugPrint('EPIRADAR-IT:   ${e.personal.score}/${e.global.score} ${e.title}');
    }
    expect(ok, greaterThanOrEqualTo(2), reason: 'manbalar: ${snap.sources.map((s) => '${s.id}:${s.ok}:${s.error}')}');
    expect(snap.events, isNotEmpty);
    expect(find.text("O'zbekiston uchun xavf darajasi"), findsOneWidget);
    expect(state.error, isNull);

    // Signallar → birinchi hodisa tafsiloti.
    await tester.tap(find.text('Signallar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text(snap.events.first.title).first);
    await tester.pumpAndSettle();
    expect(find.text('Nega bu daraja?'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();

    // Trendlar va kasalliklar ma'lumotnomasi.
    await tester.tap(find.text('Trendlar'));
    await tester.pumpAndSettle();
    expect(find.textContaining('JSST FluNet laboratoriya'), findsOneWidget);
    await tester.tap(find.text('Kasalliklar'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, 'Ebola');
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('Ebola virusi').first);
    await tester.pumpAndSettle();
    expect(find.text("Yuqish yo'li"), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();

    // Tayyorgarlik: belgi Kotlin SharedPreferences'ga saqlanadi.
    await tester.tap(find.text('Tayyorgarlik'));
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('Ichimlik suvi'));
    await tester.pumpAndSettle();
    final persisted = await engine.settings();
    expect(persisted.checklistDone, contains('water'));
    await state.toggleChecklist('water');

    // Mamlakatni UI orqali almashtirish → xavf qayta hisoblanadi.
    await tester.tap(find.text('Radar'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Sozlamalar').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mening mamlakatim'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Qozog');
    await tester.pumpAndSettle();
    await tester.tap(find.text("Qozog'iston"));
    await waitFor(tester, () => state.settings.country == 'KAZ' && state.snapshot?.country == 'KAZ' && !state.refreshing,
        what: 'mamlakat almashishi');
    debugPrint('EPIRADAR-IT: Qozog\'iston: ${state.snapshot!.personal.score} (${state.snapshot!.personal.name})');
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text("Qozog'iston uchun xavf darajasi"), findsOneWidget);

    // Asl holatga qaytarish (keyingi qadam — ilovani ishga tushirib ekranni olish — O'zbekiston bilan).
    await state.updateSettings(state.settings.copyWith(country: 'UZB'));
    await waitFor(tester, () => state.snapshot?.country == 'UZB' && !state.refreshing, what: 'qaytarish');
    debugPrint('EPIRADAR-IT: OK');
  });
}
