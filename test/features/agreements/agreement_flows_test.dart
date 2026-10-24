import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/agreements.dart';
import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> reveal(WidgetTester tester, Finder f) async {
  final scrollable = find.byType(Scrollable).first;
  if (f.evaluate().isEmpty) {
    // Ro'yxat boshidan pastga qidiriladi: pastda qolgan maydon (masalan,
    // 8-savol) ko'rinmaydigan bo'lib qolmasin.
    await top(tester);
    await tester.scrollUntilVisible(f, 200, scrollable: scrollable);
  }
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

/// Ro'yxat boshiga (to'liqlik «N / 9» shu yerda).
Future<void> top(WidgetTester tester) async {
  await tester.drag(find.byType(Scrollable).first, const Offset(0, 3000));
  await tester.pumpAndSettle();
}

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('ijara: yaratish → savollar → 9/9 → imzolashga oʻtish', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final router = env.container.read(appRouterProvider)
      ..go(AppRoutes.agreements);
    await tester.pumpAndSettle();
    expect(find.text('Kelishuvlar'), findsWidgets);

    await tester.tap(find.byKey(const Key('ag-new')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('ag-new-rent')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('ag-new-title')),
      'Doʻkon ijarasi',
    );
    await tester.enterText(find.byKey(const Key('ag-new-me')), 'Akmal');
    await tester.enterText(find.byKey(const Key('ag-new-other')), 'Bahodir');
    await tester.pump();
    await tester.tap(find.byKey(const Key('ag-new-ok')));
    await tester.pumpAndSettle();

    expect(find.text('2 / 9 savolga javob berildi'), findsOneWidget);
    await reveal(tester, find.byKey(const Key('ag-sign-locked')));
    expect(find.byKey(const Key('ag-sign-locked')), findsOneWidget);

    // 8-savol: hakam — tomonlardan biri bo'lsa xato ko'rsatiladi.
    await tapIn(tester, find.byKey(const Key('ag-q-8')));
    await tester.enterText(find.byKey(const Key('ag-arbiter-name')), 'Bahodir');
    await tester.pump();
    await tester.tap(find.byKey(const Key('ag-q-save')));
    await tester.pumpAndSettle();
    await reveal(
      tester,
      find.textContaining('Hakam tomonlardan biri boʻla olmaydi'),
    );
    expect(
      find.textContaining('Hakam tomonlardan biri boʻla olmaydi'),
      findsWidgets,
    );
    await tapIn(tester, find.byKey(const Key('ag-q-8')));
    await tester.enterText(
      find.byKey(const Key('ag-arbiter-name')),
      'Mahalla raisi',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('ag-q-save')));
    await tester.pumpAndSettle();
    await top(tester);
    expect(find.text('3 / 9 savolga javob berildi'), findsOneWidget);

    // 5-savol: «tegishli emas» — izohsiz saqlab bo'lmaydi.
    await tapIn(tester, find.byKey(const Key('ag-q-5')));
    await tester.tap(find.byKey(const Key('ag-q-na')));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextButton>(find.byKey(const Key('ag-q-save'))).onPressed,
      isNull,
    );
    await tester.enterText(
      find.byKey(const Key('ag-q-reason')),
      'Ijarada zarar boʻlishilmaydi',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('ag-q-save')));
    await tester.pumpAndSettle();
    await top(tester);
    expect(find.text('4 / 9 savolga javob berildi'), findsOneWidget);

    // Qolganlari servis orqali (har bir muharrir alohida sinalgan).
    final s = await env.container.read(agreementServiceProvider.future);
    final a = (await s.list()).single;
    final v = await s.view(a);
    await s.saveAnswers(
      a,
      v.answers.copyWith(
        contributions: [
          AgreementContribution(
            partyId: 'p1',
            kind: ContributionKind.money,
            amount: som(2000000),
          ),
          const AgreementContribution(
            partyId: 'p2',
            kind: ContributionKind.goods,
            description: 'Bino',
          ),
        ],
        duties: const [
          AgreementDuty(
            id: 'd1',
            title: 'Haqni 5-sanagacha toʻlash',
            ownerPartyId: 'p1',
            breachClause: '3 kun ichida xabar beradi',
          ),
        ],
        profit: const ProfitRule(text: 'Oyiga 2 mln soʻm'),
        custody: const CustodyRule(where: 'Naqd', keeperPartyId: 'p1'),
        exit: const ExitClause(valuation: 'Qolgan oy', payout: '10 kun'),
      ),
    );
    env.container.invalidate(agreementViewProvider(a.meta.id));
    router.go(AppRoutes.agreements);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(Key('ag-item-${a.meta.id}')));
    await tester.pumpAndSettle();
    expect(find.text('9 / 9 savolga javob berildi'), findsOneWidget);

    await tapIn(tester, find.byKey(const Key('ag-prepare-sign')));
    expect(find.text('Mahalla raisi'), findsWidgets);
    expect(find.text('Hakam'), findsOneWidget);
  });

  testWidgets('ogʻzaki kelishuv ustasi → jurnalda boshlangʻich holat', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    env.container.read(appRouterProvider).go(AppRoutes.agreements);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('ag-new')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('ag-new-oral')));
    await tester.pumpAndSettle();

    await reveal(tester, find.byKey(const Key('oral-save')));
    expect(
      tester.widget<FilledButton>(find.byKey(const Key('oral-save'))).onPressed,
      isNull,
    );
    await tester.drag(find.byType(Scrollable).first, const Offset(0, 2000));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('oral-title')),
      'Yetkazib berish',
    );
    await tester.enterText(find.byKey(const Key('oral-me')), 'Akmal');
    await tester.enterText(find.byKey(const Key('oral-other')), 'Jasur');
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('oral-from')));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await reveal(tester, find.byKey(const Key('oral-note')));
    await tester.enterText(
      find.byKey(const Key('oral-note')),
      '3 oyda 2 marta foyda boʻlingan',
    );
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('oral-save')));

    expect(find.text('Kelishuv'), findsOneWidget);
    expect(find.text('ogʻzakidan yozilgan'), findsOneWidget);
    final s = await env.container.read(agreementServiceProvider.future);
    final v = await s.view((await s.list()).single);
    expect(v.agreement.oral, isTrue);
    expect(v.journal.single.kind, JournalKind.openingBalance);
    expect(v.journal.single.note, '3 oyda 2 marta foyda boʻlingan');
  });

  testWidgets('tilxat: kelishuv kartasi, 9/9 siz imzo rad etiladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final debts = await env.container.read(debtServiceProvider.future);
    final d = await debts.add(
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
    unawaited(
      env.container
          .read(appRouterProvider)
          .push<void>(AppRoutes.debtReceipt(d.debt.meta.id)),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('ag-link-card')), findsOneWidget);
    expect(find.text('6 / 9 savolga javob berildi'), findsOneWidget);

    // Imzolash 9/9 dan keyin: hakam imzolovchilar ro'yxatiga qo'shiladi.
    await completeAgreementIn(
      env.container,
      AgreementSource.debt,
      d.debt.meta.id,
    );
    final s = await env.container.read(agreementServiceProvider.future);
    final a = (await s.bySource(AgreementSource.debt, d.debt.meta.id))!;
    final v = await s.prepareSigning(a);
    expect(v.signers.map((x) => x.role), [
      SignerRole.lender,
      SignerRole.borrower,
      SignerRole.arbiter,
    ]);
    for (final x in v.signers) {
      await s.sign(a, x, x.name, [1]);
    }
    expect((await s.find(a.meta.id))!.status, AgreementStatus.signed);
    // Qarz to'lovi tilxat jurnaliga tushadi.
    await debts.pay(d.debt, som(100000));
    final after = await s.view(a);
    expect(after.journal.last.kind, JournalKind.loanPayment);
    expect(after.brokenAt, isNull);
  });
}
