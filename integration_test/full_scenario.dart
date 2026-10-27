// Yakuniy E2E ssenariy (MVP_PLAN Vazifa 15): Akmal — taksichi, kunlik naqd
// daromad, rafiqasi Zuhra; avtokredit 39 mln (14 oy, 24 %).
//
// Ilovaning haqiqiy Riverpod provayderlari va servislari orqali boshidan
// oxirigacha: daromad → ulush → audit → havas chegarasi → obuna bekor
// qilish → qutqarilgan pulni ko'chirish → qarz → 70/20/10 → payoff → qarz
// yopilishi → darvoza ochilishi → sheriklik shartnomasi → davr taqsimoti →
// shifrlangan zaxira nusxa va 1:1 tiklash.
//
// Bir xil kod ikki joyda ishlaydi:
// * `test/e2e/full_e2e_host_test.dart` — in-memory baza, soxta shifr;
// * `integration_test/full_e2e_test.dart` — qurilmada SQLCipher bazasi va
//   Kotlin `BackupCipher` (PBKDF2 + AES-256-GCM).
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/backup/data/backup_providers.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:baraka_daftari/features/subscriptions/data/subscription_providers.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:baraka_daftari/features/vault/domain/lump_sum.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../test/helpers/agreements.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

/// Ssenariy natijasi — tiklash tekshiruvi uchun.
typedef FullScenarioResult = ({Map<String, List<Map<String, Object?>>> dump});

