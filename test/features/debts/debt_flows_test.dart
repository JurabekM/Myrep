import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/presentation/signature_pad.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

const nbsp = ' ';
String n(String s) => s.replaceAll(' ', nbsp);
Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> open(WidgetTester tester, TestEnv env, String route) async {
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

Future<void> typeAmount(WidgetTester tester, List<String> keys) async {
  for (final k in keys) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
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

Future<void> passFriction(WidgetTester tester) async {
  await tester.tap(find.byKey(const Key('check-need')));
  await tester.pump();
  expect(
    tester.widget<FilledButton>(find.byKey(const Key('check-next'))).onPressed,
    isNull,
    reason: 'ikkala savolga javob kerak',
  );
  await tester.tap(find.byKey(const Key('alt-relative')));
  await tester.pump();
  await tester.tap(find.byKey(const Key('check-next')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('qarzi hasana: «toʻxta va oʻyla» → reja (standart) → saqlash', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.debts);
    expect(find.text('Qarz yoʻq. Alhamdulillah!'), findsOneWidget);
    await tester.tap(find.byKey(const Key('debt-add')));
    await tester.pumpAndSettle();
    await passFriction(tester);

    await tester.enterText(find.byKey(const Key('debt-name')), 'Togʻam');
    await tester.pump();
    FilledButton save() =>
        tester.widget<FilledButton>(find.byKey(const Key('debt-save')));
    await reveal(tester, find.byKey(const Key('debt-save')));
    expect(save().onPressed, isNull, reason: 'summa va rejasiz — yoʻq');
    await tapIn(tester, find.byKey(const Key('debt-principal')));
    await typeAmount(tester, ['1', '5', '0', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    // Qoʻlda reja: standart bitta qator 30 kundan keyin, toʻliq summa.
    expect(find.byKey(const Key('manual-row-0')), findsOneWidget);
    expect(find.byKey(const Key('riba-warning')), findsNothing);
    await reveal(tester, find.byKey(const Key('cost-card')));
    expect(find.byKey(const Key('cost-card')), findsOneWidget);
    await reveal(tester, find.byKey(const Key('debt-save')));
    expect(save().onPressed, isNotNull);
    await tapIn(tester, find.byKey(const Key('debt-save')));

    final o = await env.container.read(debtOverviewProvider.future);
    final v = o.debts.single;
    expect(v.debt.creditorName, 'Togʻam');
    expect(v.debt.hasMarkup, isFalse);
    expect(v.plan.single.amount, som(1500000));
    expect(v.debt.borrowCheckJson, contains('relative'));
    await reveal(tester, find.textContaining('Togʻam'));
    expect(find.textContaining('Togʻam'), findsOneWidget);
  });

  testWidgets('qoʻlda reja summani qoplamasa — saqlab boʻlmaydi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.debtNew);
    await passFriction(tester);
    await tester.enterText(find.byKey(const Key('debt-name')), 'Doʻstim');
    await tapIn(tester, find.byKey(const Key('debt-principal')));
    await typeAmount(tester, ['2', '0', '0', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    // Yagona qatorni oʻchiramiz — reja boʻsh.
    await tester.tap(
      find.descendant(
        of: find.byKey(const Key('manual-row-0')),
        matching: find.byIcon(Icons.close),
      ),
    );
    await tester.pumpAndSettle();
    await reveal(tester, find.byKey(const Key('debt-save')));
    expect(
      tester.widget<FilledButton>(find.byKey(const Key('debt-save'))).onPressed,
      isNull,
    );
    expect(
      find.text('Toʻlash niyati — rejasiz qarzni saqlab boʻlmaydi.'),
      findsOneWidget,
    );
  });

  testWidgets('bank krediti: ribo ogohlantirishi va haqiqiy narx', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await open(tester, env, AppRoutes.debtNew);
    await passFriction(tester);
    await tester.tap(find.byKey(const Key('creditor-bank')));
    await tester.pump();
    await tester.enterText(find.byKey(const Key('debt-name')), 'Avtokredit');
    await tapIn(tester, find.byKey(const Key('debt-principal')));
    await typeAmount(tester, ['1', '0', '000', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('debt-term')), '12');
    await tester.enterText(find.byKey(const Key('debt-rate')), '24');
    await tester.pumpAndSettle();
    await reveal(tester, find.byKey(const Key('riba-warning')));
    expect(find.byKey(const Key('riba-warning')), findsOneWidget);
    await reveal(tester, find.byKey(const Key('cost-card')));
    expect(find.text(n('11 347 151,59 soʻm')), findsOneWidget);
    expect(find.text(n('1 347 151,59 soʻm')), findsOneWidget);
    await tapIn(tester, find.byKey(const Key('debt-save')));
    final v = (await env.container.read(
      debtOverviewProvider.future,
    )).debts.single;
    expect(v.isInterestBearing, isTrue);
    expect(v.plan, hasLength(12));
    expect(v.debt.annualRateBp, 2400);
  });

  testWidgets('qarz berdim (foizsiz) — bosh ekranda muddat eslatmasi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final debts = await env.container.read(debtServiceProvider.future);
    await debts.lend(
      debtorName: 'Qoʻshni',
      amount: som(200000),
      dueDate: LocalDate(2026, 10, 10),
    );
    env.container.invalidate(debtOverviewProvider);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('home-due')), findsOneWidget);
    expect(find.textContaining('Qoʻshni'), findsOneWidget);

    // UI: qarz berish dialogida foiz maydoni yoʻq.
    await open(tester, env, AppRoutes.debts);
    await tapIn(tester, find.byKey(const Key('debt-lend')));
    expect(find.text('Bergan qarzda foiz boʻlmaydi.'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget, reason: 'faqat ism');
  });

  testWidgets('qarz sahifasi — FLAG_SECURE (parametrli marshrut)', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final debts = await env.container.read(debtServiceProvider.future);
    final v = await debts.add(
      creditorType: CreditorType.friend,
      creditorName: 'Doʻstim',
      principal: som(500000),
      scheduleType: DebtScheduleType.manual,
      manual: [
        Installment(
          dueOn: LocalDate(2026, 11, 1),
          amount: som(500000),
          interest: const Money.zero(CurrencyCode.uzs),
        ),
      ],
    );
    final router = env.container.read(appRouterProvider)..go(AppRoutes.content);
    await tester.pumpAndSettle();
    clearInteractions(env.api);
    router.go(AppRoutes.debt(v.debt.meta.id));
    await tester.pumpAndSettle();
    verify(() => env.api.setSecureFlag(enabled: true)).called(1);
    expect(find.byKey(const Key('cost-card')), findsOneWidget);

    router.go(AppRoutes.content);
    await tester.pumpAndSettle();
    clearInteractions(env.api);
    router.go(AppRoutes.debtReceipt(v.debt.meta.id));
    await tester.pumpAndSettle();
    verify(() => env.api.setSecureFlag(enabled: true)).called(1);
    // Tomonlar avtomatik: qarz beruvchi va oluvchi.
    expect(find.text('Doʻstim'), findsWidgets);
    expect(find.text('Men'), findsOneWidget);
  });

  testWidgets('imzo: chizilmaguncha tugma oʻchiq, chizilgach yoqiladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    expect(env, isNotNull);
    final navigator = tester.state<NavigatorState>(find.byType(Navigator).last);
    unawaited(
      showSignDialog(navigator.context, role: 'Guvoh', name: 'Shoʼba'),
    );
    await tester.pumpAndSettle();
    FilledButton done() =>
        tester.widget<FilledButton>(find.byKey(const Key('sign-done')));
    expect(done().onPressed, isNull);
    final pad = find.byType(SignaturePad);
    await tester.drag(pad, const Offset(120, 40));
    await tester.pump();
    expect(done().onPressed, isNotNull);
    await tester.tap(find.byKey(const Key('sign-clear')));
    await tester.pump();
    expect(done().onPressed, isNull);
  });

  test('imzo PNG ga aylanadi', () async {
    final c = SignatureController()
      ..start(const Offset(10, 10))
      ..extend(const Offset(80, 40))
      ..extend(const Offset(140, 20));
    expect(c.isEmpty, isFalse);
    final png = await c.toPng(const Size(200, 80));
    expect(png.sublist(1, 4), 'PNG'.codeUnits);
  });
}
