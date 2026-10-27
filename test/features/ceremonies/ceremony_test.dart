import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/ceremonies/data/drift_ceremony_repositories.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony_math.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony_service.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

void main() {
  late TestDb t;
  late CeremonyService ceremonies;
  late HouseholdService households;
  late MemberPinService memberPins;
  late Member owner;
  late Member wife;

  setUp(() async {
    t = TestDb.open();
    final hh = DriftHouseholdRepository(t.db, t.clock);
    final members = DriftMemberRepository(t.db, t.clock);
    households = HouseholdService(
      households: hh,
      members: members,
      metaFactory: t.meta,
    );
    memberPins = MemberPinService(
      pins: PinService(
        store: InMemorySecureBlobStore(),
        hasher: ReferencePinHasher(),
        clock: t.clock,
        iterations: 1000,
      ),
      members: members,
    );
    final goals = DriftGoalRepository(t.db, t.clock);
    final debts = DebtService(
      households: hh,
      debts: DriftDebtRepository(t.db, t.clock),
      installments: DriftDebtInstallmentRepository(t.db, t.clock),
      payments: DriftDebtPaymentRepository(t.db, t.clock),
      receivables: DriftReceivableRepository(t.db, t.clock),
      goals: goals,
      contributors: DriftDebtContributorRepository(t.db, t.clock),
      sellables: DriftSellableItemRepository(t.db, t.clock),
      incomes: DriftIncomeRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    ceremonies = CeremonyService(
      households: hh,
      members: members,
      memberPins: memberPins,
      plans: DriftCeremonyPlanRepository(t.db, t.clock),
      scenarios: DriftCeremonyScenarioRepository(t.db, t.clock),
      lines: DriftCeremonyBudgetLineRepository(t.db, t.clock),
      marks: DriftCeremonyDiscussionMarkRepository(t.db, t.clock),
      goals: goals,
      contributions: DriftGoalContributionRepository(t.db, t.clock),
      debts: debts,
      metaFactory: t.meta,
      clock: t.clock,
    );
    owner = (await households.members(ownerName: 'Men')).single;
    wife = await households.addMember('Zuhra', MemberRole.adult);
  });

  /// O'g'ilning to'yi: 200 kishi × 150 000 osh (jamg'arma), xonanda
  /// 5 mln (oila), 10 mln sarpo (qarz).
  Future<(CeremonyPlan, CeremonyScenario)> wedding() async {
    final plan = await ceremonies.create(
      title: 'Oʻgʻlimning toʻyi',
      type: CeremonyType.toy,
      firstScenarioName: '3 kunlik, 200 kishi',
      guests: 200,
      eventDate: LocalDate(2027, 5, 15),
    );
    final s = (await ceremonies.view(plan)).scenarios.single.scenario;
    await ceremonies.addLine(
      s,
      title: 'Osh',
      kind: CeremonyLineKind.perGuest,
      amount: som(150000),
      source: FundingSource.savings,
    );
    await ceremonies.addLine(
      s,
      title: 'Xonanda',
      kind: CeremonyLineKind.oneTime,
      amount: som(5000000),
      source: FundingSource.family,
    );
    await ceremonies.addLine(
      s,
      title: 'Sarpo',
      kind: CeremonyLineKind.oneTime,
      amount: som(10000000),
      source: FundingSource.debt,
    );
    return (plan, s);
  }

  group('DEBT manbasi va oilaviy muhokama (SPEC 2D.8)', () {
    test('muhokamasiz CONFIRMED ga oʻtib boʻlmaydi', () async {
      final (plan, _) = await wedding();
      final v = await ceremonies.view(plan);
      expect(v.needsDiscussion, isTrue);
      expect(v.canConfirm, isFalse);
      await expectLater(
        ceremonies.confirm(plan),
        rule(CeremonyService.errDiscussionRequired),
      );
      expect(
        (await ceremonies.view(plan)).plan.status,
        CeremonyStatus.draft,
      );
    });

    test(
      'barcha kattalar belgi qoʻygach — DISCUSSED, keyin tasdiqlanadi',
      () async {
        final (plan, _) = await wedding();
        wife = await memberPins.setPin(wife, '482915');
        final (c1, done1) = await ceremonies.markDiscussed(plan, owner, '');
        expect(c1, isA<PinAccepted>());
        expect(done1, isFalse, reason: 'Zuhra hali belgilamagan');
        await expectLater(
          ceremonies.confirm(plan),
          rule(CeremonyService.errDiscussionRequired),
        );

        final (wrong, _) = await ceremonies.markDiscussed(plan, wife, '000000');
        expect(wrong, isA<PinRejected>());
        expect((await ceremonies.view(plan)).markedBy, {owner.meta.id});

        final (ok, done2) = await ceremonies.markDiscussed(
          plan,
          wife,
          '482915',
        );
        expect(ok, isA<PinAccepted>());
        expect(done2, isTrue);
        final v = await ceremonies.view(plan);
        expect(v.plan.status, CeremonyStatus.discussed);
        expect(v.canConfirm, isTrue);
        final confirmed = await ceremonies.confirm(plan);
        expect(confirmed.status, CeremonyStatus.confirmed);
      },
    );

    test('bola belgi qoʻya olmaydi', () async {
      final (plan, _) = await wedding();
      final son = await households.addMember('Ali', MemberRole.child);
      await expectLater(
        ceremonies.markDiscussed(plan, son, ''),
        rule(CeremonyService.errAdultOnly),
      );
    });

    test('muhokamadan keyin reja oʻzgarsa — muhokama qaytadan', () async {
      final (plan, s) = await wedding();
      await ceremonies.markDiscussed(plan, owner, '');
      await ceremonies.markDiscussed(plan, wife, '');
      expect(
        (await ceremonies.view(plan)).plan.status,
        CeremonyStatus.discussed,
      );
      await ceremonies.addLine(
        s,
        title: 'Mashina ijarasi',
        kind: CeremonyLineKind.oneTime,
        amount: som(2000000),
        source: FundingSource.debt,
      );
      final v = await ceremonies.view(plan);
      expect(v.plan.status, CeremonyStatus.draft);
      expect(v.markedBy, isEmpty);
      await expectLater(
        ceremonies.confirm(plan),
        rule(CeremonyService.errDiscussionRequired),
      );
    });

    test(
      'qarzsiz reja muhokamasiz tasdiqlanadi; tasdiqlangan oʻzgarmaydi',
      () async {
        final (plan, s) = await wedding();
        final sarpo = (await ceremonies.view(plan)).selected!.lines.firstWhere(
          (l) => l.source == FundingSource.debt,
        );
        await ceremonies.updateLine(sarpo, source: FundingSource.savings);
        final v = await ceremonies.view(plan);
        expect(v.needsDiscussion, isFalse);
        expect(
          (await ceremonies.confirm(plan)).status,
          CeremonyStatus.confirmed,
        );
        await expectLater(
          ceremonies.addLine(
            s,
            title: 'Qoʻshimcha',
            kind: CeremonyLineKind.oneTime,
            amount: som(1),
            source: FundingSource.debt,
          ),
          rule(CeremonyService.errConfirmedLocked),
        );
        await ceremonies.reopen(plan);
        expect(
          (await ceremonies.view(plan)).plan.status,
          CeremonyStatus.draft,
        );
      },
    );
  });

  group('stsenariylar taqqoslashi', () {
    test(
      'jami, manbalar va qarzning toʻlash muddati — Vazifa 11 simulyatori',
      () async {
        final (plan, big) = await wedding();
        await ceremonies.setDebtTerms(plan, monthly: som(1500000));
        final small = await ceremonies.addScenario(
          plan,
          name: '1 kunlik, 100 kishi, ixcham',
          guests: 100,
          copyFrom: big,
        );
        final sarpo = (await ceremonies.view(plan)).scenarios
            .firstWhere((x) => x.scenario.meta.id == small.meta.id)
            .lines
            .firstWhere((l) => l.title == 'Sarpo');
        await ceremonies.updateLine(sarpo, amount: som(3000000));

        final v = await ceremonies.view(plan);
        final a = v.scenarios[0];
        final b = v.scenarios[1];
        expect(a.total, som(45000000)); // 30 mln osh + 5 + 10
        expect(a.debt, som(10000000));
        expect(a.bySource[FundingSource.savings], som(30000000));
        expect(b.total, som(23000000)); // 15 mln osh + 5 + 3
        expect(b.debt, som(3000000));

        // Vazifa 11 simulyatori bilan bir xil natija.
        PayoffSchedule sim(Money debt) {
          const terms = PayoffTerms.annuity(
            annualRateBp: 0,
            annuityPayment: Money(150000000, uzs),
          );
          final rows = rowsFromBalance(
            balance: debt,
            firstDue: LocalDate(2027, 6, 15),
            terms: terms,
          );
          return planPayoff(
            [PayoffDebt(id: 'x', rows: rows, terms: terms)],
            monthlyExtra: som(0),
          ).debts.single.baseline;
        }

        expect(a.debtPayoff!.months, sim(som(10000000)).months);
        expect(a.debtPayoff!.months, 7);
        expect(a.debtPayoff!.endDate, sim(som(10000000)).endDate);
        expect(a.debtPayoff!.finalBalance, som(0));
        expect(b.debtPayoff!.months, 2);
        expect(a.debtOverpayment, som(0), reason: 'qarzi hasana');
      },
    );

    test(
      'foizli qarz: muddat va ortiqcha toʻlov simulyator bilan bir xil',
      () async {
        final (plan, _) = await wedding();
        await ceremonies.setDebtTerms(
          plan,
          monthly: som(1500000),
          annualRateBp: 2400,
        );
        final s = (await ceremonies.view(plan)).selected!;
        final expected = ceremonyDebtPayoff(
          debt: som(10000000),
          monthly: som(1500000),
          start: LocalDate(2027, 5, 15),
          annualRateBp: 2400,
        )!;
        expect(s.debtPayoff!.months, expected.months);
        expect(s.debtPayoff!.totalPaid, expected.totalPaid);
        expect(s.debtOverpayment.isPositive, isTrue);
        expect(s.debtPayoff!.finalBalance, som(0));
      },
    );

    test('oylik toʻlov foizni qoplamasa — qarz tugamaydi', () {
      expect(
        ceremonyDebtPayoff(
          debt: som(10000000),
          monthly: som(100000),
          start: LocalDate(2027, 1, 1),
          annualRateBp: 2400,
        ),
        isNull,
      );
    });

    test('muqobil maqsadlar: narx maqsadning necha foizi', () async {
      final (plan, _) = await wedding();
      final debts = DriftGoalRepository(t.db, t.clock);
      await debts.add(
        Goal(
          meta: t.meta.create(
            (await ceremonies.list()).single.meta.householdId,
          ),
          title: 'Kontrakt',
          target: som(15000000),
        ),
      );
      final s = (await ceremonies.view(plan)).selected!;
      expect(s.goalShares.single.$1.title, 'Kontrakt');
      expect(s.goalShares.single.$2, 30000, reason: '45 mln = 3 ta kontrakt');
    });

    test(
      '3 tadan koʻp stsenariy yoʻq, oxirgisini oʻchirib boʻlmaydi',
      () async {
        final (plan, s) = await wedding();
        await ceremonies.addScenario(plan, name: 'B');
        await ceremonies.addScenario(plan, name: 'C');
        await expectLater(
          ceremonies.addScenario(plan, name: 'D'),
          rule(CeremonyService.errScenarioLimit),
        );
        final v = await ceremonies.view(plan);
        for (final x in v.scenarios.skip(1)) {
          await ceremonies.removeScenario(x.scenario);
        }
        await expectLater(
          ceremonies.removeScenario(s),
          rule(CeremonyService.errLastScenario),
        );
      },
    );
  });

  test('toʻyona oʻrniga jamgʻarma: mehmonlar hissasi', () async {
    final (plan, _) = await wedding();
    final goal = await ceremonies.createGiftGoal(
      plan,
      title: 'Yosh oilaga uy',
      target: som(50000000),
    );
    await ceremonies.addContribution(
      goal,
      name: 'Amakim',
      amount: som(1000000),
    );
    await ceremonies.addContribution(goal, name: 'Xolam', amount: som(500000));
    final v = await ceremonies.view(plan);
    expect(v.giftGoal!.title, 'Yosh oilaga uy');
    expect(v.giftCollected, som(1500000));
    expect(v.giftContributions, hasLength(2));
    expect(
      v.selected!.goalShares,
      isEmpty,
      reason: 'toʻyona maqsadi muqobil sifatida koʻrsatilmaydi',
    );
  });
}