/// [c] — ilova provayderlari (baza, soat, shifr almashtirilgan).
/// [log] — qadamlar (qurilmada logcat'ga chiqadi).
Future<FullScenarioResult> runFullScenario(
  ProviderContainer c, {
  required DateTime now,
  void Function(String step)? log,
}) async {
  void step(String s) => log?.call('E2E: $s');

  // 0. Onboarding: kunlik naqd, rafiqasi Zuhra.
  final households = await c.read(householdServiceProvider.future);
  await households.members(ownerName: 'Akmal');
  final zuhra = await households.addMember('Zuhra', MemberRole.adult);
  await households.completeOnboarding(
    incomeKind: IncomeKind.dailyCash,
    at: now,
  );
  final members = await households.members(ownerName: 'Akmal');
  final akmal = members.firstWhere((m) => m.isOwner);
  step('onboarding');

  // 1. Daromad → 2. ulush («Avval o'zingizga to'lang»).
  final incomes = await c.read(incomeServiceProvider.future);
  final vault = await c.read(vaultServiceProvider.future);
  final income = await incomes.add(
    amount: som(450000),
    source: IncomeSource.dailyWork,
    channel: PaymentChannel.cash,
  );
  final share = await vault.suggestShare(income);
  expect(share, isNotNull);
  expect(share!.isPositive, isTrue);
  await vault.allocateFromIncome(income, share);
  expect((await vault.overview()).balance, share);
  step('daromad 450 000, ulush $share');

  // Xarajatlar: oziq-ovqat (zarur) va choyxona (havas).
  final expenses = await c.read(expenseServiceProvider.future);
  final cats = {
    for (final cat in await expenses.categories())
      if (cat.systemKey != null) cat.systemKey!: cat,
  };
  await expenses.add(
    amount: som(120000),
    categoryId: cats[CategoryKey.groceries]!.meta.id,
    channel: PaymentChannel.cash,
  );
  await expenses.add(
    amount: som(60000),
    categoryId: cats[CategoryKey.cafe]!.meta.id,
    channel: PaymentChannel.cash,
  );

  // 3. Audit: davr yakuni hisobotga yoziladi.
  final ledger = await c.read(ledgerServiceProvider.future);
  final period = await ledger.currentPeriod();
  final report = await ledger.completeAudit(period);
  expect(report.income, som(450000));
  expect(report.expenses, som(180000));
  step('audit: daromad ${report.income}, xarajat ${report.expenses}');

  // 4. Havas chegarasi — ikki katta a'zo rozi.
  final havas = await c.read(havasServiceProvider.future);
  final limit = await havas.propose(som(300000), proposedBy: akmal.meta.id);
  expect((await havas.consent(limit, akmal, '')).$2, isFalse);
  expect((await havas.consent(limit, zuhra, '')).$2, isTrue);
  final ho = await havas.overview();
  expect(ho.active?.limit.amount, som(300000));
  step('havas chegarasi 300 000 kelishildi');

  // 5. Obuna bekor qilish → 6. qutqarilgan pulni «Kelajagim»ga.
  final subs = await c.read(subscriptionServiceProvider.future);
  final sub = await subs.add(title: 'Kino servisi', price: som(49000));
  await subs.cancel(sub);
  final rescue = await c.read(rescueServiceProvider.future);
  final before = (await vault.overview()).balance;
  final moved = await rescue.transferWeek();
  expect(moved.isPositive, isTrue);
  expect((await vault.overview()).balance, before + moved);
  step('obuna bekor, qutqarilgan $moved Kelajagimga');

  // 7. Qarz: avtokredit 39 mln, 14 oy, 24 % (annuitet).
  final debts = await c.read(debtServiceProvider.future);
  final start = Tashkent.dateOf(now);
  final car = await debts.add(
    start: start,
    creditorType: CreditorType.bank,
    creditorName: 'Avtokredit',
    principal: som(39000000),
    scheduleType: DebtScheduleType.annuity,
    termMonths: 14,
    annualRateBp: 2400,
  );
  expect(car.plan, hasLength(14));
  expect(car.plan.first.amount, const Money(322147684, CurrencyCode.uzs));
  final readiness = await c.read(debtReadinessProvider.future);
  expect(await readiness.isReady(), isFalse);
  step('qarz 39 mln qoʻshildi');

  // 8. «Qarzdan chiqish» rejimi: 70/20/10.
  final recovery = await c.read(recoveryServiceProvider.future);
  await recovery.enable();
  final rs = await recovery.state();
  expect(rs.mode, BudgetMode.debtRecovery);
  expect(rs.split, RecoverySplit.standard);
  expect(
    (rs.split.needsBp, rs.split.debtBp, rs.split.savingsBp),
    (7000, 2000, 1000),
  );
  step('70/20/10 yoqildi');

  // 9. Payoff: oyiga +2 mln (10 mln daromadning 20 %) — 14 oy o'rniga 9.
  final schedule = buildSchedule(
    type: DebtScheduleType.annuity,
    principal: som(39000000),
    start: start,
    termMonths: 14,
    annualRateBp: 2400,
  );
  final plan = planPayoff(
    [
      PayoffDebt(
        id: car.debt.meta.id,
        rows: schedule,
        terms: PayoffTerms.annuity(
          annualRateBp: 2400,
          annuityPayment: schedule.first.amount,
        ),
      ),
    ],
    monthlyExtra: som(2000000),
  );
  final d = plan.debts.single;
  expect(d.baseline.months, 14);
  expect(d.accelerated.months, 9);
  expect(d.saved, const Money(243234042, CurrencyCode.uzs));
  step('payoff: 9 oy, tejash ${d.saved}');

  // 10. Qarz yopilishi (sotilgan buyum + jamg'arilgan pul bilan).
  // Muddatidan oldin to'liq uzish: qolgan asosiy qarz + joriy oy foizi.
  final payoff = (await debts.view(car.debt)).payoffAmount;
  expect(payoff < car.debt.remaining, isTrue);
  final paid = await debts.pay(car.debt, payoff);
  expect(paid.closed, isTrue);
  expect((await debts.overview()).debts, isEmpty);
  expect(await readiness.isReady(), isTrue);
  step('qarz yopildi');

  // 11. Darvoza: qorovul pul 6 oylik zarur xarajat — to'lgach ochiladi.
  final essentials = await c.read(essentialSpendServiceProvider.future);
  await essentials.setEstimate(som(3000000));
  var gate = (await vault.overview()).gate;
  expect(gate.debtReady, isTrue);
  expect(gate.reserveReady, isFalse);
  final missing = (await vault.overview()).reserve.missing!;
  await vault.depositManual(missing);
  gate = (await vault.overview()).gate;
  expect(gate.reserve.isFull, isTrue);
  expect(gate.ready, isTrue);
  expect(gate.bypassed, isFalse);
  expect(ReserveStatus.fullMonths, 6);
  step('darvoza ochildi');

  // 12. Sheriklik shartnomasi: musharaka, Akmal va Bobur 20 mln dan, 50/50.
  final partnerships = await c.read(partnershipServiceProvider.future);
  final p = await partnerships.create(
    title: 'Ikkinchi mashina (taksi)',
    type: PartnershipType.musharaka,
    partners: [
      PartnerDraft(
        name: 'Akmal',
        role: PartnerRole.both,
        profit: const ProfitShareInput.percent(5000),
        capital: [
          CapitalItem(
            kind: CapitalKind.cash,
            title: 'Naqd',
            amount: som(20000000),
          ),
        ],
        isMe: true,
      ),
      PartnerDraft(
        name: 'Bobur',
        role: PartnerRole.both,
        profit: const ProfitShareInput.percent(5000),
        capital: [
          CapitalItem(
            kind: CapitalKind.cash,
            title: 'Naqd',
            amount: som(20000000),
          ),
        ],
      ),
    ],
    termMonths: 12,
    reportPeriod: ReportPeriod.monthly,
    endTerms: 'Muddat oxirida mashina sotilib, kapitalga mutanosib boʻlinadi.',
    disputeTerms: 'Avval oila oqsoqollari, keyin sud.',
  );
  // 6-qonun: 9 savolga javob — vazifalar, hisob, chiqish, hakam (9/9).
  await completeAgreement(
    await c.read(agreementServiceProvider.future),
    AgreementSource.partnership,
    p.meta.id,
  );
  for (final s in (await partnerships.view(p)).signers) {
    await partnerships.sign(p, s, s.name, [137, 80, 78, 71]);
  }
  final active = await partnerships.activate(p);
  expect(active.status, PartnershipStatus.active);
  expect((await vault.overview()).gate.bypassed, isFalse);
  step('sheriklik imzolandi va faollashdi (darvoza chetlab oʻtilmadi)');

  // 13. Davr taqsimoti: kirim 10 mln, xarajat 4 mln → foyda 6 mln, 50/50.
  final ventures = await c.read(ventureLedgerServiceProvider.future);
  await ventures.addEntry(
    active,
    kind: VentureEntryKind.income,
    title: 'Oylik yoʻl haqi',
    amount: som(10000000),
  );
  await ventures.addEntry(
    active,
    kind: VentureEntryKind.expense,
    title: 'Benzin va taʼmir',
    amount: som(4000000),
  );
  final closed = await ventures.closePeriod(active);
  expect(closed.shares.map((s) => s.amount).toSet(), {som(3000000)});
  final db = await c.read(appDatabaseProvider.future);
  final tavakkal = await (db.select(
    db.incomes,
  )..where((i) => i.sourceType.equalsValue(IncomeSourceType.tavakkal))).get();
  expect(tavakkal.single.amountMinor, som(3000000).minorUnits);
  step('davr yopildi: Akmal 3 mln uy daromadiga');

  // 6-qonun: shartnoma = 9/9 kelishuv, hisob jurnali butun (xesh-zanjir).
  final agreements = await c.read(agreementServiceProvider.future);
  final ag = await agreements.view(
    (await agreements.bySource(AgreementSource.partnership, p.meta.id))!,
  );
  expect(ag.completeness.complete, isTrue);
  expect(ag.agreement.status, AgreementStatus.active);
  expect(ag.brokenAt, isNull);
  expect(
    ag.journal.map((e) => e.kind).toSet(),
    containsAll({
      JournalKind.ventureIncome,
      JournalKind.ventureExpense,
      JournalKind.profitDistribution,
    }),
  );

  // 6-qonun (14A): «bajarilmadi» hodisasi va oylik ko'rik. Bobur muddatida
  // mashinani bera olmadi, Akmal roziman, Bobur e'tiroz bildirdi; bayonnoma
  // zanjir boshi bilan yoziladi va zanjir butun qoladi.
  final acc = await c.read(accountabilityServiceProvider.future);
  final agreement = (await agreements.bySource(
    AgreementSource.partnership,
    p.meta.id,
  ))!;
  final party = ag.answers.parties;
  await acc.reportDuty(
    agreement,
    dutyId: 'd1',
    partyId: party[1].id,
    reason: 'Mashina taʼmirda edi',
    fix: 'Keyingi kuni oʻrniga chiqaman',
  );
  final reviewId = await acc.openReview(agreement);
  await acc.acknowledge(
    agreement,
    reviewId: reviewId,
    partyId: party[0].id,
    verdict: ReviewVerdict.agree,
  );
  await acc.acknowledge(
    agreement,
    reviewId: reviewId,
    partyId: party[1].id,
    verdict: ReviewVerdict.object,
    objection: 'Benzin hisobida 50 000 soʻm farq bor',
  );
  final minutes = await acc.completeReview(agreement, reviewId: reviewId);
  final review = await acc.view(agreement);
  expect(review.minutes, hasLength(1));
  expect(review.review.isOpen, isFalse);
  expect(
    review.incidents,
    isEmpty,
    reason: 'hodisa bayonnomada hisobga olindi',
  );
  final journal = review.base.journal;
  expect(verifyChain(journal), isNull);
  expect(minutesIntact(journal, minutes), isTrue);
  expect(
    journal.map((e) => e.kind).toSet(),
    containsAll({
      JournalKind.dutyIncident,
      JournalKind.reviewOpened,
      JournalKind.reviewAck,
      JournalKind.accountReview,
    }),
  );
  step("oylik ko'rik bayonnoma bilan yakunlandi (zanjir butun)");

  // 7-qonun (14B): Bekzod «oyiga 35 %» taklifini besh belgi bilan
  // tekshiradi — qizil; maslahatsiz «pul qo'yaman» ochilmaydi, rad etadi.
  // Dollardagi jamg'arma: oilaviy zaxira allaqachon to'la — hammasi hunarga.
  final offers = await c.read(offerCheckServiceProvider.future);
  final (tezFoyda, verdict) = await offers.save(
    'Tez Foyda',
    {
      OfferQuestion.guaranteed: OfferAnswer.yes,
      OfferQuestion.lossShared: OfferAnswer.no,
      OfferQuestion.realGoods: OfferAnswer.unknown,
      OfferQuestion.recruitment: OfferAnswer.yes,
      OfferQuestion.pressure: OfferAnswer.yes,
      OfferQuestion.writtenContract: OfferAnswer.yes,
      OfferQuestion.exitEasy: OfferAnswer.unknown,
      OfferQuestion.license: OfferAnswer.unknown,
      OfferQuestion.verifiedInPerson: OfferAnswer.no,
    },
    amount: som(10000 * 12650),
    promisedMonthlyBp: 3500,
  );
  expect(verdict.verdict, OfferVerdict.red);
  expect(verdict.level, ScamLevel.flee);
  expect(verdict.signs, hasLength(4));
  await expectLater(
    offers.decide(tezFoyda, OfferDecision.accepted),
    throwsA(
      isA<DomainRuleException>().having(
        (e) => e.code,
        'code',
        OfferCheckService.errAdvisorRequired,
      ),
    ),
  );
  final declined = await offers.decide(
    tezFoyda,
    OfferDecision.declined,
    advisor: 'Shavkat aka',
  );
  expect(declined.decision, OfferDecision.declined);
  final wall = (await vault.overview()).reserve.missing!;
  final lump = splitLumpSum(som(18000 * 12650), wall);
  expect(lump.toReserve, som(0), reason: 'zaxira 11-qadamda toʻlgan');
  expect(lump.toInvest, som(18000 * 12650));
  step("Bekzod: taklif qizil (4 belgi), rad etildi; zaxira to'la — hunarga");

  // 14. Shifrlangan zaxira nusxa.
  final backup = await c.read(backupServiceProvider.future);
  final dump = await backup.dump();
  expect(dump['debts'], hasLength(1));
  expect(dump['partnerships'], hasLength(1));
  return (dump: dump);
}
