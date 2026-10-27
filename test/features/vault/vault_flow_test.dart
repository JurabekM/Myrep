import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

/// Drift soʻrovlari test zonasida toʻgʻridan-toʻgʻri bajariladi.
/// `tester.runAsync` ishlatilmaydi: u ijrochini real zonaga bogʻlab, keyingi
/// soxta vaqtdagi soʻrovlarni osiltirib qoʻyadi.
Future<T> _direct<T>(Future<T> Function() f) => f();
String n(String s) => s.replaceAll(' ', nbsp);

/// Bosish hisoblagichi: har `tap` shu orqali oʻtadi.
class TapCounter {
  TapCounter(this.tester);

  final WidgetTester tester;
  int count = 0;

  Future<void> tap(Finder f) async {
    count++;
    await tester.tap(f);
    await tester.pumpAndSettle();
  }
}

Future<void> seedIncome(
  TestEnv env,
  int major, {
  IncomeSource source = IncomeSource.dailyWork,
  PaymentChannel channel = PaymentChannel.cash,
}) async {
  final hh = (await DriftHouseholdRepository(
    env.db,
    env.clock,
  ).current()).meta.id;
  await DriftIncomeRepository(env.db, env.clock).add(
    Income(
      meta: env.container.read(syncMetaFactoryProvider).create(hh),
      amount: som(major),
      source: source,
      channel: channel,
      receivedAt: env.clock.nowUtc(),
    ),
  );
  env.clock.advance(const Duration(minutes: 1));
}

Future<List<Income>> incomesOf(TestEnv env) async {
  final hh = (await DriftHouseholdRepository(
    env.db,
    env.clock,
  ).current()).meta.id;
  return DriftIncomeRepository(env.db, env.clock).listActive(hh);
}

