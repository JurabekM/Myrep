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
import 'package:baraka_daftari/features/partnerships/data/drift_partnership_repositories.dart';
import 'package:baraka_daftari/features/partnerships/domain/contract_template.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

CapitalItem cash(int major) =>
    CapitalItem(kind: CapitalKind.cash, title: 'Pul', amount: som(major));

CapitalItem tool(String title, int major) =>
    CapitalItem(kind: CapitalKind.equipment, title: title, amount: som(major));

PartnerDraft provider(
  String name,
  int bp, {
  bool me = false,
  List<CapitalItem>? capital,
}) => PartnerDraft(
  name: name,
  role: PartnerRole.capitalProvider,
  profit: ProfitShareInput.percent(bp),
  capital: capital ?? [cash(30000000)],
  isMe: me,
);

PartnerDraft worker(String name, int bp, {bool me = false}) => PartnerDraft(
  name: name,
  role: PartnerRole.worker,
  profit: ProfitShareInput.percent(bp),
  isMe: me,
);

GateState gateWith({required bool open}) => GateState(
  reserve: ReserveStatus(
    balance: som(open ? 6000000 : 0),
    monthlyEssential: som(1000000),
  ),
  debtReady: true,
  bypassed: false,
);

void main() {
  group('validatsiya qoidalari (SPEC 2E.1)', () {
    void ok(PartnershipType t, List<PartnerDraft> p) =>
        PartnershipRules.validate(t, p, uzs);
    void bad(PartnershipType t, List<PartnerDraft> p, String code) =>
        expect(() => PartnershipRules.validate(t, p, uzs), rule(code));

    test('foyda faqat sof foyda foizi; ulushlar yigʻindisi 100 %', () {
      ok(PartnershipType.mudaraba, [provider('A', 4000), worker('B', 6000)]);
      bad(
        PartnershipType.mudaraba,
        [provider('A', 4000), worker('B', 5000)],
        PartnershipRules.errSharesTotal,
      );
      bad(
        PartnershipType.mudaraba,
        [provider('A', 11000), worker('B', -1000)],
        PartnershipRules.errShareNegative,
      );
    });

    test('qatʼiy summa yoki kafolatli daromad — «bu sheriklik emas»', () {
      for (final profit in [
        ProfitShareInput.fixed(som(2000000)),
        const ProfitShareInput.guaranteed(4000),
      ]) {
        bad(
          PartnershipType.mudaraba,
          [
            PartnerDraft(
              name: 'Kapital egasi',
              role: PartnerRole.capitalProvider,
              profit: profit,
              capital: [cash(30000000)],
            ),
            worker('Usta', 6000),
          ],
          PartnershipRules.errNotPartnership,
        );
      }
    });

    test('mudaraba: kapital bir tomondan, mehnat boshqa tomondan', () {
      bad(
        PartnershipType.mudaraba,
        [provider('A', 5000), provider('B', 5000)],
        PartnershipRules.errMudarabaRoles,
      );
      bad(
        PartnershipType.mudaraba,
        [
          provider('A', 5000),
          PartnerDraft(
            name: 'B',
            role: PartnerRole.worker,
            profit: const ProfitShareInput.percent(5000),
            capital: [cash(1000000)],
          ),
        ],
        PartnershipRules.errMudarabaWorkerCapital,
      );
      bad(
        PartnershipType.mudaraba,
        [provider('A', 5000, capital: const []), worker('B', 5000)],
        PartnershipRules.errNoCapital,
      );
      bad(
        PartnershipType.mudaraba,
        [provider('A', 10000)],
        PartnershipRules.errMinPartners,
      );
    });

    test('musharaka: har bir sherik kapital kiritadi', () {
      ok(PartnershipType.musharaka, [
        provider('A', 5000, capital: [cash(20000000)]),
        PartnerDraft(
          name: 'B',
          role: PartnerRole.both,
          profit: const ProfitShareInput.percent(5000),
          capital: [tool('Tikuv mashinasi', 10000000)],
        ),
      ]);
      bad(
        PartnershipType.musharaka,
        [provider('A', 5000), worker('B', 5000)],
        PartnershipRules.errMusharakaCapital,
      );
    });
  });

  group('zarar taqsimoti', () {
    test('musharaka: kapitalga mutanosib (capital_i / Σcapital)', () {
      final shares = PartnershipRules.lossShares(
        type: PartnershipType.musharaka,
        roles: const [PartnerRole.both, PartnerRole.both],
        capital: [som(20000000), som(10000000)],
        loss: som(3000000),
      );
      expect(shares, [som(2000000), som(1000000)]);
    });

    test('mudaraba: zarar kapital egasida, ishchi mehnatidan ayriladi', () {
      final shares = PartnershipRules.lossShares(
        type: PartnershipType.mudaraba,
        roles: const [PartnerRole.capitalProvider, PartnerRole.worker],
        capital: [som(30000000), som(0)],
        loss: som(5000000),
      );
      expect(shares, [som(5000000), som(0)]);
    });

    test('mudaraba: beparvolik — ishchiga, lekin faqat izoh bilan', () {
      expect(
        () => PartnershipRules.lossShares(
          type: PartnershipType.mudaraba,
          roles: const [PartnerRole.capitalProvider, PartnerRole.worker],
          capital: [som(30000000), som(0)],
          loss: som(5000000),
          negligence: true,
        ),
        rule(PartnershipRules.errNegligenceNote),
      );
      final shares = PartnershipRules.lossShares(
        type: PartnershipType.mudaraba,
        roles: const [PartnerRole.capitalProvider, PartnerRole.worker],
        capital: [som(30000000), som(0)],
        loss: som(5000000),
        negligence: true,
        note: 'Uskunani qoʻriqlamasdan qoldirgan',
      );
      expect(shares, [som(0), som(5000000)]);
    });
  });

  test('buyout: qoldiq aynan 0, ulush kamayib boradi', () {
    final rows = buyoutSchedule(
      providerStake: som(10000000),
      totalCapital: som(10000000),
      monthly: som(3000000),
      firstDue: LocalDate(2026, 11, 1),
      paid: som(1000000),
    );
    expect(rows, hasLength(3));
    expect(rows.last.payment, som(3000000));
    expect(rows.last.remaining, som(0));
    expect(rows.first.providerShareBp, 6000);
    expect(rows.last.providerShareBp, 0);
  });

  group('servis', () {
    late TestDb t;
    late PartnershipService service;
    late HouseholdService households;
    late MemberPinService memberPins;
    late Member owner;
    late Member wife;
    var gateOpen = false;

    setUp(() async {
      t = TestDb.open();
      gateOpen = false;
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
      service = PartnershipService(
        households: hh,
        members: members,
        memberPins: memberPins,
        partnerships: DriftPartnershipRepository(t.db, t.clock),
        partners: DriftPartnerRepository(t.db, t.clock),
        capital: DriftCapitalContributionRepository(t.db, t.clock),
        contracts: DriftPartnershipContractRepository(t.db, t.clock),
        signers: DriftLoanSignerRepository(t.db, t.clock),
        buyouts: DriftBuyoutPaymentRepository(t.db, t.clock),
        consents: DriftPartnershipConsentRepository(t.db, t.clock),
        gate: () async => gateWith(open: gateOpen),
        metaFactory: t.meta,
        clock: t.clock,
      );
      owner = (await households.members(ownerName: 'Men')).single;
      wife = await households.addMember('Zuhra', MemberRole.adult);
    });

    Future<Partnership> create({required bool meProvider}) => service.create(
      title: 'Tikuvchilik sexi',
      type: PartnershipType.mudaraba,
      partners: [
        provider('Men', 4000, me: meProvider),
        worker('Dilnoza', 6000, me: !meProvider),
      ],
      termMonths: 12,
      reportPeriod: ReportPeriod.monthly,
      endTerms: 'Uskuna kapital egasiga qaytadi',
      disputeTerms: 'Mahalla oqsoqoli huzurida',
      witnesses: ['Bekzod aka'],
    );

    Future<void> signAll(Partnership p) async {
      for (final s in (await service.view(p)).signers) {
        await service.sign(p, s, s.name, [1, 2, 3]);
      }
    }

    test(
      'shartnomasiz sheriklik yoʻq: yaratilganda 1-versiya va imzolar',
      () async {
        final p = await create(meProvider: true);
        final v = await service.view(p);
        expect(v.contracts.single.version, 1);
        expect(v.template, ContractTemplate.mudarabaV1);
        expect(v.template.isPending, isTrue);
        expect(v.signers.map((s) => s.role), [
          SignerRole.party,
          SignerRole.party,
          SignerRole.witness,
        ]);
        expect(v.terms.partners.first.capitalTotal(uzs), som(30000000));
        await expectLater(
          service.activate(p),
          rule(PartnershipService.errContractUnsigned),
        );
        await signAll(p);
        expect(
          (await service.view(p)).partnership.status,
          PartnershipStatus.signed,
        );
      },
    );

    test(
      'imzolangan tomon qayta imzolay olmaydi (imzo jim almashmaydi)',
      () async {
        final p = await create(meProvider: true);
        final first = (await service.view(p)).signers.first;
        await service.sign(p, first, first.name, [1, 2, 3]);
        // Eski (ekrandagi) nusxa bilan ham rad etiladi — holat bazadan olinadi.
        await expectLater(
          service.sign(p, first, 'Boshqa', [4, 5, 6]),
          rule(PartnershipService.errAlreadySigned),
        );
        final stored = (await service.view(p)).signers.singleWhere(
          (s) => s.meta.id == first.meta.id,
        );
        expect(stored.signaturePng, orderedEquals([1, 2, 3]));
      },
    );

    test('kafolatli daromad bilan yaratib boʻlmaydi', () async {
      await expectLater(
        service.create(
          title: 'X',
          type: PartnershipType.mudaraba,
          partners: [
            PartnerDraft(
              name: 'Men',
              role: PartnerRole.capitalProvider,
              profit: ProfitShareInput.fixed(som(1000000)),
              capital: [cash(10000000)],
              isMe: true,
            ),
            worker('Usta', 10000),
          ],
          termMonths: 12,
          reportPeriod: ReportPeriod.monthly,
          endTerms: 'a',
          disputeTerms: 'b',
        ),
        rule(PartnershipRules.errNotPartnership),
      );
      expect(await service.list(), isEmpty);
    });

    test('versiya oʻzgarganda imzolar qayta soʻraladi', () async {
      final p = await create(meProvider: true);
      await signAll(p);
      final v1 = await service.view(p);
      expect(v1.allSigned, isTrue);

      final c2 = await service.amend(p, termMonths: 18);
      final v2 = await service.view(p);
      expect(c2.version, 2);
      expect(v2.contract.meta.id, c2.meta.id);
      expect(v2.contracts, hasLength(2));
      expect(v2.terms.termMonths, 18);
      expect(v2.allSigned, isFalse);
      expect(v2.signers.every((s) => !s.isSigned), isTrue);
      expect(v2.signers, hasLength(3), reason: 'guvoh ham qayta');
      expect(v2.partnership.status, PartnershipStatus.draft);
      // Eski versiya imzolari saqlanadi (tarix).
      expect(
        ContractTerms.fromJson(v2.contracts.first.termsJson).termMonths,
        12,
      );

      // Ulushlarni o'zgartirish ham qoidaga bo'ysunadi.
      final ids = [for (final x in v2.partners) x.meta.id];
      await expectLater(
        service.amend(p, sharesBp: {ids[0]: 5000, ids[1]: 4000}),
        rule(PartnershipRules.errSharesTotal),
      );
      await service.amend(p, sharesBp: {ids[0]: 5000, ids[1]: 5000});
      expect((await service.view(p)).contract.version, 3);
    });

    test(
      'faol sheriklikda yangi versiya — faol qoladi, qayta imzo kerak',
      () async {
        gateOpen = true;
        final p = await create(meProvider: true);
        await signAll(p);
        await service.activate(p);
        await service.amend(p, disputeTerms: 'Hakam orqali');
        final v = await service.view(p);
        expect(v.partnership.status, PartnershipStatus.active);
        expect(v.needsResign, isTrue);
      },
    );

    test('darvoza faqat kapital kirituvchiga qoʻllanadi', () async {
      // Men — kapital egasi: darvoza yopiq → faollashtirib bo'lmaydi.
      final mine = await create(meProvider: true);
      await signAll(mine);
      await expectLater(
        service.activate(mine),
        rule(PartnershipService.errGateClosed),
      );
      // Ongli chetlab o'tish qayd etiladi.
      final active = await service.activate(
        mine,
        gateBypassConfirmed: true,
      );
      expect(active.status, PartnershipStatus.active);

      // Men — mehnat egasi (kapital qabul qilaman): darvoza yopiq bo'lsa ham
      // unga bog'liq emas, lekin «bu qarz emas» va oilaviy rozilik shart.
      final received = await create(meProvider: false);
      await signAll(received);
      await expectLater(
        service.activate(received),
        rule(PartnershipService.errNotDebtAck),
      );
      await service.acknowledgeNotDebt(received);
      await expectLater(
        service.activate(received),
        rule(PartnershipService.errConsentRequired),
      );
      await service.consent(received, owner, '');
      wife = await memberPins.setPin(wife, '482915');
      expect(
        await service.consent(received, wife, '000000'),
        isA<PinRejected>(),
      );
      await expectLater(
        service.activate(received),
        rule(PartnershipService.errConsentRequired),
      );
      expect(
        await service.consent(received, wife, '482915'),
        isA<PinAccepted>(),
      );
      final ok = await service.activate(received);
      expect(ok.status, PartnershipStatus.active);
      expect(gateOpen, isFalse, reason: 'darvoza yopiq edi — talab qilinmadi');
    });

    test('bola rozilik bera olmaydi', () async {
      final p = await create(meProvider: false);
      final son = await households.addMember('Ali', MemberRole.child);
      await expectLater(
        service.consent(p, son, ''),
        rule(PartnershipService.errAdultOnly),
      );
    });

    test('buyout: toʻlovlar qolgan ulushni kamaytiradi', () async {
      final p = await create(meProvider: false);
      await service.setBuyout(p, som(5000000));
      var v = await service.view(p);
      expect(v.providerStake, som(30000000));
      expect(v.buyout, hasLength(6));
      await service.recordBuyout(p, som(10000000));
      v = await service.view(p);
      expect(v.buyoutRemaining, som(20000000));
      expect(v.buyout, hasLength(4));
      expect(v.buyout.last.remaining, som(0));
      await expectLater(
        service.recordBuyout(p, som(20000001)),
        rule(PartnershipService.errNotPositive),
      );
    });
  });
}
