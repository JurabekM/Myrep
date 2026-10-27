// A6: Kasb-kor — «O'zimga sarmoya» (K9, kasbkor/SPEC 8A). Feruzaning o'tgan oyi (3.1 misoli):
// tushum 18 000 000, chiqim 8 500 000, o'z mehnati 5 000 000, qizining 80 soati × 15 000, mashinalar
// 12 000 000 / 60 oy → «Hisob kuni» yopiladi → egasi topgani 8 100 000 (maosh qo'shilmaydi) →
// 10 soat × 26 kun → 31 153,85 so'm → «O'zim qilaymi yoki o'rgatib topshiraymi?» (yordamchi 15 000,
// 20 soat, o'rgatish 500 000 + 10 soat) → 3 oyda qoplanadi, qaror xodim kartochkasiga → «Ilm
// zakoti» xodimga → chiqim «Sarmoya (o'qish)» belgisi bilan. Haqiqiy yadro bilan.
import 'package:baraka/core/core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

const nb = '\u00a0';

Future<void> _space(WidgetTester tester, String label) async {
  tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.descendant(of: find.byType(Drawer), matching: find.widgetWithText(ChoiceChip, label)));
  await settle(tester, rounds: 10);
}

/// Menyuning oxirgi bo'limlari ekran pastida qoladi — markazga aylantirib bosamiz.
Future<void> _goTo(WidgetTester tester, String label) async {
  tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  final item = find.descendant(of: find.byType(Drawer), matching: find.text(label));
  await tester.scrollUntilVisible(
    item,
    120,
    scrollable: find.descendant(of: find.byType(Drawer), matching: find.byType(Scrollable)).last,
  );
  await tester.runAsync(() => Scrollable.ensureVisible(tester.element(item), alignment: 0.5));
  await tester.pump();
  await tester.tap(item);
  await settle(tester, rounds: 10);
}

