// A1: Uy makoni — xarajat, qarz (reja bilan) va to'lov, «Qarzdan chiqish» rejimi, marosim,
// qarz tilxati (PDF ulashiladi), «Kelajagim»dan PIN bilan pul olish. Haqiqiy yadro bilan.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

Future<void> _anim(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

const nb = ' ';

/// Kalendardan oyning 28-kunini tanlash (yaqin kelajak yoki o'tgan oy — yadro tekshiradi).
Future<void> pickDay(WidgetTester tester, String label, {bool nextMonth = true}) async {
  await _anim(tester);
  final f = find.ancestor(of: find.text(label), matching: find.byType(InputDecorator));
  await tester.ensureVisible(f.first);
  await tester.tap(f.first);
  await _anim(tester);
  if (nextMonth) {
    await tester.tap(find.byIcon(Icons.chevron_right));
    await _anim(tester);
  }
  await tester.tap(find.text('28').last);
  await tester.pump(const Duration(milliseconds: 200));
  await tester.tap(find.byType(TextButton).last);
  await _anim(tester);
}

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('Uy: xarajat, qarz, rejim, marosim, tilxat, Kelajagim', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    await tester.runAsync(device.bootstrap);
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));

    // Xarajat: kategoriya va toifa — ZARUR yig'indisida ko'rinadi.
    await goTo(tester, 'Xarajatlar');
    await enter(tester, 'Summa', '500 000');
    await choose(tester, 'Kategoriya', 'Oziq-ovqat');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.text('500${nb}000${nb}soʻm'));
    await scrollTop(tester);
    await shot(tester, 'android-12-expenses');

    // Qarz: qo'lda reja (1 qator) → kartada qoldiq → to'lov.
    await goTo(tester, 'Qarzlar');
    await tapText(tester, 'Qarz qoʻshish');
    await enter(tester, 'Kreditor (ism yoki bank)', 'Togʻam');
    await enter(tester, 'Hozirgi qoldiq', '15 000 000');
    await pickDay(tester, 'Sana 1');
    await enter(tester, 'Summa 1', '15 000 000');
    await tapText(tester, 'Saqlash');
    // Karta chizilguncha: «Togʻam» matni forma maydonida ham bor (CI'da poyga bo'lgan).
    await waitFor(tester, find.text('Toʻlov yozish'));
    expect(find.text('Togʻam'), findsWidgets);
    expect(find.text('15${nb}000${nb}000${nb}soʻm'), findsWidgets);
    await scrollTop(tester);
    await shot(tester, 'android-13-debts');
    await tapText(tester, 'Toʻlov yozish');
    await enter(tester, 'Summa', '5 000 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.text('10${nb}000${nb}000${nb}soʻm'));

    // «Qarzdan chiqish»: rejim yoqiladi.
    await goTo(tester, 'Qarzdan chiqish');
    await tapText(tester, 'Yoqish');
    await waitFor(tester, find.text('«Qarzdan chiqish» rejimi'));
    await scrollTop(tester);
    await shot(tester, 'android-14-payoff');

    // Marosim: yaratish → batafsil sahifa → xarajat qatori → jami.
    await goTo(tester, 'Marosimlar');
    await enter(tester, 'Nomi', 'Oʻgʻlimning toʻyi');
    await enter(tester, 'Birinchi stsenariy', 'Oddiy');
    await enter(tester, 'Mehmonlar soni', '200');
    await tapText(tester, 'Yaratish');
    await waitFor(tester, find.text('Stsenariy'));
    await enter(tester, 'Xarajat (osh, xonanda, sarpo…)', 'Osh');
    await choose(tester, 'Hisob turi', 'kishi boshiga');
    await enter(tester, 'Summa yoki kishi boshiga narx', '50 000');
    await tapText(tester, 'Qoʻshish');
    await waitFor(tester, find.text('10${nb}000${nb}000${nb}soʻm'));
    await scrollTop(tester);
    await shot(tester, 'android-15-ceremony');
    await tester.tap(find.byType(BackButton));
    await settle(tester, rounds: 10);

    // Qarz tilxati: saqlanadi, PDF ulashiladi, qisqa kod ko'rsatiladi.
    await goTo(tester, 'Qarz tilxati');
    await enter(tester, 'Qarz beruvchi', 'Karim');
    await enter(tester, 'Qarz oluvchi', 'Anvar');
    await enter(tester, 'Qarz summasi', '2 000 000');
    await enter(tester, 'Joy (shahar, mahalla)', 'Toshkent');
    await pickDay(tester, 'Sana 1');
    await enter(tester, 'Summa 1', '2 000 000');
    await tapText(tester, 'Tilxatni saqlash va PDF');
    // PDF (typst) debug yadroda bir necha soniya.
    await waitFor(tester, find.byKey(const Key('receipt-code')), rounds: 2000);
    expect(device.shared.single.name, startsWith('tilxat-'));
    expect(String.fromCharCodes(device.shared.single.bytes.take(4)), '%PDF');

    // «Kelajagim»: boshlang'ich qoldiq, keyin PIN va sabab bilan pul olish.
    await goTo(tester, 'Kelajagim');
    await enter(tester, 'Boshlangʻich balans (roʻmolcha)', '1 000 000');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.textContaining('1${nb}000${nb}000'));
    await tapText(tester, 'Pul olish');
    await enter(tester, 'Summa', '200 000');
    await enter(tester, 'Sabab', 'Dori');
    await enter(tester, 'PIN', '135790');
    await tapText(tester, 'Pul olish');
    await waitFor(tester, find.textContaining('800${nb}000'));
  });
}
