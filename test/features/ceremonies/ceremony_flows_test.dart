import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/ceremonies/data/ceremony_providers.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

const nbsp = ' ';
String n(String s) => s.replaceAll(' ', nbsp);
Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> open(WidgetTester tester, TestEnv env, String route) async {
  env.container
    ..invalidate(ceremonyPlansProvider)
    ..invalidate(ceremonyViewProvider);
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

Future<void> reveal(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    200,
    scrollable: find.byType(Scrollable).first,
  );
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

/// To'y: 200 kishi, osh 150 000 kishi boshiga (jamg'arma) va 10 mln sarpo
/// (qarz); qarzni oyiga 1,5 mln.
Future<CeremonyPlan> seedWedding(TestEnv env) async {
  await env.container.read(membersProvider.future);
  final s = await env.container.read(ceremonyServiceProvider.future);
  final plan = await s.create(
    title: 'Oʻgʻlimning toʻyi',
    type: CeremonyType.toy,
    firstScenarioName: 'Asosiy',
    guests: 200,
    eventDate: LocalDate(2027, 5, 15),
  );
  final sc = (await s.view(plan)).scenarios.single.scenario;
  await s.addLine(
    sc,
    title: 'Osh',
    kind: CeremonyLineKind.perGuest,
    amount: som(150000),
    source: FundingSource.savings,
  );
  await s.addLine(
    sc,
    title: 'Sarpo',
    kind: CeremonyLineKind.oneTime,
    amount: som(10000000),
    source: FundingSource.debt,
  );
  await s.setDebtTerms(plan, monthly: som(1500000));
  return plan;
}

void main() {
  testWidgets('reja tuzish: qarzli qator → muhokamasiz tasdiqlab boʻlmaydi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await env.container.read(membersProvider.future);
    await open(tester, env, AppRoutes.ceremonies);
    expect(find.byKey(const Key('pressure-card')), findsOneWidget);
    await tester.tap(find.byKey(const Key('ceremony-add')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('ceremony-name')), 'Toʻy');
    await tester.pump();
    await tester.tap(find.byKey(const Key('ceremony-type-toy')));
    await tester.tap(find.byKey(const Key('ceremony-save')));
    await tester.pumpAndSettle();

    // Qarz bilan moliyalangan qator.
    await tapIn(tester, find.byKey(const Key('line-add')));
    await tester.enterText(find.byKey(const Key('line-title')), 'Sarpo');
    await tester.pump();
    await tester.tap(find.byKey(const Key('line-source-debt')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('line-save')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['1', '0', '000', '000']);

    await reveal(tester, find.byKey(const Key('ceremony-confirm')));
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('ceremony-confirm')))
          .onPressed,
      isNull,
      reason: 'qarz bor — muhokamasiz tasdiqlanmaydi',
    );
    expect(find.byKey(const Key('ceremony-confirm-blocked')), findsOneWidget);
    expect(find.byKey(const Key('discussion-card')), findsOneWidget);

    // Yagona katta a'zo (egasi) belgi qo'yadi → muhokama yakunlandi.
    final owner = (await env.container.read(membersProvider.future)).single;
    await tapIn(tester, find.byKey(Key('discuss-${owner.meta.id}')));
    await reveal(tester, find.byKey(const Key('ceremony-confirm')));
    expect(find.byKey(const Key('ceremony-confirm-blocked')), findsNothing);
    await tapIn(tester, find.byKey(const Key('ceremony-confirm')));

    final plan = (await env.container.read(
      ceremonyPlansProvider.future,
    )).single;
    expect(plan.status, CeremonyStatus.confirmed);
    await reveal(tester, find.byKey(const Key('ceremony-locked')));
    expect(find.byKey(const Key('ceremony-locked')), findsOneWidget);
    expect(find.byKey(const Key('line-add')), findsNothing);
  });

  testWidgets('stsenariy taqqoslash: toʻlash muddati simulyatordan', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final plan = await seedWedding(env);
    await open(tester, env, AppRoutes.ceremony(plan.meta.id));
    final v = (await env.container.read(
      ceremonyViewProvider(plan.meta.id).future,
    ))!;
    final id = v.scenarios.single.scenario.meta.id;
    expect(
      tester.widget<Text>(find.byKey(Key('scenario-total-$id'))).data,
      contains(n('40 000 000')),
    );
    expect(
      tester.widget<Text>(find.byKey(Key('scenario-payoff-$id'))).data,
      startsWith('Qarz 7 oyda uziladi'),
    );

    // Ixcham stsenariy (nusxa), 100 kishi.
    await tapIn(tester, find.byKey(const Key('scenario-add')));
    await tester.enterText(find.byKey(const Key('scenario-name')), 'Ixcham');
    await tester.tap(find.byKey(const Key('scenario-name-ok')));
    await tester.pumpAndSettle();
    final v2 = (await env.container.read(
      ceremonyViewProvider(plan.meta.id).future,
    ))!;
    expect(v2.scenarios, hasLength(2));
    final id2 = v2.scenarios[1].scenario.meta.id;
    await tapIn(tester, find.byKey(Key('scenario-guests-$id2')));
    await tester.enterText(find.byKey(const Key('guests-field')), '100');
    await tester.tap(find.byKey(const Key('guests-ok')));
    await tester.pumpAndSettle();
    await reveal(tester, find.byKey(Key('scenario-total-$id2')));
    expect(
      tester.widget<Text>(find.byKey(Key('scenario-total-$id2'))).data,
      contains(n('25 000 000')),
    );
  });

  testWidgets('toʻyona oʻrniga jamgʻarma: maqsad va mehmon hissasi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final plan = await seedWedding(env);
    await open(tester, env, AppRoutes.ceremony(plan.meta.id));
    await tapIn(tester, find.byKey(const Key('gift-create')));
    await tester.enterText(
      find.byKey(const Key('gift-name')),
      'Yosh oilaga uy',
    );
    await tester.tap(find.byKey(const Key('gift-name-ok')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['5', '0', '000', '000']);

    await tapIn(tester, find.byKey(const Key('gift-add')));
    await tester.enterText(find.byKey(const Key('gift-contributor')), 'Amakim');
    await tester.tap(find.byKey(const Key('gift-contributor-ok')));
    await tester.pumpAndSettle();
    await typeAmount(tester, ['1', '000', '000']);

    await reveal(tester, find.byKey(const Key('gift-progress')));
    expect(
      tester.widget<Text>(find.byKey(const Key('gift-progress'))).data,
      allOf(contains(n('1 000 000')), contains(n('50 000 000'))),
    );
    expect(find.text('Amakim'), findsOneWidget);
  });

  testWidgets('marosim sahifasi — FLAG_SECURE (parametrli marshrut)', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final plan = await seedWedding(env);
    final router = env.container.read(appRouterProvider)..go(AppRoutes.content);
    await tester.pumpAndSettle();
    clearInteractions(env.api);
    router.go(AppRoutes.ceremony(plan.meta.id));
    await tester.pumpAndSettle();
    verify(() => env.api.setSecureFlag(enabled: true)).called(1);
  });
}