String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// O'tgan oyda yopilgan «Hisob kuni» (yadro orqali, oy boshi — 1-kun).
Future<void> _closedMonth(BarakaCore core, String kk) async {
  final now = DateTime.now();
  final start = DateTime(now.year, now.month - 1);
  String day(int d) => _ymd(DateTime(start.year, start.month, d));
  await core.kkSetOwnerLabor(spaceId: kk, amount: '5 000 000');
  await core.kkRecordSale(
    spaceId: kk,
    input: KkSaleInput(amount: '18 000 000', channel: 'CARD', occurredOn: day(10)),
  );
  final materials = (await core.categories(spaceId: kk)).firstWhere((c) => c.nameKey == 'category.kk.materials');
  await core.recordExpense(
    spaceId: kk,
    input: NewExpenseInput(
      amount: '8 500 000',
      categoryId: materials.id,
      channel: 'CARD',
      occurredOn: day(12),
      isGift: false,
      isOstentation: false,
      fundedByDebt: false,
      selfInvestment: false,
    ),
  );
  await core.kkAddFamilyLabor(
    spaceId: kk,
    input: KkFamilyLaborInput(person: 'Qizi', hours: '80', hourlyRate: '15 000', paid: false, workedOn: day(15)),
  );
  await core.kkAddEquipment(
    spaceId: kk,
    input: KkEquipmentInput(name: '2 ta tikuv mashinasi', cost: '12 000 000', usefulMonths: 60, acquiredOn: day(1)),
  );
  await core.kkCloseMonth(
    spaceId: kk,
    input: KkCloseInput(periodStart: day(1), carryOverdraw: false),
  );
  await core.kkAddEmployee(
    spaceId: kk,
    input: const KkEmployeeInput(
      name: 'Sardor',
      role: 'Tikuvchi',
      phoneConsent: false,
      duties: 'Buyurtmalarni tikish',
      salary: '2 500 000',
      payDay: 5,
      noticeDays: 14,
    ),
  );
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Kasb-kor: egasining soati → o‘zim qilaymi → Ilm zakoti → Sarmoya (o‘qish)', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    final setup = (await tester.runAsync(() => device.bootstrap(spaces: ['UY', 'KASBKOR'], name: 'Feruza')))!;
    final kk = device.spaceId(setup, 'KASBKOR');
    await tester.runAsync(() => _closedMonth(device.core, kk));
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await _space(tester, 'Kasb-kor');
    await waitFor(tester, find.byKey(const Key('kk-true-profit')));

    // Chiqim «Sarmoya (o'qish)» belgisi bilan — haqiqiy foydaga kiradi, alohida qator.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Chiqim').first);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Chiqim').first);
    await settle(tester, rounds: 4);
    await enter(tester, 'Summa', '300 000');
    await tapText(tester, 'Sarmoya (oʻqish)');
    await tapText(tester, 'Saqlash');
    await waitGone(tester, find.text('Sarmoya (oʻqish)'));

    // Egasining bir soati: yopilgan oydan 8 100 000 (maosh qo'shilmaydi) → 31 153,85 so'm.
    await _goTo(tester, 'Oʻzimga sarmoya');
    await waitFor(tester, find.text('Egasining bir soati'));
    expect(find.text('Bu haftaning 3 vazifasi'), findsOneWidget);
    expect(find.text('300${nb}000${nb}soʻm'), findsOneWidget);
    await waitFor(tester, find.textContaining('topgani 8${nb}100${nb}000${nb}soʻm'));
    expect(
      find.textContaining('oʻz mehnati 5${nb}000${nb}000${nb}soʻm + haqiqiy foyda 3${nb}100${nb}000${nb}soʻm'),
      findsOneWidget,
    );
    await enter(tester, 'Kuniga soat', '10');
    await enter(tester, 'Kuniga daqiqa', '0');
    await enter(tester, 'Oyda ish kunlari', '26');
    await tapText(tester, 'Hisoblash va saqlash');
    await waitFor(tester, find.byKey(const Key('kkl-hour-value')));
    expect(find.text('31${nb}153,85${nb}soʻm'), findsOneWidget);
    expect(find.textContaining('yopilgan oylar oʻrtachasi (1 oy)'), findsOneWidget);
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.ensureVisible(find.text('Egasining bir soati'));
    await shot(tester, 'android-46-kk-learning-hour');

    // «O'zim qilaymi yoki o'rgatib topshiraymi?»: hisob yadroda, 3 oyda qoplanadi.
    await enter(tester, 'Ish turi', 'Mato qabul qilish');
    await choose(tester, 'Xodim kartochkasi (ixtiyoriy)', 'Sardor');
    await enter(tester, 'Yordamchi yoki xodimning 1 soati narxi', '15 000');
    await enter(tester, 'Bu ishga oyiga, soat', '20');
    await enter(tester, 'Oʻrgatishga ketadigan vaqtingiz, soat', '10');
    await enter(tester, 'Bir martalik oʻrgatish xarajati (ixtiyoriy)', '500 000');
    await tapText(tester, 'Hisoblash');
    await waitFor(tester, find.byKey(const Key('kkl-delegate-result')));
    expect(find.text('3 oy'), findsOneWidget);
    expect(find.text('323${nb}077${nb}soʻm'), findsOneWidget);
    expect(find.text('811${nb}538,50${nb}soʻm'), findsOneWidget);
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.ensureVisible(find.byKey(const Key('kkl-delegate-result')));
    await shot(tester, 'android-47-kk-delegate');

    // Yordamchi qimmatroq — «hozircha o'zingiz qilganingiz arzon».
    await enter(tester, 'Yordamchi yoki xodimning 1 soati narxi', '40 000');
    await tapText(tester, 'Hisoblash');
    await waitFor(tester, find.textContaining('Hozircha oʻzingiz qilganingiz arzon'));
    expect(find.byKey(const Key('kkl-payback')), findsNothing);
    await enter(tester, 'Yordamchi yoki xodimning 1 soati narxi', '15 000');
    await tapText(tester, 'Qarorni saqlash');
    await waitFor(tester, find.text('Mato qabul qilish · Sardor'));

    // «Ilm zakoti»: xodim kartochkasidan.
    await tapText(tester, 'Oʻrgatganimni yozish');
    await waitFor(tester, find.text('Ilm zakoti: oʻrgatish yozuvi'));
    await enter(tester, 'Nimani oʻrgatdi', 'Buyurtma qabul qilish');
    await tapText(tester, 'Saqlash');
    await waitGone(tester, find.text('Ilm zakoti: oʻrgatish yozuvi'));
    await waitFor(tester, find.text('Shu oy: 1 marta oʻrgatildi'));
    expect(find.textContaining('kimga: Sardor'), findsOneWidget);

    await scrollTop(tester);
    await shot(tester, 'android-48-kk-learning-teach');

    // Saqlangan qarorni o'chirish — avval tasdiq so'raladi.
    await tapText(tester, 'Oʻchirish');
    await waitFor(tester, find.text('«Mato qabul qilish» qarorini oʻchirasizmi?'));
    await tapText(tester, 'Ha, oʻchirish');
    await waitFor(tester, find.text('Hali saqlangan qaror yoʻq.'));
  });
}
