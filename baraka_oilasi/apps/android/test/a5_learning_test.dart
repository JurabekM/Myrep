// A5: Uy makoni — «O'zimga sarmoya» (U16c, uy/SPEC 2G). Bekzod: daromad 12 000 000 →
// «Bir soatim qancha?» qo'lda 10 296 000, kuniga 11 soat, 26 kun → 36 000 so'm, soat chegarasi →
// ikki bilim rejasi, uchinchisi — 2 ta faol reja chegarasi → 1 soat 30 daqiqa o'qish → xarajat
// «O'zimga sarmoya» belgisi bilan rejaga (sarflandi 1 200 000, daromadning 10 %) → kurs
// tekshiruvi: daromad kafolati — qizil → «Ilm zakoti» → natija: yangi hisobsiz xabar, keyin
// 45 000 — farq 9 000 (25 %). Haqiqiy yadro bilan.
import 'package:baraka/core/core.dart';
import 'package:baraka/features/learning/learning_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

const nb = ' ';
const plan1 = 'Elektr montaj asoslari';

/// Bilim rejasi kartasi (sarlavhasi bo'yicha).
Finder _plan(String skill) => find.ancestor(of: find.text(skill), matching: find.byType(Card)).first;

Future<void> _anim(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

/// Karta ichidagi tugma yoki matnni bosish.
Future<void> _tapIn(WidgetTester tester, Finder scope, String text) async {
  await _anim(tester);
  final f = find.descendant(of: scope, matching: find.text(text));
  await tester.ensureVisible(f.first);
  await tester.tap(f.first);
  await settle(tester, rounds: 4);
}

Future<void> _enterIn(WidgetTester tester, Finder scope, String label, String value) async {
  await _anim(tester);
  final f = find.descendant(of: scope, matching: find.widgetWithText(TextField, label));
  await tester.ensureVisible(f.first);
  await tester.enterText(f.first, value);
  await tester.pump();
}

Future<void> _newPlan(WidgetTester tester, String skill, List<String> paths, {String? budget}) async {
  await tapText(tester, 'Yangi reja');
  await waitFor(tester, find.text('Yangi bilim rejasi'));
  await enter(tester, 'Koʻnikma', skill);
  for (final p in paths) {
    await tapText(tester, p);
  }
  if (budget != null) await enter(tester, 'Byudjet (ixtiyoriy)', budget);
  await enter(tester, 'Haftasiga soat', '3');
  await tapText(tester, 'Rejani ochish');
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Uy: soat qiymati → bilim rejalari → sarmoya xarajati → kurs tekshiruvi → Ilm zakoti → natija', (
    tester,
  ) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    final setup = (await tester.runAsync(device.bootstrap))!;
    final uy = device.spaceId(setup, 'UY');
    await tester.runAsync(
      () => device.core.recordIncome(
        spaceId: uy,
        input: const NewIncomeInput(amount: '12 000 000', source: 'Taksi', channel: 'CASH'),
      ),
    );
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));

    // «Bir soatim qancha?»: qo'lda daromad, kuniga 11 soat — chegara eslatmasi (ayblovsiz).
    await goTo(tester, 'Oʻzimga sarmoya');
    await waitFor(tester, find.text('Bir soatim qancha? — Bekzod'));
    expect(find.text('Bu haftaning 3 vazifasi'), findsOneWidget);
    await enter(tester, 'Oylik daromad (boʻsh — avtomatik)', '10 296 000');
    await enter(tester, 'Kuniga soat', '11');
    await enter(tester, 'Kuniga daqiqa', '0');
    await enter(tester, 'Oyda ish kunlari', '26');
    await tapText(tester, 'Hisoblash va saqlash');
    await waitFor(tester, find.text('36${nb}000${nb}soʻm'));
    expect(find.text('72${nb}000${nb}soʻm'), findsOneWidget);
    expect(find.textContaining('qoʻlda kiritilgan'), findsOneWidget);
    expect(find.byKey(const Key('hour-ceiling')), findsOneWidget);
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.ensureVisible(find.text('Bir soatim qancha? — Bekzod'));
    await shot(tester, 'android-43-learning-hour');

    // Bilim rejalari: ikkitasi ochiladi, uchinchisi — chegara.
    await _newPlan(tester, plan1, ['Kurs', 'Amaliyot'], budget: '1 500 000');
    await waitGone(tester, find.text('Yangi bilim rejasi'));
    await waitFor(tester, find.textContaining('Byudjet: 1${nb}500${nb}000${nb}soʻm · sarflandi: 0${nb}soʻm'));
    expect(find.text('Boshlangʻich nuqta: 36${nb}000${nb}soʻm / soat'), findsOneWidget);
    await _newPlan(tester, 'Buxgalteriya', ['Kitob']);
    await waitGone(tester, find.text('Yangi bilim rejasi'));
    await _newPlan(tester, 'Ingliz tili', ['Ustoz']);
    await waitFor(tester, find.textContaining('koʻpi bilan 2 ta faol reja'));
    await tapText(tester, 'Bekor qilish');
    await waitGone(tester, find.text('Yangi bilim rejasi'));

    // O'qish vaqti: 1 soat 30 daqiqa.
    await _enterIn(tester, _plan(plan1), 'Oʻqish, soat', '1');
    await _enterIn(tester, _plan(plan1), 'Oʻqish, daqiqa', '30');
    await _tapIn(tester, _plan(plan1), 'Vaqtni yozish');
    await waitFor(tester, find.text('Jami oʻqildi: 1 soat 30 daqiqa'));

    // Xarajat «O'zimga sarmoya» belgisi bilan rejaga — kartada sarflangan va oylik ulush.
    await goTo(tester, 'Xarajatlar');
    await enter(tester, 'Summa', '1 200 000');
    await choose(tester, 'Kategoriya', 'Boshqa');
    await tapText(tester, 'Oʻzimga sarmoya (bilim, malaka)');
    await choose(tester, 'Bilim rejasi (ixtiyoriy)', plan1);
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.text('1${nb}200${nb}000${nb}soʻm'));
    await goTo(tester, 'Oylik audit');
    await waitFor(tester, find.text('1${nb}200${nb}000${nb}soʻm — daromadning 10 %'));
    await goTo(tester, 'Oʻzimga sarmoya');
    await waitFor(tester, find.textContaining('sarflandi: 1${nb}200${nb}000${nb}soʻm'));
    expect(find.text('1${nb}200${nb}000${nb}soʻm — daromadning 10 %'), findsOneWidget);

    // Kurs tekshiruvi (rejadan): daromad kafolati — qizil.
    await _tapIn(tester, _plan(plan1), 'Kursni tekshirish');
    await waitFor(tester, find.text('Kursdan keyin daromad yoki ish kafolatlanyaptimi?'));
    for (final (i, reply) in ['Yoʻq', 'Yoʻq', 'Ha', 'Ha', 'Bilmayman', 'Yoʻq', 'Yoʻq', 'Ha'].indexed) {
      await tapChip(tester, reply, index: i);
    }
    await tapText(tester, 'Tekshirish');
    await waitFor(tester, find.text('Qizil: pul toʻlamang'));
    expect(find.textContaining('Hech kim kelajakdagi daromadingizni kafolatlay olmaydi'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('offer-result')));
    await shot(tester, 'android-44-course-check');
    await tapText(tester, 'Yopish');
    await waitGone(tester, find.text('Qizil: pul toʻlamang'));

    // «Ilm zakoti».
    await tapText(tester, 'Oʻrgatganimni yozish');
    await waitFor(tester, find.text('Ilm zakoti: oʻrgatish yozuvi'));
    await enter(tester, 'Nimani oʻrgatdi', 'Rozetka ulash');
    await enter(tester, 'Kimga (ixtiyoriy): ism yoki «qoʻshni», «xodim»', 'hamkasb');
    await enter(tester, 'Qancha vaqt, daqiqa (ixtiyoriy)', '45');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.text('Shu oy: 1 marta oʻrgatildi'));
    expect(find.textContaining('kimga: hamkasb'), findsOneWidget);

    // Natija: yangi hisobsiz — xabar; qayta hisobdan keyin farq va foiz.
    await _tapIn(tester, _plan(plan1), 'Natijani oʻlchash');
    await waitFor(tester, find.textContaining('hisobini yangidan saqlang'));
    await enter(tester, 'Oylik daromad (boʻsh — avtomatik)', '12 870 000');
    await tapText(tester, 'Hisoblash va saqlash');
    await waitFor(tester, find.text('45${nb}000${nb}soʻm'));
    await _tapIn(tester, _plan(plan1), 'Natijani oʻlchash');
    await waitFor(tester, find.text('Farq: 9${nb}000${nb}soʻm (25 %)'));
    expect(find.text('36${nb}000${nb}soʻm → 45${nb}000${nb}soʻm / soat'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('plan-result')));
    await shot(tester, 'android-45-learning-plans');
  });

  test('vaqt maydonlari: desktop bilan bir xil qoida (soat ≤ 3 raqam, daqiqa 0–59, kunlar 1–2 raqam)', () {
    expect(toMinutes('9', '30'), 570);
    expect(toMinutes('', '45'), 45);
    expect(toMinutes('1', ''), 60);
    expect(toMinutes('1', '60'), 0);
    expect(toMinutes('1,5', ''), 0);
    expect(toMinutes('1000', '0'), 0);
    expect(parseCount('26', 2), 26);
    expect(parseCount('260', 2), 0);
    expect(parseCount('-1', 2), 0);
    expect(parseCount('1440', 4), 1440);
  });

  testWidgets('boshlangʻich nuqtasiz reja: natija faqat hozirgi qiymat va betaraf izoh', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    await tester.runAsync(device.bootstrap);
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await goTo(tester, 'Oʻzimga sarmoya');
    await waitFor(tester, find.text('Bir soatim qancha? — Bekzod'));
    await _newPlan(tester, 'Buxgalteriya', ['Kitob']);
    await waitGone(tester, find.text('Yangi bilim rejasi'));
    await waitFor(tester, find.textContaining('Boshlangʻich nuqta yoʻq'));
    await enter(tester, 'Oylik daromad (boʻsh — avtomatik)', '10 296 000');
    await enter(tester, 'Kuniga soat', '11');
    await enter(tester, 'Oyda ish kunlari', '26');
    await tapText(tester, 'Hisoblash va saqlash');
    await waitFor(tester, find.text('36${nb}000${nb}soʻm'));
    await _tapIn(tester, _plan('Buxgalteriya'), 'Natijani oʻlchash');
    await waitFor(tester, find.textContaining('boshlangʻich nuqta yozilmagan edi'));
    expect(find.text('Hozirgi qiymat: 36${nb}000${nb}soʻm / soat'), findsOneWidget);
    expect(find.textContaining('ayb emas'), findsNothing);
    expect(find.textContaining('qiymati oshdi'), findsNothing);
  });

  testWidgets('oʻqish qarzga: «Toʻxta va oʻyla» savollari bilan saqlanadi, yadro javobsiz qabul qilmaydi (2G.2)', (
    tester,
  ) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    final setup = (await tester.runAsync(device.bootstrap))!;
    final uy = device.spaceId(setup, 'UY');
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await goTo(tester, 'Xarajatlar');
    await enter(tester, 'Summa', '900 000');
    await choose(tester, 'Kategoriya', 'Boshqa');
    expect(find.byKey(const Key('expense-study-debt')), findsNothing);
    await tapText(tester, 'Oʻzimga sarmoya (bilim, malaka)');
    await waitFor(tester, find.byKey(const Key('expense-study-debt')));
    expect(find.text('Toʻxta va oʻyla'), findsNothing);
    await tapText(tester, 'Bu pul qarzga olingan');
    await waitFor(tester, find.text('Toʻxta va oʻyla'));
    expect(find.textContaining('joriy byudjetdan yoki oʻsadigan pul ulushidan'), findsOneWidget);
    // Javoblar oldindan tanlanmagan — javobsiz tekshirib bo'lmaydi.
    FilledButton button(String text) => tester.widget<FilledButton>(find.widgetWithText(FilledButton, text));
    expect(button('Tekshirish').onPressed, isNull);
    await tapText(tester, 'Zarurat');
    expect(button('Tekshirish').onPressed, isNull);
    await tapText(tester, 'Ha, foizli');
    await tapText(tester, 'Qarindoshdan foizsiz');
    await tapText(tester, 'Tekshirish');
    await waitFor(tester, find.byKey(const Key('study-debt-warnings')));
    expect(find.textContaining('Bu qarz foizli (ribo)'), findsOneWidget);
    expect(find.textContaining('Foizsiz muqobil bor ekan'), findsOneWidget);
    await tapText(tester, 'Oʻyladim, saqlash');
    await waitGone(tester, find.text('Toʻxta va oʻyla'));
    final summary = (await tester.runAsync(() => device.core.monthlySummary(spaceId: uy)))!;
    expect(summary.selfInvestment.total.minor, '90000000');
    // Yadro: qarzga o'qish — javobsiz saqlanmaydi.
    final categories = (await tester.runAsync(() => device.core.categories(spaceId: uy)))!;
    Object? error;
    await tester.runAsync(() async {
      try {
        await device.core.recordExpense(
          spaceId: uy,
          input: NewExpenseInput(
            amount: '100 000',
            categoryId: categories.first.id,
            channel: 'CASH',
            isGift: false,
            isOstentation: false,
            fundedByDebt: true,
            selfInvestment: true,
          ),
        );
      } on AppError catch (e) {
        error = e;
      }
    });
    expect(error, isA<AppError>().having((e) => e.code, 'code', 'BORROW_CHECK_REQUIRED'));
  });
}
