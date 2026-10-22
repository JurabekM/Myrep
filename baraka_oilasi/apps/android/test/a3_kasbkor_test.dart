// A3: Kasb-kor makoni — tushum va chiqim, tovar xaridi, xodim (imzo va avans), nasiya va to'lov,
// kassa kuni, buyurtma narxi, uskuna, oilaviy mehnat; Hisob kuni, darvoza, zakot, tarozi va
// ta'minotchilar ekranlari ochiladi. Haqiqiy yadro bilan.
import 'package:baraka/core/core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

const nb = ' ';

/// Yon menyudan makonni almashtirish.
Future<void> _space(WidgetTester tester, String label) async {
  tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.descendant(of: find.byType(Drawer), matching: find.widgetWithText(ChoiceChip, label)));
  await settle(tester, rounds: 10);
}

/// Kalit ostidagi matn (KPI qiymati).
String _textAt(WidgetTester tester, String key) {
  final f = find.descendant(of: find.byKey(Key(key)), matching: find.byType(Text));
  final w = f.evaluate().isEmpty ? tester.widget<Text>(find.byKey(Key(key))) : tester.widget<Text>(f.first);
  return w.data ?? w.textSpan?.toPlainText() ?? '';
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Kasb-kor: tushum, tovar, xodim, nasiya, kassa, narx, uskuna, mehnat', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    await tester.runAsync(() => device.bootstrap(spaces: ['UY', 'KASBKOR']));
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await _space(tester, 'Kasb-kor');
    await waitFor(tester, find.byKey(const Key('kk-true-profit')));

    // Tushum (tez tugma) va chiqim.
    await tapText(tester, 'Tushum');
    await enter(tester, 'Summa', '1 500 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.textContaining('1${nb}500${nb}000'));
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Chiqim').first);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Chiqim').first);
    await settle(tester, rounds: 4);
    await enter(tester, 'Summa', '300 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.textContaining('1${nb}200${nb}000'));
    expect(_textAt(tester, 'kk-wallet-CASH'), contains('1${nb}200${nb}000'));
    await scrollTop(tester);
    await shot(tester, 'android-30-kk-home');

    // Tovar: yangi tovar → xarid.
    await goTo(tester, 'Tovarlar');
    await tapText(tester, 'Yangi tovar');
    await enter(tester, 'Nomi', 'Un');
    await tapText(tester, 'Tovarni qoʻshish');
    await waitFor(tester, find.byKey(const Key('kk-item-Un')));
    await tapText(tester, 'Xarid');
    await enter(tester, 'Jami narx', '400 000');
    final qty = find.byWidgetPredicate(
      (w) => w is TextField && (w.decoration?.labelText?.startsWith('Miqdor') ?? false),
    );
    await tester.enterText(qty.first, '50');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.textContaining('400${nb}000'));
    await scrollTop(tester);
    await shot(tester, 'android-31-kk-stock');

    // Xodim: qo'shish → imzolash → avans.
    await goTo(tester, 'Xodimlar');
    await tapText(tester, 'Yangi xodim');
    await enter(tester, 'Ism', 'Sardor');
    await enter(tester, 'Lavozim', 'Tikuvchi');
    await enter(tester, 'Vazifalar', 'Buyurtmalarni tikish');
    await enter(tester, 'Oylik haq', '3 000 000');
    await tapText(tester, 'Xodimni qoʻshish');
    // Xodim kartasi chizilguncha (ism forma maydonida ham bor).
    await waitFor(tester, find.text('Imzolash'));
    expect(find.textContaining('Sardor', findRichText: true), findsWidgets);
    await tapText(tester, 'Imzolash');
    await tapText(tester, 'Imzolandi deb yozish');
    await waitFor(tester, find.text('Avans'));
    await tapText(tester, 'Kelishuv PDF');
    await waitShared(tester, device, (n) => n == 'kelishuv.pdf');
    await tapText(tester, 'Avans');
    await enter(tester, 'Summa', '500 000');
    await tapText(tester, 'Avansni yozish');
    await waitFor(tester, find.textContaining('500${nb}000'));

    // Nasiya: yangi mijoz va nasiya → to'lov.
    await goTo(tester, 'Nasiya daftari');
    await tapText(tester, 'Yangi nasiya');
    // Mijoz hali yo'q — yangi mijoz formasi darhol ochiladi.
    await enter(tester, 'Ism', 'Karim aka');
    await tapText(tester, 'Mijozni saqlash');
    await waitFor(tester, find.text('Karim aka'));
    await enter(tester, 'Tovar yoki xizmat', 'Muzlatkich');
    await enter(tester, 'Nasiya narxi (qotiriladi)', '6 000 000');
    await enter(tester, 'Toʻlovlar soni (oylik)', '6');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('kk-credit-sale-Karim aka')));
    await tapText(tester, 'Toʻlov');
    await enter(tester, 'Summa', '1 000 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.textContaining('5${nb}000${nb}000'));
    await scrollTop(tester);
    await shot(tester, 'android-32-kk-credit');

    // Kassa kuni: sanaldi → farq → yopish.
    await goTo(tester, 'Kassa');
    await waitFor(tester, find.byKey(const Key('kk-cash-expected')));
    // Naqd: 1,5 mln tushum + 1 mln nasiya to'lovi − 300 ming chiqim − 500 ming avans (xarid — karta).
    expect(find.textContaining('1${nb}700${nb}000'), findsWidgets);
    await enter(tester, 'Sanalgan summa', '1 700 000');
    await tapText(tester, 'Tekshirish');
    await waitFor(tester, find.byKey(const Key('kk-cash-difference')));
    await tapText(tester, 'Kunni yopish');
    await waitFor(tester, find.text('Bugungi kassa yopilgan. Ertaga shu yerda.'));

    // Buyurtma narxi.
    await goTo(tester, 'Buyurtma narxi');
    await enter(tester, 'Material', '200 000');
    await enter(tester, 'Mehnat (soat)', '10');
    await enter(tester, 'Soat bahosi', '30 000');
    await enter(tester, 'Mijozga aytiladigan narx', '600 000');
    await tapText(tester, 'Hisoblash');
    await waitFor(tester, find.byKey(const Key('kk-quote-verdict')));
    await shot(tester, 'android-33-kk-quote');

    // Uskuna va oilaviy mehnat.
    await goTo(tester, 'Uskunalar');
    await enter(tester, 'Nomi', 'Tikuv mashinasi');
    await enter(tester, 'Narxi', '6 000 000');
    await tapText(tester, 'Qoʻshish');
    await waitFor(tester, find.byKey(const Key('kk-eq-dep-Tikuv mashinasi')));
    await goTo(tester, 'Oilaviy mehnat');
    await enter(tester, 'Kim', 'Gulnora');
    await enter(tester, 'Soat', '20');
    await enter(tester, 'Soat bahosi', '20 000');
    await tapText(tester, 'Yozish');
    await waitFor(tester, find.textContaining('400${nb}000'));

    // Qolgan ekranlar ochiladi (yadro ma'lumoti bilan).
    await goTo(tester, 'Taʼminotchilar');
    await waitFor(tester, find.text('Yangi taʼminotchi'));
    await goTo(tester, 'Hisob kuni');
    await waitFor(tester, find.byKey(const Key('kk-close-remaining')));
    await scrollTop(tester);
    await shot(tester, 'android-34-kk-close');
    await goTo(tester, 'Kengayish darvozasi');
    await waitFor(tester, find.byKey(const Key('kk-gate-status')));
    await goTo(tester, 'Zakot hisobi');
    await waitFor(tester, find.byKey(const Key('kk-zakat-base')));
    await goTo(tester, 'Tarozi va sanoq');
    await waitFor(tester, find.text('Tekshirildi'));
  });

  testWidgets('Sotuvchi qurilmasi: ulash → sotuv → smenani yopish', (tester) async {
    phone(tester);
    // Egasining qurilmasi (faqat yadro orqali): Kasb-kor makoni va sotuvchi uchun ulash fayli.
    final owner = (await tester.runAsync(Device.create))!;
    final r = (await tester.runAsync(() => owner.bootstrap(spaces: ['UY', 'KASBKOR'])))!;
    final offer = (await tester.runAsync(
      () => owner.core.pairingOffer(
        input: PairingInput(role: 'SELLER', spaceId: owner.spaceId(r, 'KASBKOR')),
      ),
    ))!;
    // Sotuvchi telefoni: faylni ochadi va kodni kiritadi.
    final seller = (await tester.runAsync(Device.create))!;
    await tester.runAsync(
      () => seller.container
          .read(sessionActionsProvider)
          .join('246802', offer.bytes, JoinInput(secret: offer.code, deviceName: 'Sotuvchi', platform: 'android')),
    );
    seller.container.read(sessionActionsProvider).finishSetup();
    await tester.pumpWidget(seller.app());
    await waitFor(tester, find.text('Sotuvni yozish'));

    await enter(tester, 'Summa', '250 000');
    await tapText(tester, 'Sotuvni yozish');
    await waitFor(tester, findRows('kk-seller-row'));
    await scrollTop(tester);
    await shot(tester, 'android-35-kk-seller');

    await goTo(tester, 'Smena');
    await waitFor(tester, find.text('Sanalgan summa'));
    if (find.text('Kassadagi boshlangʻich naqd').evaluate().isNotEmpty) {
      await enter(tester, 'Kassadagi boshlangʻich naqd', '50 000');
    }
    await enter(tester, 'Sanalgan summa', '300 000');
    await enter(tester, 'Egasiga topshirildi', '250 000');
    await settle(tester, rounds: 10);
    await tapText(tester, 'Smenani yopish');
    await waitFor(tester, find.text('Bugungi smena yopilgan. Ertaga shu yerda.'));
  });
}
