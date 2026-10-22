// A2: Uy makoni — «Hunardan ishga» g'oyasi → mudoraba qoralamasi → 9 savol → imzolar (barmoq
// bilan) → «bu qarz emas», oila roziligi → faol; kassa daftari (chek ilovasi), davr taqsimoti va
// hisobot PDF; vazifa hodisasi, ochiq hisob ko'rigi va bayonnoma PDF; nizo va hakam qarori;
// kelishuvlar markazi va oilaviy kelishuv (PIN bilan); taklif tekshiruvi; zaxira eksport va
// o'z faylini qayta import qilish rad etilishi. Haqiqiy yadro bilan.
import 'dart:convert';
import 'dart:typed_data';

import 'package:baraka/bindings/third_party/baraka_app.dart';
import 'package:baraka/features/setup/setup_screen.dart';
import 'package:baraka/features/venture/ledger_view.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

const nb = '\u00a0';

/// 1×1 PNG (chek rasmi o'rniga).
final Uint8List _png = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
);

/// Sehrgar qadami (`○ 3. …` yoki `● 3. …`).
Future<void> _step(WidgetTester tester, int n) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  final f = find.byWidgetPredicate(
    (w) => w is ChoiceChip && w.label is Text && RegExp('^(. )?$n\\. ').hasMatch((w.label as Text).data ?? ''),
  );
  await waitFor(tester, f);
  await tester.ensureVisible(f);
  await tester.tap(f);
  await settle(tester, rounds: 4);
}

