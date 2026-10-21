// A0: onboarding (5 qadam) → tiklash kodi → ilova → qulf → PIN bilan ochish. Haqiqiy yadro.
import 'package:baraka/core/core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

void main() {
  setUpAll(() async {
    await initRust();
    await loadFonts();
  });

  testWidgets('onboarding → qulf → ochish', (tester) async {
    phone(tester);
    final device = (await tester.runAsync(Device.create))!;
    await tester.pumpWidget(device.app());
    await waitFor(tester, find.text('Til va boshlash'));
    expect(find.text('1 / 5'), findsNothing);
    await shot(tester, 'android-01-setup-language');

    await tapText(tester, 'Davom etish');
    expect(find.text('Oilangiz'), findsOneWidget);
    await enter(tester, 'Oila nomi', 'Anvarning oilasi');
    await enter(tester, 'Ismingiz', 'Anvar');
    await tapText(tester, 'Davom etish');
    await tapText(tester, 'Oylik maosh');
    await tapText(tester, 'Davom etish');
    await tapText(tester, 'Yoʻq');
    await tapText(tester, 'Davom etish');
    await enter(tester, '6 xonali PIN', '135790');
    await enter(tester, 'PINʼni takrorlang', '135790');
    await shot(tester, 'android-02-setup-pin');
    await tapText(tester, 'Boshlash');

    await waitFor(tester, find.byKey(const Key('recovery-code')));
    final code = tester.widget<SelectableText>(find.byKey(const Key('recovery-code'))).data!;
    expect(code.replaceAll(RegExp('[^A-Z0-9]'), '').length, greaterThanOrEqualTo(20));
    await tapText(tester, 'Yozib oldim');

    // Ilova: sarlavhada makon nomi, menyuda sozlamalar.
    await waitFor(tester, find.byTooltip('Qulflash'));
    final status = await tester.runAsync(device.services.core.status);
    expect(status!.unlocked, isTrue);

    await tester.tap(find.byTooltip('Qulflash'));
    await waitFor(tester, find.text('Daftar qulflangan'));
    await shot(tester, 'android-03-lock');
    await enter(tester, 'PIN', '000000');
    await waitFor(tester, find.text('PIN notoʻgʻri'));
    await enter(tester, 'PIN', '135790');
    await waitFor(tester, find.byTooltip('Qulflash'));
    await expectLater(tester.runAsync(device.services.core.household), completion(isA<HouseholdDto>()));
  });
}
