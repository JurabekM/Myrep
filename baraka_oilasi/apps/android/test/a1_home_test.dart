// A1: bosh sahifa — daromad → ulush taklifi → «Ajratish» → KPI yangilanadi (yadro hodisasi orqali).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('daromad va ulush', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    await tester.runAsync(device.bootstrap);
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.byKey(const Key('kpi-paid-to-self')));
    await waitFor(tester, find.textContaining('0\u00a0soʻm'));
    await shot(tester, 'android-10-home');

    await tester.tap(find.text('Daromad kiritish').last);
    await settle(tester, rounds: 6);
    await enter(tester, 'Summa', '3 000 000');
    await enter(tester, 'Manba', 'Oylik');
    await tapText(tester, 'Saqlash');
    await waitFor(tester, find.byKey(const Key('income-share-offer')));
    expect(find.textContaining('150\u00a0000\u00a0soʻm'), findsWidgets);
    await shot(tester, 'android-11-income-share');
    await tapText(tester, 'Ajratish');
    await waitFor(
      tester,
      find.descendant(of: find.byKey(const Key('kpi-paid-to-self')), matching: find.textContaining('150\u00a0000')),
    );
  });
}