void main() {
  group('tez daromad kiritish', () {
    testWidgets('3 bosishda saqlanadi: «Daromad» → oxirgi summa → «Saqlash»', (
      tester,
    ) async {
      final env = await pumpBarakaApp(tester);
      await seedIncome(env, 150000);
      final taps = TapCounter(tester);

      await taps.tap(find.byKey(const Key('home-add-income')));
      await taps.tap(find.byKey(const Key('recent-amount-0')));
      await taps.tap(find.byKey(const Key('income-save')));

      expect(taps.count, 3);
      final saved = await _direct(() => incomesOf(env));
      expect(saved, hasLength(2));
      expect(saved.first.amount, som(150000));
      // Darhol ulush taklifi: 5 % → 7 500 → 8 000 soʻm.
      expect(find.textContaining(n('8 000 soʻm')), findsOneWidget);
      expect(find.textContaining('kelajagingiz uchun'), findsOneWidget);
    });

    testWidgets('oxirgi manba va kanal oldindan tanlangan', (tester) async {
      final env = await pumpBarakaApp(tester);
      await seedIncome(
        env,
        90000,
        source: IncomeSource.order,
        channel: PaymentChannel.card,
      );
      await tester.tap(find.byKey(const Key('home-add-income')));
      await tester.pumpAndSettle();

      ChoiceChip chip(String name) =>
          tester.widget<ChoiceChip>(find.byKey(Key('choice-$name')));
      expect(chip('order').selected, isTrue);
      expect(chip('card').selected, isTrue);
      expect(chip('dailyWork').selected, isFalse);

      for (final d in ['2', '5', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$d')));
        await tester.pump();
      }
      expect(find.text(n('25 000 soʻm')), findsOneWidget);
      await tester.tap(find.byKey(const Key('income-save')));
      await tester.pumpAndSettle();
      final saved = (await _direct(() => incomesOf(env))).first;
      expect(saved.amount, som(25000));
      expect(saved.source, IncomeSource.order);
      expect(saved.channel, PaymentChannel.card);
    });

    testWidgets('summa boʻlmasa saqlash oʻchiq; oʻchirish tugmasi', (
      tester,
    ) async {
      await pumpBarakaApp(tester);
      await tester.tap(find.byKey(const Key('home-add-income')));
      await tester.pumpAndSettle();
      FilledButton save() =>
          tester.widget<FilledButton>(find.byKey(const Key('income-save')));
      expect(save().onPressed, isNull);
      await tester.tap(find.byKey(const Key('amount-key-7')));
      await tester.pump();
      expect(save().onPressed, isNotNull);
      await tester.tap(find.byKey(const Key('amount-key-back')));
      await tester.pump();
      expect(save().onPressed, isNull);
    });
  });

  group('ulush taklifi', () {
    Future<TestEnv> openOffer(WidgetTester tester) async {
      final env = await pumpBarakaApp(tester);
      await tester.tap(find.byKey(const Key('home-add-income')));
      await tester.pumpAndSettle();
      for (final d in ['1', '5', '0', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$d')));
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('income-save')));
      await tester.pumpAndSettle();
      return env;
    }

    Future<Money> balance(WidgetTester tester, TestEnv env) async {
      final o = await _direct(
        () async => (await env.container.read(
          vaultServiceProvider.future,
        )).overview(),
      );
      return o.balance;
    }

    testWidgets('[Ajratish] — DEPOSIT yoziladi', (tester) async {
      final env = await openOffer(tester);
      await tester.tap(find.byKey(const Key('share-allocate')));
      await tester.pumpAndSettle();
      expect(await balance(tester, env), som(8000));
      expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
    });

    testWidgets('[Boshqa summa] — oʻz summasi', (tester) async {
      final env = await openOffer(tester);
      await tester.tap(find.byKey(const Key('share-other')));
      await tester.pumpAndSettle();
      // Taklif (8 000) dan boshlanadi; tozalab 15 000 kiritamiz.
      for (var i = 0; i < 4; i++) {
        await tester.tap(find.byKey(const Key('amount-key-back')).last);
        await tester.pump();
      }
      for (final d in ['1', '5', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$d')).last);
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('amount-sheet-done')));
      await tester.pumpAndSettle();
      expect(await balance(tester, env), som(15000));
    });

    testWidgets('[Bu safar emas] — hech narsa yozilmaydi, ayblanmaydi', (
      tester,
    ) async {
      final env = await openOffer(tester);
      await tester.tap(find.byKey(const Key('share-skip')));
      await tester.pumpAndSettle();
      expect(await balance(tester, env), som(0));
      expect(find.textContaining('keyingi safar'), findsOneWidget);
    });
  });

  group('«Kelajagim» ekrani', () {
    Future<TestEnv> openVault(WidgetTester tester) async {
      final env = await pumpBarakaApp(tester);
      env.container.read(appRouterProvider).go(AppRoutes.vault);
      await tester.pumpAndSettle();
      return env;
    }

    testWidgets('odat koʻrsatkichi balansdan oldin turadi', (tester) async {
      await openVault(tester);
      final streak = tester.getTopLeft(find.byKey(const Key('vault-streak')));
      final balance = tester.getTopLeft(find.byKey(const Key('vault-balance')));
      expect(streak.dy, lessThan(balance.dy));
      expect(find.text('0 hafta'), findsOneWidget);
      expect(find.textContaining('5 %'), findsOneWidget);
    });

    testWidgets('«avval yigʻilgan pul»: bir martalik boshlangʻich balans', (
      tester,
    ) async {
      await openVault(tester);
      await tester.scrollUntilVisible(
        find.byKey(const Key('vault-initial-action')),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('vault-initial-action')));
      await tester.pumpAndSettle();
      for (final d in ['2', '000', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$d')));
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('amount-sheet-done')));
      await tester.pumpAndSettle();
      expect(find.text(n('2 000 000 soʻm')), findsWidgets);
      expect(find.byKey(const Key('vault-initial')), findsNothing);
      expect(find.text('Boshlangʻich jamgʻarma'), findsOneWidget);
      // «Avval yigʻilgan pul» odatga kirmaydi (odat kartasi tepada).
      await tester.scrollUntilVisible(
        find.text('0 hafta'),
        -300,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('0 hafta'), findsOneWidget);
    });

    testWidgets('ulushni 10 % ga oʻzgartirish', (tester) async {
      final env = await openVault(tester);
      await tester.tap(find.byKey(const Key('vault-edit-rule')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('rule-10')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('rule-progressive')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('rule-save')));
      await tester.pumpAndSettle();
      expect(find.textContaining('10 %'), findsOneWidget);
      expect(find.textContaining('progressiv'), findsOneWidget);
      final rule = (await _direct(
        () async => (await env.container.read(
          vaultServiceProvider.future,
        )).overview(),
      )).rule;
      expect(rule.basisPoints, 1000);
      expect(rule.mode, AllocationMode.progressive);
    });

    testWidgets('qatʼiy oylik summa', (tester) async {
      await openVault(tester);
      await tester.tap(find.byKey(const Key('vault-edit-rule')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('rule-fixed-edit')));
      await tester.pumpAndSettle();
      for (final d in ['3', '0', '0', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$d')));
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('amount-sheet-done')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('rule-save')));
      await tester.pumpAndSettle();
      expect(find.textContaining('oyiga ${n("300 000 soʻm")}'), findsOneWidget);
    });
  });

  group('pul olish — sabab, pauza va PIN', () {
    Future<TestEnv> openWithdraw(WidgetTester tester) async {
      final env = await pumpBarakaApp(tester);
      await _direct(
        () async => (await env.container.read(
          vaultServiceProvider.future,
        )).setInitialBalance(som(1000000)),
      );
      env.container.read(appRouterProvider).go(AppRoutes.vault);
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('vault-withdraw')));
      await tester.pumpAndSettle();
      // Qorovul puldan — «favqulodda holat» tasdigʻi (SPEC 2C.3).
      await tester.ensureVisible(find.byKey(const Key('withdraw-emergency')));
      await tester.tap(find.byKey(const Key('withdraw-emergency')));
      await tester.pump();
      return env;
    }

    Future<Money> balance(WidgetTester tester, TestEnv env) async =>
        (await _direct(
          () async => (await env.container.read(
            vaultServiceProvider.future,
          )).overview(),
        )).balance;

    FilledButton btn(WidgetTester tester, String key) =>
        tester.widget<FilledButton>(find.byKey(Key(key)));

    testWidgets('eslatma koʻrinadi; sababsiz davom etib boʻlmaydi', (
      tester,
    ) async {
      await openWithdraw(tester);
      expect(find.byKey(const Key('withdraw-reminder')), findsOneWidget);
      expect(find.textContaining('kelajakdagi oʻzingizniki'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('withdraw-amount')), '50000');
      await tester.pump();
      expect(btn(tester, 'withdraw-continue').onPressed, isNull);
      await tester.enterText(find.byKey(const Key('withdraw-reason')), '   ');
      await tester.pump();
      expect(btn(tester, 'withdraw-continue').onPressed, isNull);
      await tester.enterText(find.byKey(const Key('withdraw-reason')), 'Dori');
      await tester.pump();
      expect(btn(tester, 'withdraw-continue').onPressed, isNotNull);
      // Favqulodda tasdigʻi olib tashlansa — davom etib boʻlmaydi.
      await tester.tap(find.byKey(const Key('withdraw-emergency')));
      await tester.pump();
      expect(btn(tester, 'withdraw-continue').onPressed, isNull);
      await tester.tap(find.byKey(const Key('withdraw-emergency')));
      await tester.pump();
      await tester.enterText(
        find.byKey(const Key('withdraw-amount')),
        '2000000',
      );
      await tester.pump();
      expect(btn(tester, 'withdraw-continue').onPressed, isNull);
    });

    Future<void> fillAndPause(WidgetTester tester) async {
      await tester.enterText(
        find.byKey(const Key('withdraw-amount')),
        '250000',
      );
      await tester.enterText(
        find.byKey(const Key('withdraw-reason')),
        'Davolanish',
      );
      await tester.pump();
      await tester.tap(find.byKey(const Key('withdraw-continue')));
      await tester.pump();
      // Pauza: 5 soniya tasdiqlab boʻlmaydi.
      expect(btn(tester, 'withdraw-pause-confirm').onPressed, isNull);
      await tester.pump(const Duration(seconds: 4));
      expect(btn(tester, 'withdraw-pause-confirm').onPressed, isNull);
      await tester.pump(const Duration(seconds: 1));
      expect(btn(tester, 'withdraw-pause-confirm').onPressed, isNotNull);
      await tester.tap(find.byKey(const Key('withdraw-pause-confirm')));
      await tester.pumpAndSettle();
      expect(find.text('PIN kodni qayta kiriting'), findsOneWidget);
    }

    testWidgets('notoʻgʻri PIN yoki bekor qilish — pul olinmaydi', (
      tester,
    ) async {
      final env = await openWithdraw(tester);
      await fillAndPause(tester);
      await enterPin(tester, '000001');
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('pin-confirm-message')), findsOneWidget);
      await tester.tap(find.byType(CloseButton));
      await tester.pumpAndSettle();
      expect(await balance(tester, env), som(1000000));
    });

    testWidgets('toʻgʻri PIN — pul olinadi, sabab tarixda', (tester) async {
      final env = await openWithdraw(tester);
      await fillAndPause(tester);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(await balance(tester, env), som(750000));
      // Qayta toʻldirish rejasi: 250 000 / 6 oy → 42 000 (1 000 gacha yuqoriga).
      expect(find.byKey(const Key('refill-plan')), findsOneWidget);
      expect(find.textContaining(n('42 000 soʻm')), findsOneWidget);
      await tester.tap(find.text('Tushunarli'));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('Olindi: Davolanish'),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('Olindi: Davolanish'), findsOneWidget);
    });

    testWidgets('pauzada «Fikrimdan qaytdim»', (tester) async {
      final env = await openWithdraw(tester);
      await tester.enterText(find.byKey(const Key('withdraw-amount')), '1000');
      await tester.enterText(find.byKey(const Key('withdraw-reason')), 'Bozor');
      await tester.pump();
      await tester.tap(find.byKey(const Key('withdraw-continue')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('withdraw-pause-cancel')));
      await tester.pumpAndSettle();
      expect(find.text('PIN kodni qayta kiriting'), findsNothing);
      expect(await balance(tester, env), som(1000000));
    });
  });
}
