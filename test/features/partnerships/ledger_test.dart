import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_partnership_repositories.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_venture_repositories.dart';
import 'package:baraka_daftari/features/partnerships/domain/idea_math.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
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
  late PartnershipService partnerships;
  late VentureLedgerService ledger;
  late IdeaService ideas;
  late OfferCheckService offers;
  late DriftIncomeRepository incomes;
  late Member owner;

  setUp(() async {
    t = TestDb.open();
    final hh = DriftHouseholdRepository(t.db, t.clock);
    final members = DriftMemberRepository(t.db, t.clock);
    final households = HouseholdService(
      households: hh,
      members: members,
      metaFactory: t.meta,
    );
    final repo = DriftPartnershipRepository(t.db, t.clock);
    final buyouts = DriftBuyoutPaymentRepository(t.db, t.clock);
    incomes = DriftIncomeRepository(t.db, t.clock);
    partnerships = PartnershipService(
      households: hh,
      members: members,
      memberPins: MemberPinService(
        pins: PinService(
          store: InMemorySecureBlobStore(),
          hasher: ReferencePinHasher(),
          clock: t.clock,
          iterations: 1000,
        ),
        members: members,
      ),
      partnerships: repo,
      partners: DriftPartnerRepository(t.db, t.clock),
      capital: DriftCapitalContributionRepository(t.db, t.clock),
      contracts: DriftPartnershipContractRepository(t.db, t.clock),
      signers: DriftLoanSignerRepository(t.db, t.clock),
      buyouts: buyouts,
      consents: DriftPartnershipConsentRepository(t.db, t.clock),
      gate: () async => GateState(
        reserve: ReserveStatus(balance: som(0)),
        debtReady: true,
        bypassed: false,
      ),
      metaFactory: t.meta,
      clock: t.clock,
    );
    ledger = VentureLedgerService(
      partnerships: partnerships,
      partnershipRepo: repo,
      entries: DriftVentureEntryRepository(t.db, t.clock),
      periods: DriftVenturePeriodRepository(t.db, t.clock),
      shares: DriftDistributionShareRepository(t.db, t.clock),
      buyouts: buyouts,
      incomes: incomes,
      metaFactory: t.meta,
      clock: t.clock,
    );
    ideas = IdeaService(
      households: hh,
      skills: DriftSkillRepository(t.db, t.clock),
      ideas: DriftVentureIdeaRepository(t.db, t.clock),
      capex: DriftIdeaCapexItemRepository(t.db, t.clock),
      metaFactory: t.meta,
    );
    offers = OfferCheckService(
      households: hh,
      checks: DriftOfferCheckRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    owner = (await households.members(ownerName: 'Men')).single;
  });

  /// Mudaraba: Gʻayrat — 30 mln uskuna (40 %), men — mehnat (60 %).
  Future<Partnership> active({bool meWorker = true}) async {
    final p = await partnerships.create(
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
          isMe: !meWorker,
        ),
        PartnerDraft(
          name: 'Dilnoza',
          role: PartnerRole.worker,
          profit: const ProfitShareInput.percent(6000),
          isMe: meWorker,
        ),
      ],
      termMonths: 12,
      reportPeriod: ReportPeriod.monthly,
      endTerms: 'a',
      disputeTerms: 'b',
    );
    for (final s in (await partnerships.view(p)).signers) {
      await partnerships.sign(p, s, s.name, [1]);
    }
    if (meWorker) {
      await partnerships.acknowledgeNotDebt(p);
      await partnerships.consent(p, owner, '');
      return partnerships.activate(p);
    }
    return partnerships.activate(p, gateBypassConfirmed: true);
  }

  Future<List<Money>> householdIncomes() async => [
    for (final i in await incomes.listActive(owner.meta.householdId)) i.amount,
  ];

  test('faol boʻlmagan sheriklikda daftar yoʻq', () async {
    final p = await partnerships.create(
      title: 'X',
      type: PartnershipType.musharaka,
      partners: [
        PartnerDraft(
          name: 'A',
          role: PartnerRole.both,
          profit: const ProfitShareInput.percent(5000),
          capital: [
            CapitalItem(kind: CapitalKind.cash, title: 'P', amount: som(1)),
          ],
          isMe: true,
        ),
        PartnerDraft(
          name: 'B',
          role: PartnerRole.both,
          profit: const ProfitShareInput.percent(5000),
          capital: [
            CapitalItem(kind: CapitalKind.cash, title: 'P', amount: som(1)),
          ],
        ),
      ],
      termMonths: 1,
      reportPeriod: ReportPeriod.monthly,
      endTerms: 'a',
      disputeTerms: 'b',
    );
    await expectLater(
      ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: 'Buyurtma',
        amount: som(1),
      ),
      rule(VentureLedgerService.errNotActive),
    );
  });

  test(
    'davr: foyda taqsimlanadi, mening ulushim uy daromadiga (tavakkal)',
    () async {
      final p = await active();
      await ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: '20 ta koʻylak buyurtmasi',
        amount: som(8000000),
        receiptImage: [1, 2, 3],
      );
      await ledger.addEntry(
        p,
        kind: VentureEntryKind.expense,
        title: 'Mato va ip',
        amount: som(2000000),
      );
      await ledger.addEntry(
        p,
        kind: VentureEntryKind.expense,
        title: 'Yordamchiga ish haqi',
        amount: som(1000000),
      );
      final v = await ledger.view(p);
      expect(v.openIncome, som(8000000));
      expect(v.openExpense, som(3000000));
      expect(v.openNet, som(5000000));
      expect(
        v.entries.firstWhere((e) => e.title.startsWith('20 ta')).receiptImage,
        [1, 2, 3],
        reason: 'chek rasmi shifrlangan bazada',
      );
      expect(await householdIncomes(), isEmpty, reason: 'biznes puli alohida');

      final closed = await ledger.closePeriod(p);
      expect(closed.period.net, som(5000000));
      expect(closed.shares.map((s) => s.amount), [som(2000000), som(3000000)]);
      expect(await householdIncomes(), [som(3000000)]);
      final inc = (await incomes.listActive(owner.meta.householdId)).single;
      expect(inc.sourceType, IncomeSourceType.tavakkal);
      expect(closed.period.incomeId, inc.meta.id);
    },
  );

  test('yopilgan davr oʻzgarmaydi — tuzatish yangi yozuv bilan', () async {
    final p = await active();
    final e = await ledger.addEntry(
      p,
      kind: VentureEntryKind.income,
      title: 'Buyurtma',
      amount: som(1000000),
    );
    await ledger.closePeriod(p);
    final v = await ledger.view(p);
    expect(v.isLocked(e), isTrue);
    await expectLater(
      ledger.removeEntry(p, e),
      rule(VentureLedgerService.errPeriodClosed),
    );
    await expectLater(
      ledger.addEntry(
        p,
        kind: VentureEntryKind.expense,
        title: 'Esdan chiqqan xarajat',
        amount: som(100000),
        date: t.clock.nowUtc().let(Tashkent.dateOf),
      ),
      rule(VentureLedgerService.errPeriodClosed),
    );
    await expectLater(
      ledger.closePeriod(p),
      rule(VentureLedgerService.errNothingToClose),
    );
    // Ertasi kuni — tuzatish (manfiy) yangi davrda.
    t.clock.advance(const Duration(days: 1));
    final fix = await ledger.addEntry(
      p,
      kind: VentureEntryKind.correction,
      title: 'Oʻtgan davr xarajati',
      amount: som(-100000),
      note: '1-davrda yozilmagan mato',
    );
    expect(fix.effect, som(-100000));
    expect((await ledger.view(p)).openNet, som(-100000));
    await ledger.removeEntry(p, fix);
  });

  test('buyout bilan foyda: toʻlov ulushdan avtomatik ayiriladi', () async {
    final p = await active();
    await partnerships.setBuyout(p, som(1000000));
    await ledger.addEntry(
      p,
      kind: VentureEntryKind.income,
      title: 'Buyurtmalar',
      amount: som(5000000),
    );
    final closed = await ledger.closePeriod(p);
    expect(closed.period.buyout, som(1000000));
    // 40/60 → 2 + 1 mln va 3 − 1 mln.
    expect(closed.shares.map((s) => s.amount), [som(3000000), som(2000000)]);
    expect(await householdIncomes(), [som(2000000)]);
    final v = await partnerships.view(p);
    expect(v.buyoutRemaining, som(29000000));
    expect(v.buyoutPayments.single.amount, som(1000000));
  });

  test('mudaraba zarar: kapital egasida, uy daromadi yoʻq', () async {
    final p = await active();
    await ledger.addEntry(
      p,
      kind: VentureEntryKind.income,
      title: 'Buyurtma',
      amount: som(1000000),
    );
    await ledger.addEntry(
      p,
      kind: VentureEntryKind.forceMajeure,
      title: 'Omborni suv bosdi',
      amount: som(4000000),
      note: 'Rasm va qoʻshnilar guvohligi',
      receiptImage: [9],
    );
    final closed = await ledger.closePeriod(p);
    expect(closed.period.net, som(-3000000));
    expect(closed.shares.map((s) => s.amount), [som(-3000000), som(0)]);
    expect(await householdIncomes(), isEmpty);
  });

  test('mudarabada kapital egasi daftarni faqat koʻradi', () async {
    final p = await active(meWorker: false);
    expect((await ledger.view(p)).readOnly, isTrue);
    await expectLater(
      ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: 'X',
        amount: som(1),
      ),
      rule(VentureLedgerService.errReadOnly),
    );
  });

  test('«Hunardan ishga»: CAPEX 8 mln, uch stsenariy', () async {
    final skill = await ideas.addSkill('Tikuvchilik');
    final v = await ideas.addIdea(
      title: 'Uyda tikuv sexi',
      skillId: skill.meta.id,
      baseIncome: som(6000000),
      monthlyExpense: som(4000000),
      capex: [
        ('Overlok', som(4500000)),
        ('Bichish stoli', som(1500000)),
        ('2 oʻram mato', som(2000000)),
      ],
    );
    expect(v.capexTotal, som(8000000));
    expect(v.scenarios.map((s) => s.scenario), IdeaScenario.values);
    expect(v.scenarios.map((s) => s.paybackMonths), [40, 4, 3]);
    expect((await ideas.ideas()).single.idea.title, 'Uyda tikuv sexi');
    expect((await ideas.skills()).single.name, 'Tikuvchilik');
  });

  test('taklif tekshiruvi saqlanadi', () async {
    final (r, e) = await offers.save('Kripto signal guruhi', {
      OfferQuestion.guaranteed: OfferAnswer.yes,
      OfferQuestion.recruitment: OfferAnswer.yes,
    });
    expect(e.verdict, OfferVerdict.red);
    expect(r.verdict, OfferVerdict.red);
    expect((await offers.history()).single.title, 'Kripto signal guruhi');
  });
}

extension<T> on T {
  R let<R>(R Function(T) f) => f(this);
}
