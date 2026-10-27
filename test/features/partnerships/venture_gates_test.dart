import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/drift_agreement_repositories.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_partnership_repositories.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_venture_repositories.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/agreements.dart';
import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

/// Sheriklik kassa daftari va kelishuv (jurnal, ko'rik, nizo) bog'langan
/// holda: taqsimot gate'lari (2F.5, 2F.7, 2F.8) shu yerda sinaladi.
void main() {
  late TestDb t;
  late PartnershipService partnerships;
  late VentureLedgerService ledger;
  late AgreementService agreements;
  late AccountabilityService acc;

  LocalDate today() => Tashkent.dateOf(t.clock.nowUtc());

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
    final incomes = DriftIncomeRepository(t.db, t.clock);
    agreements = AgreementService(
      households: hh,
      agreements: DriftAgreementRepository(t.db, t.clock),
      versions: DriftAgreementVersionRepository(t.db, t.clock),
      journal: DriftJournalRepository(t.db, t.meta),
      signers: DriftLoanSignerRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    acc = AccountabilityService(
      agreements: agreements,
      repo: DriftAgreementRepository(t.db, t.clock),
      journal: DriftJournalRepository(t.db, t.meta),
      clock: t.clock,
    );
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
      agreements: agreements,
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
      agreements: agreements,
    );
    await households.members(ownerName: 'Men');
  });

  /// Mudaraba: Gʻayrat — uskuna (sarmoya), Dilnoza — mehnat (men).
  Future<Partnership> active() async {
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
    // 9/9 savol javoblari — imzolashdan oldin (Vazifa 9A).
    await completeAgreement(agreements, AgreementSource.partnership, p.meta.id);
    for (final s in (await partnerships.view(p)).signers) {
      await partnerships.sign(p, s, s.name, [1]);
    }
    final owner =
        (await DriftMemberRepository(
          t.db,
          t.clock,
        ).listActive(await t.householdId())).firstWhere(
          (m) => m.role == MemberRole.adult,
        );
    await partnerships.acknowledgeNotDebt(p);
    await partnerships.consent(p, owner, '');
    return partnerships.activate(p);
  }

  Future<Agreement> bound(Partnership p) async {
    final a = await agreements.bySource(AgreementSource.partnership, p.meta.id);
    expect(a, isNotNull, reason: 'sheriklik shartnomasi kelishuvga bogʻlangan');
    return a!;
  }

  Future<List<String>> partnerIds(Partnership p) async => [
    for (final x in (await partnerships.view(p)).partners) x.meta.id,
  ];

  test('nizo ochiq boʻlsa taqsimot bloklanadi, hakam qarori ochadi', () async {
    final p = await active();
    await ledger.addEntry(
      p,
      kind: VentureEntryKind.income,
      title: 'Buyurtma',
      amount: som(1000000),
    );
    final a = await bound(p);
    final ids = await partnerIds(p);
    final id = await acc.openDispute(
      a,
      partyId: ids.first,
      topic: 'Foyda ulushi',
      clause: '4-band',
      claim: 'Ulush qayta hisoblansin',
    );
    expect(
      (await agreements.view(a)).agreement.status,
      AgreementStatus.inDispute,
    );
    await expectLater(
      ledger.closePeriod(p),
      rule(AccountabilityErrors.inDispute),
    );

    await acc.decideDispute(a, disputeId: id, decision: 'Ulush oʻzgarmaydi');
    final closed = await ledger.closePeriod(p);
    expect(closed.period.net, som(1000000));
  });

  test(
    "ochiq ko'rik davrni yopishga ruxsat bermaydi; yozuv qulflanadi",
    () async {
      final p = await active();
      await ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: 'Buyurtma',
        amount: som(500000),
      );
      final a = await bound(p);
      final reviewId = await acc.openReview(a);
      await expectLater(
        ledger.closePeriod(p),
        rule(AccountabilityErrors.reviewOpen),
      );

      for (final id in await partnerIds(p)) {
        await acc.acknowledge(
          a,
          reviewId: reviewId,
          partyId: id,
          verdict: ReviewVerdict.agree,
        );
      }
      await acc.completeReview(a, reviewId: reviewId);

      // Bayonnomadan keyin bugungi kassa yozuvi qo'shilmaydi.
      await expectLater(
        ledger.addEntry(
          p,
          kind: VentureEntryKind.income,
          title: 'Qoʻshimcha',
          amount: som(100000),
        ),
        rule(AccountabilityErrors.reviewLocked),
      );
      // Yakunlangan ko'rikdan keyin davrni yopish — odatiy oqim.
      final closed = await ledger.closePeriod(p);
      expect(closed.period.net, som(500000));
    },
  );

  test(
    'katta foyda: ikkala tomon tasdiqlamaguncha taqsimot oʻtmaydi',
    () async {
      final p = await active();
      final base = today().plusDays(-10);
      // Oxirgi 3 davr: 100 000, 120 000, 110 000 soʻm (o'rtacha 110 000).
      for (final (i, amount) in [100000, 120000, 110000].indexed) {
        await ledger.addEntry(
          p,
          kind: VentureEntryKind.income,
          title: 'Savdo ${i + 1}',
          amount: som(amount),
          date: base.plusDays(i),
        );
        await ledger.closePeriod(p, endDate: base.plusDays(i));
      }
      // 220 000 — o'rtachadan 200 % (B sharti); oldingi davrlar tasdiqsiz.
      await ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: 'Katta buyurtma',
        amount: som(220000),
        date: base.plusDays(3),
      );
      final end = base.plusDays(3);
      final check = await ledger.spikeCheck(p, endDate: end);
      expect(check.alert, isTrue);
      expect(check.blocks, isTrue);
      await expectLater(
        ledger.closePeriod(p, endDate: end),
        rule(AccountabilityErrors.spikeAckRequired),
      );

      final a = await bound(p);
      final ids = await partnerIds(p);
      await acc.acknowledgeSpike(a, partyId: ids[0], key: check.key);
      await expectLater(
        ledger.closePeriod(p, endDate: end),
        rule(AccountabilityErrors.spikeAckRequired),
        reason: 'bitta tomon yetarli emas',
      );
      await expectLater(
        acc.acknowledgeSpike(a, partyId: ids[0], key: check.key),
        rule(AccountabilityErrors.alreadyAcked),
      );
      await acc.acknowledgeSpike(a, partyId: ids[1], key: check.key);

      final closed = await ledger.closePeriod(p, endDate: end);
      expect(closed.period.net, som(220000));
    },
  );

  test(
    'foyda oʻzgarsa tasdiq eskirgan hisoblanadi (kalit foyda bilan)',
    () async {
      final p = await active();
      final base = today().plusDays(-10);
      for (final (i, amount) in [100000, 120000, 110000].indexed) {
        await ledger.addEntry(
          p,
          kind: VentureEntryKind.income,
          title: 'Savdo ${i + 1}',
          amount: som(amount),
          date: base.plusDays(i),
        );
        await ledger.closePeriod(p, endDate: base.plusDays(i));
      }
      final end = base.plusDays(3);
      await ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: 'Katta buyurtma',
        amount: som(220000),
        date: end,
      );
      final first = await ledger.spikeCheck(p, endDate: end);
      final a = await bound(p);
      for (final id in await partnerIds(p)) {
        await acc.acknowledgeSpike(a, partyId: id, key: first.key);
      }
      expect((await ledger.spikeCheck(p, endDate: end)).blocks, isFalse);

      await ledger.addEntry(
        p,
        kind: VentureEntryKind.income,
        title: 'Yana bitta buyurtma',
        amount: som(30000),
        date: end,
      );
      final second = await ledger.spikeCheck(p, endDate: end);
      expect(second.key, isNot(first.key));
      expect(second.blocks, isTrue, reason: 'yangi foyda — yangi tasdiq');
    },
  );
}
