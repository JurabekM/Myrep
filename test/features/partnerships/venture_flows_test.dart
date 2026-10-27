import 'dart:async';

import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/agreements.dart';
import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> open(WidgetTester tester, TestEnv env, String route) async {
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

/// Element ekranda bo'lmasa — ro'yxat boshiga qaytib, pastga aylantirish.
Future<void> reveal(WidgetTester tester, Finder f) async {
  final scrollable = find.byType(Scrollable).first;
  if (f.evaluate().isEmpty) {
    await tester.fling(scrollable, const Offset(0, 3000), 5000);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(f, 200, scrollable: scrollable);
  }
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

Future<void> typeAmount(WidgetTester tester, List<String> keys) async {
  for (final k in keys) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
  await tester.tap(find.byKey(const Key('amount-sheet-done')));
  await tester.pumpAndSettle();
}

/// Faol mudaraba: Gʻayrat — 30 mln uskuna (40 %), men — mehnat (60 %).
Future<Partnership> seedActive(TestEnv env) async {
  final owner = (await env.container.read(membersProvider.future)).single;
  final s = await env.container.read(partnershipServiceProvider.future);
  final p = await s.create(
    title: 'Tikuvchilik sexi',
    type: PartnershipType.mudaraba,
    partners: [
      PartnerDraft(
        name: 'Gʻayrat',
        role: PartnerRole.capitalProvider,
        profit: const ProfitShareInput.percent(4000),
        capital: [
          CapitalItem(
            kind: CapitalKind.equipment,
            title: 'Overlok',
            amount: som(30000000),
          ),
        ],
      ),
      const PartnerDraft(
        name: 'Dilnoza',
        role: PartnerRole.worker,
        profit: ProfitShareInput.percent(6000),
        isMe: true,
      ),
    ],
    termMonths: 12,
    reportPeriod: ReportPeriod.monthly,
    endTerms: 'a',
    disputeTerms: 'b',
  );
  await completeAgreementIn(
    env.container,
    AgreementSource.partnership,
    p.meta.id,
  );
  for (final x in (await s.view(p)).signers) {
    await s.sign(p, x, x.name, [1]);
  }
  await s.acknowledgeNotDebt(p);
  await s.consent(p, owner, '');
  return s.activate(p);
}

void main() {
  testWidgets('taklif detektori: kafolatli foyda — qizil, bayroq izohlanadi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.offerCheck);
    await tester.enterText(find.byKey(const Key('offer-title')), 'Signal');
    for (final (q, a) in [
      ('guaranteed', 'yes'),
      ('lossShared', 'yes'),
      ('realGoods', 'yes'),
      ('recruitment', 'no'),
      ('pressure', 'no'),
      ('writtenContract', 'yes'),
      // 7-qonun (SPEC 2G.1).
      ('exitEasy', 'yes'),
      ('license', 'yes'),
      ('verifiedInPerson', 'yes'),
    ]) {
      await tapIn(tester, find.byKey(Key('offer-$q-$a')));
    }
    await tapIn(tester, find.byKey(const Key('offer-evaluate')));
    await reveal(tester, find.byKey(const Key('offer-result-red')));
    expect(find.byKey(const Key('offer-result-red')), findsOneWidget);
    expect(find.byKey(const Key('offer-flag-guaranteed')), findsOneWidget);
    expect(find.byKey(const Key('offer-flag-pressure')), findsNothing);
    final history = await env.container.read(offerChecksProvider.future);
    expect(history.single.verdict, OfferVerdict.red);
  });

  testWidgets(
    'taklif detektori: «bilmayman» bayrogʻi qaysi savol ekanini aytadi',
    (
      tester,
    ) async {
      // Qurilmada topildi: bir nechta «bilmayman» bir xil qator bo'lib
      // takrorlanardi — foydalanuvchi nimani aniqlashtirishni bilmasdi.
      final env = await pumpBarakaApp(tester);
      final l10n = lookupAppLocalizations(const Locale('uz'));
      await open(tester, env, AppRoutes.offerCheck);
      await tester.enterText(find.byKey(const Key('offer-title')), 'Tez Foyda');
      for (final (q, a) in [
        ('guaranteed', 'no'),
        ('lossShared', 'yes'),
        ('realGoods', 'yes'),
        ('recruitment', 'no'),
        ('pressure', 'no'),
        ('writtenContract', 'yes'),
        ('exitEasy', 'unknown'),
        ('license', 'unknown'),
        ('verifiedInPerson', 'yes'),
      ]) {
        await tapIn(tester, find.byKey(Key('offer-$q-$a')));
      }
      await tapIn(tester, find.byKey(const Key('offer-evaluate')));
      for (final q in [l10n.offerQExit, l10n.offerQLicense]) {
        final f = find.text(l10n.offerFlagUnknown(q));
        await reveal(tester, f);
        expect(f, findsOneWidget);
      }
    },
  );

  testWidgets('kassa daftari: yozuv → davrni yopish → ulush uy daromadiga', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final p = await seedActive(env);
    await open(tester, env, AppRoutes.partnershipLedger(p.meta.id));
    expect(find.byKey(const Key('ledger-read-only')), findsNothing);

    await tester.tap(find.byKey(const Key('ledger-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('ledger-title')), 'Buyurtma');
    await tester.pump();
    await tester.tap(find.byKey(const Key('ledger-entry-ok')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['5', '000', '000']);
    expect(
      tester.widget<Text>(find.byKey(const Key('ledger-net'))).data,
      contains('5'),
    );

    await tapIn(tester, find.byKey(const Key('ledger-close')));
    await tester.tap(find.byKey(const Key('ledger-close-ok')));
    await tester.pumpAndSettle();
    final v = (await env.container.read(
      ledgerViewProvider(p.meta.id).future,
    ))!;
    expect(v.closed.single.shares.map((s) => s.amount), [
      som(2000000),
      som(3000000),
    ]);
    // Mening ulushim uy daromadiga «tavakkal» bo'lib tushdi.
    final repo = await env.container.read(incomeRepositoryProvider.future);
    final income = (await repo.listActive(p.meta.householdId)).single;
    expect(income.amount, som(3000000));
    expect(income.sourceType, IncomeSourceType.tavakkal);
    await reveal(
      tester,
      find.byKey(Key('ledger-period-${v.closed.single.period.meta.id}')),
    );
    expect(
      find.byKey(Key('ledger-report-${v.closed.single.period.meta.id}')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('ledger-close')), findsNothing);
  });

  testWidgets('hunardan ishga: CAPEX 8 mln → 4 oyda, shartnoma qoralamasi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await env.container.read(membersProvider.future);
    await open(tester, env, AppRoutes.ideaNew);
    await tester.enterText(find.byKey(const Key('idea-title')), 'Tikuv sexi');
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('capex-add')));
    await tester.enterText(find.byKey(const Key('capex-title')), 'Overlok');
    await tester.tap(find.byKey(const Key('capex-ok')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['8', '000', '000']);
    await tapIn(tester, find.byKey(const Key('idea-income')));
    await typeAmount(tester, ['6', '000', '000']);
    await tapIn(tester, find.byKey(const Key('idea-expense')));
    await typeAmount(tester, ['4', '000', '000']);
    await reveal(tester, find.byKey(const Key('idea-payback-base')));
    expect(
      tester.widget<Text>(find.byKey(const Key('idea-payback-base'))).data,
      'Qoplanadi: 4 oyda',
    );
    expect(
      tester
          .widget<Text>(find.byKey(const Key('idea-payback-pessimistic')))
          .data,
      'Qoplanadi: 40 oyda',
    );
    await tapIn(tester, find.byKey(const Key('idea-save')));

    final ideas = (await env.container.read(ideasOverviewProvider.future)).$2;
    expect(ideas.single.capexTotal, som(8000000));
    await open(tester, env, AppRoutes.ideas);
    await tapIn(
      tester,
      find.byKey(Key('idea-contract-${ideas.single.idea.meta.id}')),
    );
    expect(find.text('Tikuv sexi'), findsWidgets, reason: 'nomi toʻldirildi');
    expect(find.text('1 / 6 · Tur'), findsOneWidget);
  });

  testWidgets('kassa daftari — FLAG_SECURE (parametrli marshrut)', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final p = await seedActive(env);
    final router = env.container.read(appRouterProvider)..go(AppRoutes.content);
    await tester.pumpAndSettle();
    clearInteractions(env.api);
    router.go(AppRoutes.partnershipLedger(p.meta.id));
    await tester.pumpAndSettle();
    verify(() => env.api.setSecureFlag(enabled: true)).called(1);
  });
}
