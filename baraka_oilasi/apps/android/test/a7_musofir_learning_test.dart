// A7: Musofir — «O'zimga sarmoya» (M6, musofir/SPEC 6A). Bobur aka (Koreya, KRW): oxirgi uch oyda
// 2 600 000 / 2 750 000 (maosh + boshqa daromad) / 2 600 000 von, joriy oy maoshi 2 700 000, kurs
// 1 KRW = 9,1 so'm → chet eldagi xarajat «Sarmoya (o'qish)» belgisi bilan (oy hisobida alohida qator)
// → bir soati 12 045 von (10 soat × 22 kun), so'mda faqat kurs bilan → uyda daromad beradigan hunar
// rejasi «Hunardan ishga» g'oyasiga bog'lanadi → «Ilm zakoti»: hamyurtiga hujjatlar bo'yicha yordam →
// kurs tekshiruvi «chet elda ish kafolati» savoli bilan. Haqiqiy yadro bilan.
import 'package:baraka/core/core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

const nb = ' ';

Future<void> _space(WidgetTester tester, String label) async {
  tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.descendant(of: find.byType(Drawer), matching: find.widgetWithText(ChoiceChip, label)));
  await settle(tester, rounds: 10);
}

Future<void> _goTo(WidgetTester tester, String label) async {
  tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.descendant(of: find.byType(Drawer), matching: find.text(label)));
  await settle(tester, rounds: 10);
}

