// A4: Musofir makoni — sozlash, maosh va jamg'armaga ulush, uyga yuborish, kurs, «Ikki qirg'oq»
// shartlari, qaytish va sovutish davri, katta qaror tekshiruvi; Uy makonida «Ikki qirg'oq» —
// yuborilgan pulni qabul qilish va maqsad bo'yicha xarajat. Haqiqiy yadro bilan.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

/// Yon menyudan makonni almashtirish.
Future<void> _space(WidgetTester tester, String label) async {
  tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.descendant(of: find.byType(Drawer), matching: find.widgetWithText(ChoiceChip, label)));
  await settle(tester, rounds: 10);
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Musofir: maosh → jamgʻarma → uyga → kurs → shartlar → qaytish → qaror → Ikki qirgʻoq', (
    tester,
  ) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    await tester.runAsync(() => device.bootstrap(spaces: ['UY', 'MUSOFIR']));
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await _space(tester, 'Musofir');

    // Sozlash: ish valyutasi KRW (standart), ulush va maqsad.
    await waitFor(tester, find.text('Musofir makonini sozlash'));
    await enter(tester, 'Qaytish jamgʻarmasi maqsadi (soʻmda)', '60 000 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('mf-fund')));

    // Maosh (tez tugma) → ulush taklifi → jamg'armaga.
    await tapText(tester, 'Maosh');
    await enter(tester, 'Summa (KRW)', '2 500 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('mf-offer')));
    await tapText(tester, 'Jamgʻarmaga qoʻyish');
    await waitFor(tester, find.text('Jamgʻarmaga'));
    await tapText(tester, 'Saqlash');
    await waitGone(tester, find.byKey(const Key('mf-offer')));

    // Kurs: 1 KRW = 9 so'm.
    await enter(tester, '1 KRW necha UZS', '9');
    await tapText(tester, 'Kursni saqlash');
    await waitFor(tester, find.byKey(const Key('mf-fund-home')));
    await scrollTop(tester);
    await shot(tester, 'android-40-mf-home');

    // Uyga yuborish.
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Uyga yuborish').first);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Uyga yuborish').first);
    await settle(tester, rounds: 4);
    await enter(tester, 'Summa (KRW)', '1 000 000');
    await enter(tester, 'Komissiya (KRW)', '10 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.textContaining('1 000 000'));

    // «Ikki qirg'oq» shartlari (kelishuv matni yadrodan).
    await tapText(tester, 'Shartlarni belgilash');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('mf-terms-agreement')));

    // Katta qaror: hamma savolga «Bilmayman» → xulosa → «Kutaman».
    await tapText(tester, 'Katta qarorni tekshirish');
    await waitFor(tester, find.text('Nima haqida'));
    final amount = find.byWidgetPredicate(
      (w) => w is TextField && (w.decoration?.labelText?.startsWith('Summa') ?? false),
    );
    await tester.enterText(amount.first, '50 000 000');
    await enter(tester, 'Nima haqida', 'Doʻstimning doʻkoniga sherik boʻlish');
    final unknown = find.widgetWithText(ChoiceChip, 'Bilmayman');
    await waitFor(tester, unknown);
    for (var i = 0; i < unknown.evaluate().length; i++) {
      await tapChip(tester, 'Bilmayman', index: i);
    }
    await tapText(tester, 'Tekshirish');
    await waitFor(tester, find.byKey(const Key('mf-decision-result')));
    await shot(tester, 'android-41-mf-decision');
    await tapText(tester, 'Kutaman');
    await waitFor(tester, find.byKey(const Key('mf-decision')));

    // Qaytdim → sovutish davri.
    await tapText(tester, 'Qaytdim');
    await pickDate(tester, 'Qaytgan sana', -1);
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('mf-cooling')));

    // Uy makoni: «Ikki qirg'oq» — pulni qabul qilish va maqsad bo'yicha xarajat.
    await _space(tester, 'Uy');
    await goTo(tester, 'Ikki qirgʻoq');
    await waitFor(tester, find.byKey(const Key('mf-remittance')));
    await enter(tester, 'Olingan summa (soʻmda)', '9 000 000');
    await tapText(tester, 'Qabul qildim');
    await waitFor(tester, find.textContaining('Qabul qilindi:'));
    await enter(tester, 'Summa', '500 000');
    await tapText(tester, 'Xarajatni yozish');
    await waitFor(tester, findRows('mf-spend'));
    await scrollTop(tester);
    await shot(tester, 'android-42-two-shores');
  });
}