/// Imzo maydoniga chiziq tortish va tasdiqlash.
Future<void> _sign(WidgetTester tester, String name) async {
  await tapText(tester, '$name imzolaydi');
  await waitFor(tester, find.text('$name: imzo'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.drag(find.byKey(const Key('signature-pad')), const Offset(120, 30));
  await tester.pump();
  await tapText(tester, 'Imzolash');
  await waitGone(tester, find.text('$name: imzo'));
  await waitGone(tester, find.text('$name imzolaydi'));
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Uy: gʻoya → sheriklik → kassa → koʻrik → nizo → kelishuvlar → sinxron', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    ({String name, Uint8List bytes})? picked;
    device.overrides.addAll([
      pickAttachmentsProvider.overrideWithValue(() async => [AttachmentInput(fileName: 'chek.png', bytes: _png)]),
      pickFileProvider.overrideWithValue(() async => picked),
    ]);
    await tester.runAsync(device.bootstrap);
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));

    // «Hunardan ishga»: g'oya hisobi (mudoraba) → shartnoma qoralamasi.
    await goTo(tester, 'Hunardan ishga');
    await tapText(tester, 'Yangi gʻoya');
    await enter(tester, 'Gʻoya nomi', 'Tikuv ustaxonasi');
    await enter(tester, '1-narsa', 'Tikuv mashinasi');
    await enter(tester, '1-narsa narxi', '6 000 000');
    // Uch stsenariy: yomon, o'rtacha, yaxshi oy.
    for (final (i, (income, expense)) in [
      ('3 000 000', '2 000 000'),
      ('5 000 000', '2 000 000'),
      ('7 000 000', '2 500 000'),
    ].indexed) {
      for (final (label, v) in [('Oylik kirim', income), ('Oylik xarajat', expense)]) {
        final f = find.widgetWithText(TextField, label).at(i);
        await tester.ensureVisible(f);
        await tester.enterText(f, v);
      }
    }
    await enter(tester, 'Bizning foyda ulushimiz, %', '50');
    await tapText(tester, 'Hisoblash va saqlash');
    await waitFor(tester, find.text('Sheriklik shartnomasiga oʻtish'));
    await scrollTop(tester);
    await shot(tester, 'android-20-idea');
    await tapText(tester, 'Sheriklik shartnomasiga oʻtish');
    await enter(tester, 'Kapital beruvchining toʻliq ismi', 'Dilshod Rahimov');
    await enter(tester, 'Bizning toʻliq ismimiz', 'Anvar Karimov');
    await tapText(tester, 'Qoralama yaratish');
    await waitFor(tester, find.text('Tikuv ustaxonasi'));
    // Shartnoma oynasi ochilsin: «4 / 9» matni sheriklik ro'yxatida ham bor (CI'da poyga bo'lgan).
    await waitFor(tester, find.textContaining('1. Kim bilan kim? '));
    expect(find.text('4 / 9 savolga javob berildi'), findsWidgets);

    // 3. Vazifa (ma'sul va «bajarilmasa»).
    await _step(tester, 3);
    await tapChip(tester, 'Javob');
    await tapText(tester, '+ Vazifa qoʻshish');
    await enter(tester, 'Vazifa', 'Buyurtmalarni qabul qilish');
    await choose(tester, 'Masʼul', 'Anvar Karimov');
    await enter(tester, 'Bajarilmasa nima boʻladi', '1 kun ichida xabar beradi');
    await tapText(tester, 'Saqlash va keyingisi');
    await waitFor(tester, find.text('4. Foyda qanday boʻlinadi?'));
    // 6. Pul va hisob.
    await _step(tester, 6);
    await tapChip(tester, 'Javob');
    await enter(tester, 'Pul qayerda turadi', 'Anvarning kartasida');
    await choose(tester, 'Hisobni kim yuritadi', 'Anvar Karimov');
    await enter(tester, 'Necha kunda bir koʻrib chiqiladi', '30');
    await tapText(tester, 'Saqlash va keyingisi');
    // 7. Ajralish.
    await waitFor(tester, find.text('7. Qanday ajralib chiqiladi?'));
    await tapChip(tester, 'Javob');
    await enter(tester, 'Oldindan ogohlantirish (kun)', '30');
    await enter(tester, 'Ulush qanday baholanadi', 'Bozor narxida');
    await enter(tester, 'Qachon va qanday toʻlanadi', '3 oy ichida, teng qismlarda');
    await enter(tester, 'Mol-mulk qanday boʻlinadi', 'Hissaga koʻra');
    await tapText(tester, 'Saqlash va keyingisi');
    // 8. Hakam va guvoh.
    await waitFor(tester, find.text('8. Kelisha olmasak, kim hakam?'));
    await tapChip(tester, 'Javob');
    await enter(tester, 'Hakam (toʻliq ism)', 'Hasan Yusupov');
    await enter(tester, 'Tomonlarga aloqasi', 'mahalla oqsoqoli');
    await enter(tester, '1-guvoh', 'Jamshid Aliyev');
    await tapText(tester, 'Saqlash va keyingisi');
    // 9. Muddat.
    await waitFor(tester, find.text('9. Qachon yangilanadi?'));
    await tapChip(tester, 'Javob');
    // O'tgan oydan boshlangan — bugungi yozuvlar muddat ichida.
    await pickDate(tester, 'Boshlanish sanasi', -1);
    await enter(tester, 'Muddat (oy)', '12');
    await pickDate(tester, 'Qayta koʻrib chiqish sanasi', 6);
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.text('9 / 9 — shartnomani imzolash mumkin.'));
    await scrollTop(tester);
    await shot(tester, 'android-21-partnership-9');

    // 10. Imzolar: tomonlar, guvoh va hakam shu telefonda.
    await _step(tester, 10);
    for (final name in ['Dilshod Rahimov', 'Anvar Karimov', 'Jamshid Aliyev', 'Hasan Yusupov']) {
      await _sign(tester, name);
    }
    await waitFor(tester, find.text('1-versiyani hamma imzoladi.'));
    expect(find.byType(SvgPicture), findsNWidgets(4));
    await scrollTop(tester);
    await shot(tester, 'android-22-signed');

    // 11. Boshlash: «bu qarz emas», oila roziligi → faol.
    await _step(tester, 11);
    await tapText(tester, 'Tushundim, bu qarz emas');
    await waitFor(tester, find.text('Anvar rozi'));
    await tapText(tester, 'Anvar rozi');
    // «Boshlash» tugmasi rozilikdan oldin ham bor — rozilik yozilganini kutamiz.
    await waitFor(tester, find.textContaining('✓ rozi,'));
    await tapText(tester, 'Sheriklikni boshlash');
    await waitFor(tester, find.textContaining('Sheriklik faol'));

    // Kassa daftari: kirim (chek rasmi bilan) va xarajat.
    await tapText(tester, 'Kassa daftari');
    await waitFor(tester, find.text('Daftarga yozish'));
    await enter(tester, 'Summa', '5 000 000');
    await enter(tester, 'Izoh', 'Toʻy liboslari buyurtmasi');
    await tapText(tester, 'Fayl tanlash');
    await waitFor(tester, find.text('chek.png'));
    await tapText(tester, 'Yozish');
    // Saqlangach forma tozalanadi — yozuv faqat ro'yxatda qoladi.
    await waitFor(tester, find.text('Yozuvlar'));
    await tapChip(tester, 'Xarajat');
    await enter(tester, 'Summa', '2 200 000');
    await enter(tester, 'Izoh', 'Mato va iplar');
    await tapText(tester, 'Yozish');
    await waitFor(tester, find.text('2${nb}800${nb}000${nb}soʻm'));
    // Ilova qilingan chek — rasm oynasi.
    await tapText(tester, 'chek.png');
    await waitFor(tester, find.byType(AlertDialog));
    await tapText(tester, 'Yopish');

    // Davr taqsimoti: sof 2,8 mln → mehnat egasiga (bizga) 50 %.
    await tapText(tester, 'Taqsimotni koʻrish');
    await waitFor(tester, find.text('Oila byudjetiga daromad boʻlib tushadi: 1${nb}400${nb}000${nb}soʻm'));
    await shot(tester, 'android-23-distribution');
    await tapText(tester, 'Davrni yopish');
    await waitFor(tester, find.textContaining('1-davr: '));
    await tapText(tester, 'Sherik uchun hisobot (PDF)');
    await waitShared(tester, device, (n) => n == 'davr-1.pdf');

    // Ko'rik va nizo: vazifa hodisasi → «bajarilmasa» bandi eslatiladi.
    await tapText(tester, 'Koʻrik va nizo');
    await waitFor(tester, find.text('Bajara olmayapman'));
    await tapText(tester, 'Bajara olmayapman');
    await enter(tester, 'Sabab', 'Telefon buzildi');
    await enter(tester, 'Taklif qilingan yechim', 'Buyurtmalarni Gulnora qabul qiladi');
    await tapText(tester, 'Xabar berish');
    await waitFor(tester, find.textContaining('Xabar jurnalga yozildi'));
    expect(find.textContaining('1 kun ichida xabar beradi', findRichText: true), findsWidgets);
    await shot(tester, 'android-24-incident');

    // Ochiq hisob ko'rigi: zanjir butun, ikki tomon rozi → bayonnoma va PDF.
    await tapText(tester, 'Koʻrikni boshlash');
    await waitFor(tester, find.text('Zanjir tekshiruvi: barcha yozuvlar butun.'));
    await tapChip(tester, 'Koʻrdim, roziman');
    await tapChip(tester, 'Koʻrdim, roziman', index: 1);
    await scrollTop(tester);
    await shot(tester, 'android-25-review');
    await tapText(tester, 'Bayonnomani yozish');
    await waitFor(tester, find.text('Butun'));
    await tapText(tester, 'Bayonnoma PDF');
    await waitShared(tester, device, (n) => n == 'korik-1.pdf');

    // Nizo: ochiladi → taqsimot to'xtaydi → hakam qarori bilan yopiladi.
    await tapText(tester, 'Nizo ochish');
    await enter(tester, 'Mavzu', 'Material narxi');
    await tapText(tester, '6. Pul va hisob');
    await enter(tester, 'Talab', 'Chek koʻrsatilsin');
    await tapText(tester, 'Nizo ochish');
    await waitFor(tester, find.textContaining('Nizo ochiq.'));
    await enter(tester, 'Qaror mazmuni', 'Chek koʻrsatildi, davom etiladi');
    await tapText(tester, 'Qarorni yozish');
    await waitFor(tester, find.textContaining('Hakam qarori — Hasan Yusupov'));
    expect(find.textContaining('Nizo ochiq.'), findsNothing);
    await tester.tap(find.byType(BackButton));
    await settle(tester, rounds: 10);

    // Kelishuvlar markazi: qidiruv, oilaviy kelishuv va PIN bilan tasdiq.
    await goTo(tester, 'Kelishuvlar');
    await waitFor(tester, find.text('Tikuv ustaxonasi'));
    await enter(tester, 'Qidirish', 'yoʻq narsa');
    await waitFor(tester, find.text('Kelishuv topilmadi.'));
    await enter(tester, 'Qidirish', '');
    await tapChip(tester, 'Oilaviy kelishuvlar');
    await tapText(tester, 'Uyda kim nima qiladi');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.text('Anvar tasdiqlaydi'));
    await tapText(tester, 'Anvar tasdiqlaydi');
    await enter(tester, 'Anvar: PIN bilan tasdiqlang', '135790');
    await tapText(tester, 'Tasdiqlash');
    await waitFor(tester, find.text('Hamma tasdiqlagan'));
    await scrollTop(tester);
    await shot(tester, 'android-26-family');

    // Taklif tekshiruvi (menyudan): «kafolatli foyda» → qizil.
    tester.state<ScaffoldState>(find.byType(Scaffold).first).openDrawer();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.descendant(of: find.byType(Drawer), matching: find.text('Taklifni tekshirish')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    for (final (i, reply) in ['Ha', 'Yoʻq', 'Yoʻq', 'Ha', 'Ha', 'Yoʻq', 'Yoʻq', 'Yoʻq', 'Yoʻq'].indexed) {
      // Har savolda «Ha / Yoʻq / Bilmayman»: `i`-savolning chipi — `i`-o'rinda.
      await tapChip(tester, reply, index: i);
    }
    await tapText(tester, 'Tekshirish');
    await waitFor(tester, find.text('Qizil: pul bermang'));
    await shot(tester, 'android-27-offer');
    await tapText(tester, 'Yopish');

    // Zaxira nusxa: eksport → shu faylni import oynasida ochish.
    await goTo(tester, 'Sinxronlash');
    await enter(tester, 'Fayl paroli', 'Anvar-2026!');
    await enter(tester, 'Parolni takrorlang', 'Anvar-2026!');
    await tapText(tester, 'Faylni saqlash');
    await waitFor(tester, find.textContaining('Fayl saqlandi'));
    final backup = device.shared.last;
    expect(backup.name, endsWith('.baraka'));
    picked = (name: backup.name, bytes: backup.bytes);
    await tapText(tester, 'Fayl tanlash');
    await waitFor(tester, find.text(backup.name));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    final pw = find.widgetWithText(TextField, 'Fayl paroli').last;
    await tester.ensureVisible(pw);
    await tester.enterText(pw, 'Anvar-2026!');
    await tester.pump();
    // O'z faylini qayta qabul qilish — yadro rad etadi (yozuvlar ikki marta tushmasin).
    await tapText(tester, 'Koʻrib chiqish');
    await waitFor(tester, find.text('Bu fayl shu qurilmaning oʻzida yaratilgan'));
    expect(find.text('Qabul qilish'), findsNothing);
  });
}
