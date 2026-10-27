import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/lump_sum.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

/// Matndagi summa (bo'shliqlarsiz) — formatdagi ingichka bo'shliqlarga
/// bog'lanmaslik uchun.
String digits(WidgetTester tester, String key) => tester
    .widget<Text>(find.byKey(Key(key)))
    .data!
    .replaceAll(RegExp(r'[\s  ]'), '');

Future<void> typeAmount(WidgetTester tester, String value) async {
  for (final k in value.split('')) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
  await tester.tap(find.byKey(const Key('amount-sheet-done')));
  await tester.pumpAndSettle();
}

void main() {
  group('splitLumpSum (SPEC 2G.5)', () {
    test('zaxira toʻlmaguncha sarmoyaga faqat ortgani', () {
      final a = splitLumpSum(som(10000000), som(18000000));
      expect(a.toReserve, som(10000000));
      expect(a.toInvest, som(0));
      final b = splitLumpSum(som(227700000), som(18000000));
      expect(b.toReserve, som(18000000));
      expect(b.toInvest, som(209700000));
    });

    test('zaxira toʻla (kamomad 0 yoki manfiy) — hammasi sarmoyaga', () {
      expect(splitLumpSum(som(5000000), som(0)).toInvest, som(5000000));
      expect(splitLumpSum(som(5000000), som(-1)).toReserve, som(0));
    });

    test('valyuta mos kelmasa — xato', () {
      expect(
        () => splitLumpSum(
          Money.major(100, CurrencyCode.usd),
          som(1000000),
        ),
        throwsA(isA<CurrencyMismatchException>()),
      );
    });
  });

  testWidgets('katta summa: maqsad yoʻq boʻlsa shu ekranda belgilanadi', (
    tester,
  ) async {
    // Qurilmada topildi: «avval belgilang» deyilardi-yu, qayerda —
    // ko'rsatilmasdi.
    final env = await pumpBarakaApp(tester);
    env.container.read(appRouterProvider).go(AppRoutes.vaultLumpSum);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('lump-estimate')));
    await tester.pumpAndSettle();
    await typeAmount(tester, '3000000');
    expect(find.byKey(const Key('lump-no-target')), findsNothing);
    final o = await env.container.read(vaultOverviewProvider.future);
    expect(o.reserve.missing, som(18000000));
  });

  testWidgets(
    'katta summa: dollar kurs bilan, avval 6 oylik zaxira, qolgani hunarga',
    (tester) async {
      final env = await pumpBarakaApp(tester);
      env.container.read(appRouterProvider).go(AppRoutes.vaultLumpSum);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('lump-no-target')), findsOneWidget);

      // 6 oylik zarur xarajat: 3 mln/oy → zaxira 18 mln.
      await (await env.container.read(
        essentialSpendServiceProvider.future,
      )).setEstimate(som(3000000));
      env.container.invalidate(vaultOverviewProvider);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('lump-no-target')), findsNothing);

      await tester.tap(find.byKey(const Key('lump-cur-usd')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('lump-amount')));
      await tester.pumpAndSettle();
      await typeAmount(tester, '18000');
      await tester.enterText(find.byKey(const Key('lump-rate')), '12650');
      await tester.pump();
      await tester.pumpAndSettle();

      // 18 000 × 12 650 = 227 700 000 soʻm: 18 mln zaxiraga, qolgani hunarga.
      expect(digits(tester, 'lump-reserve'), contains('18000000'));
      expect(digits(tester, 'lump-invest'), contains('209700000'));

      await tester.ensureVisible(find.byKey(const Key('lump-deposit')));
      await tester.tap(find.byKey(const Key('lump-deposit')));
      await tester.pumpAndSettle();
      final o = await (await env.container.read(
        vaultServiceProvider.future,
      )).overview();
      expect(o.reserveBalance, som(18000000));
      expect(o.reserve.missing, som(0));
    },
  );
}