String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// Sozlamalar, oxirgi uch to'liq oy daromadi, bugungi kurs va Uy makonidagi «Hunardan ishga» g'oyasi.
Future<void> _setup(BarakaCore core, String mf, String uy) async {
  await core.mfSetSettings(
    spaceId: mf,
    input: const MfSettingsInput(country: 'Koreya', workCurrency: 'KRW', sharePercent: '20'),
  );
  final now = DateTime.now();
  Future<void> income(int back, String kind, String amount, int day) => core.mfRecordIncome(
    spaceId: mf,
    input: MfIncomeInput(
      kind: kind,
      amount: amount,
      channel: 'CARD',
      occurredOn: _ymd(DateTime(now.year, now.month - back, day)),
    ),
  );
  await income(3, 'SALARY', '2 600 000', 10);
  await income(2, 'SALARY', '2 600 000', 10);
  await income(2, 'OTHER_INCOME', '150 000', 20);
  await income(1, 'SALARY', '2 600 000', 10);
  // Joriy oy maoshi — o'rtachaga kirmaydi (to'liq oy emas), «Sarmoya» ulushi shundan.
  await income(0, 'SALARY', '2 700 000', 1);
  await core.mfSetRate(
    spaceId: mf,
    input: const MfRateInput(rate: '9,1', source: 'Bank'),
  );
  IdeaScenarioInput sc(String name, String income) =>
      IdeaScenarioInput(name: name, income: income, expense: '4 000 000');
  await core.createVentureIdea(
    spaceId: uy,
    input: VentureIdeaInput(
      title: 'Payvandlash ustaxonasi',
      capex: const [CapexLineInput(title: 'Payvandlash apparati', amount: '12 000 000')],
      scenarios: [sc('PESSIMISTIC', '5 000 000'), sc('BASE', '7 000 000'), sc('OPTIMISTIC', '9 000 000')],
    ),
  );
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Musofir: Sarmoya belgisi → bir soatim (von va soʻm) → ikki maqsad → Ilm zakoti → kurs', (
    tester,
  ) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    final setup = (await tester.runAsync(() => device.bootstrap(spaces: ['UY', 'MUSOFIR'], name: 'Bobur')))!;
    final mf = device.spaceId(setup, 'MUSOFIR');
    final uy = device.spaceId(setup, 'UY');
    await tester.runAsync(() => _setup(device.core, mf, uy));
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await _space(tester, 'Musofir');
    await waitFor(tester, find.byKey(const Key('mf-fund')));

    // Chet eldagi xarajat «Sarmoya (o'qish)» belgisi bilan — toifasida qoladi, oy hisobida alohida qator.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Xarajat').first);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Xarajat').first);
    await settle(tester, rounds: 4);
    await enter(tester, 'Summa (KRW)', '135 000');
    await tapText(tester, 'Sarmoya (oʻqish)');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('mf-self-investment')));
    expect(find.text('· shundan «Sarmoya (oʻqish)»'), findsOneWidget);

    // Bir soatim: oxirgi uch oy o'rtachasi 2 650 000 von → 12 045 von; so'mda — kurs bilan.
    await _goTo(tester, 'Oʻzimga sarmoya');
    await waitFor(tester, find.text('Bir soatim qancha? — chet elda'));
    expect(find.text('Bu haftaning 3 vazifasi'), findsOneWidget);
    await waitFor(tester, find.textContaining('2${nb}750${nb}000${nb}KRW'));
    await tapText(tester, 'Hisoblash va saqlash');
    await waitFor(tester, find.byKey(const Key('mfl-hour-value')));
    expect(find.text('12${nb}045${nb}KRW'), findsOneWidget);
    expect(find.textContaining('≈ 109${nb}609,50${nb}soʻm / soat'), findsOneWidget);
    expect(find.textContaining('oxirgi oylar oʻrtachasi (3 oy)'), findsOneWidget);
    expect(find.text('135${nb}000${nb}KRW — daromadning 5 %'), findsOneWidget);
    FocusManager.instance.primaryFocus?.unfocus();
    await scrollTop(tester);
    await tester.ensureVisible(find.text('Bir soatim qancha? — chet elda'));
    await shot(tester, 'android-49-mf-learning-hour');

    // Uyda daromad beradigan hunar — «Hunardan ishga» g'oyasiga bog'lanadi.
    await tapText(tester, 'Yangi reja');
    await waitFor(tester, find.text('Yangi bilim rejasi'));
    await tapChip(tester, 'Uyda');
    await enter(tester, 'Koʻnikma', 'Payvandlash');
    await choose(tester, '«Hunardan ishga» gʻoyasi (ixtiyoriy)', 'Payvandlash ustaxonasi');
    await tapText(tester, 'Ustoz');
    await enter(tester, 'Haftasiga soat', '4');
    await tapText(tester, 'Rejani ochish');
    await waitGone(tester, find.text('Yangi bilim rejasi'));
    await waitFor(tester, find.byKey(const Key('mfl-plan-idea')));
    expect(find.text('Gʻoya: Payvandlash ustaxonasi'), findsOneWidget);
    expect(find.textContaining('Uyda — Qaytgandan keyin uyda daromad beradigan hunar'), findsOneWidget);
    expect(find.text('Boshlangʻich nuqta: 12${nb}045${nb}KRW / soat'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('mfl-plan-idea')));
    await shot(tester, 'android-50-mf-learning-plan');

    // «Ilm zakoti»: yangi kelgan hamyurtga hujjatlar bo'yicha yordam.
    await tapText(tester, 'Oʻrgatganimni yozish');
    await waitFor(tester, find.text('Ilm zakoti: oʻrgatish yozuvi'));
    await tapChip(tester, 'Hujjatlar');
    await enter(tester, 'Nimani oʻrgatdi', 'Yashash kartasi hujjatlari');
    await enter(tester, 'Kimga (ixtiyoriy): ism yoki «yangi kelgan hamyurt»', 'Yangi kelgan hamyurt');
    await tapText(tester, 'Saqlash');
    await waitGone(tester, find.text('Ilm zakoti: oʻrgatish yozuvi'));
    await waitFor(tester, find.text('Shu oy: 1 marta oʻrgatildi'));
    expect(find.textContaining('Hujjatlar · Yashash kartasi hujjatlari · kimga: Yangi kelgan hamyurt'), findsOneWidget);

    // Kurs tekshiruvi: Musofir savoli — «kursdan keyin chet elda ish kafolati» (o'zi qizil).
    await tester.ensureVisible(find.byKey(const Key('mfl-course-check')));
    await tester.tap(find.byKey(const Key('mfl-course-check')));
    await settle(tester, rounds: 6);
    await waitFor(tester, find.text('Kursdan keyin chet elda ish kafolatlanyaptimi?'));
    final no = find.widgetWithText(ChoiceChip, 'Yoʻq');
    await waitFor(tester, no);
    expect(no.evaluate().length, 9);
    for (var i = 0; i < 9; i++) {
      // Dastur bor, o'qituvchini tekshirsa bo'ladi, sinov darsi bor; chet elda ish kafolati — «Ha».
      await tapChip(tester, i == 3 || i == 4 || i == 7 || i == 8 ? 'Ha' : 'Yoʻq', index: i);
    }
    await tapText(tester, 'Tekshirish');
    await waitFor(tester, find.textContaining('chet elda ish vaʼda qilinmoqda'));
    expect(find.text('Qizil: pul toʻlamang'), findsOneWidget);
    await tester.ensureVisible(find.text('Qizil: pul toʻlamang'));
    await shot(tester, 'android-51-mf-course-check');
  });
}
