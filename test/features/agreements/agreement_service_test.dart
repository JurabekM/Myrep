import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/builders.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/debts/data/debt_providers.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/agreements.dart';
import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

void main() {
  late TestDb t;
  late ProviderContainer c;
  late AgreementService s;

  LocalDate today() => Tashkent.dateOf(t.clock.nowUtc());

  setUp(() async {
    t = TestDb.open();
    c = ProviderContainer(
      overrides: [
        appDatabaseProvider.overrideWith((ref) async => t.db),
        clockProvider.overrideWithValue(t.clock),
        secureBlobStoreProvider.overrideWithValue(InMemorySecureBlobStore()),
        pinHasherProvider.overrideWithValue(ReferencePinHasher()),
      ],
    );
    addTearDown(c.dispose);
    s = await c.read(agreementServiceProvider.future);
  });

  AgreementAnswers full(AgreementAnswers a) => a.copyWith(
    contributions: [
      AgreementContribution(
        partyId: 'p1',
        kind: ContributionKind.money,
        amount: som(2000000),
      ),
      const AgreementContribution(
        partyId: 'p2',
        kind: ContributionKind.goods,
        description: 'Doʻkon binosi',
      ),
    ],
    duties: const [
      AgreementDuty(
        id: 'd1',
        title: 'Ijara haqini 5-sanagacha toʻlash',
        ownerPartyId: 'p1',
        breachClause: '3 kun ichida xabar beradi',
      ),
      AgreementDuty(
        id: 'd2',
        title: 'Tomni taʼmirlash',
        ownerPartyId: 'p2',
        breachClause: 'Ijarachi taʼmirlab, haqdan ayiradi',
      ),
    ],
    profit: const ProfitRule(text: 'Ijara haqi oyiga 2 mln soʻm'),
    lossText: 'Bino zarari — egasida',
    custody: const CustodyRule(
      where: 'Naqd, tilxat bilan',
      keeperPartyId: 'p1',
    ),
    exit: const ExitClause(
      noticeDays: 30,
      valuation: 'Oldindan toʻlangan qism qaytariladi',
      payout: '10 kun ichida',
    ),
    arbiter: const ArbiterInfo(name: 'Mahalla raisi'),
  );

  test('ijara: 9/9 gacha imzo yopiq → SIGNED → ACTIVE', () async {
    final a = await s.create(
      type: AgreementType.rent,
      title: 'Doʻkon ijarasi',
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
        AgreementParty(id: 'p2', name: 'Bahodir'),
      ],
    );
    var v = await s.view(a);
    expect(v.completeness.answered, 2, reason: '1 va 9 (yangilash sanasi)');
    expect(v.canSign, isFalse);
    await expectLater(
      s.prepareSigning(a),
      rule(AgreementService.errIncomplete),
    );

    v = await s.saveAnswers(a, full(v.answers));
    expect(v.completeness.complete, isTrue);
    expect(v.agreement.reviewDate, today().plusMonths(12));
    v = await s.prepareSigning(a);
    expect(v.signers.map((x) => x.role), [
      SignerRole.party,
      SignerRole.party,
      SignerRole.arbiter,
    ]);
    for (final x in v.signers) {
      v = await s.sign(a, x, x.name, [1]);
    }
    expect(v.agreement.status, AgreementStatus.signed);
    expect(v.editable, isFalse);
    await expectLater(
      s.saveAnswers(a, v.answers.copyWith(lossText: 'oʻzgardi')),
      rule(AgreementService.errNotEditable),
    );
    expect((await s.activate(a)).status, AgreementStatus.active);

    // Yillik yangilash: o'zgarishsiz — baribir yangi versiya va qayta imzo.
    v = await s.newVersion(a, note: 'Oʻzgarishsiz tasdiqlandi');
    expect(v.agreement.currentVersion, 2);
    expect(v.agreement.status, AgreementStatus.draft);
    expect(v.current.note, 'Oʻzgarishsiz tasdiqlandi');
    expect(v.signers, isEmpty);
    expect(v.versions.first.answers.lossText, 'Bino zarari — egasida');
  });

  test(
    'imzolagan tomon qayta imzolay olmaydi (imzo jim almashmaydi)',
    () async {
      final a = await s.create(
        type: AgreementType.rent,
        title: 'Doʻkon ijarasi',
        parties: const [
          AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
          AgreementParty(id: 'p2', name: 'Bahodir'),
        ],
      );
      var v = await s.saveAnswers(a, full((await s.view(a)).answers));
      v = await s.prepareSigning(a);
      final first = v.signers.first;
      await s.sign(a, first, first.name, [1, 2]);
      await expectLater(
        s.sign(a, first, 'Boshqa', [3, 4]),
        rule(AgreementService.errAlreadySigned),
      );
      final stored = (await s.view(a)).signers.singleWhere(
        (x) => x.meta.id == first.meta.id,
      );
      expect(stored.signaturePng, orderedEquals([1, 2]));
    },
  );

  test('imzodan oldin tomon oʻzgarsa — imzolovchilar yangilanadi', () async {
    final a = await s.create(
      type: AgreementType.service,
      title: 'Taʼmir',
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal'),
        AgreementParty(id: 'p2', name: 'Usta'),
      ],
    );
    var v = await s.saveAnswers(a, full((await s.view(a)).answers));
    v = await s.prepareSigning(a);
    final renamed = v.answers.copyWith(
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal'),
        AgreementParty(id: 'p2', name: 'Usta Karim'),
      ],
    );
    v = await s.saveAnswers(a, renamed);
    expect(v.signers.map((x) => x.name), contains('Usta Karim'));
    expect(v.signers.map((x) => x.name), isNot(contains('Usta')));
  });

  test('ogʻzaki kelishuv: oʻtgan sanadan, holat jurnalda', () async {
    const parties = [
      AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
      AgreementParty(id: 'p2', name: 'Jasur'),
    ];
    await expectLater(
      s.recordOral(
        type: AgreementType.partnership,
        title: 'Yetkazib berish',
        parties: parties,
        effectiveFrom: today().plusDays(1),
        opening: const [],
      ),
      rule(AgreementService.errFutureDate),
    );
    final a = await s.recordOral(
      type: AgreementType.partnership,
      title: 'Yetkazib berish',
      parties: parties,
      effectiveFrom: LocalDate(2026, 4, 1),
      opening: [
        OpeningLine(partyId: 'p1', amount: som(3000000)),
        OpeningLine(partyId: 'p2', amount: som(3000000)),
      ],
      openingNote: '6 oyda 3 marta foyda boʻlingan',
    );
    final v = await s.view(a);
    expect(v.agreement.oral, isTrue);
    expect(v.agreement.effectiveFrom, LocalDate(2026, 4, 1));
    expect(v.journal.map((e) => e.kind), [
      JournalKind.openingBalance,
      JournalKind.openingBalance,
    ]);
    expect(v.journal.first.note, '6 oyda 3 marta foyda boʻlingan');
    expect(v.brokenAt, isNull);
  });

  test('jurnal: tuzatish yangi yozuv; oʻzgartirish aniqlanadi', () async {
    final a = await s.recordOral(
      type: AgreementType.other,
      title: 'Qarz',
      parties: const [
        AgreementParty(id: 'p1', name: 'A'),
        AgreementParty(id: 'p2', name: 'B'),
      ],
      effectiveFrom: LocalDate(2026, 1, 1),
      opening: [OpeningLine(partyId: 'p1', amount: som(1000000))],
    );
    await s.correct(a, note: 'Notoʻgʻri summa', amount: som(-100000));
    expect(await s.verify(a), isNull);
    // Trigger chetlab o'tilgan holat (masalan, fayl qo'lda tahrirlangan):
    // zanjir buzilgan joyni aniq ko'rsatadi.
    await t.db.customStatement('DROP TRIGGER journal_entries_no_update');
    await t.db.customStatement(
      'UPDATE journal_entries SET amount_minor = 999 WHERE seq = 1',
    );
    expect(await s.verify(a), 1);
  });

  test('tilxat: qarz toʻlovlari jurnalga, ensureLoan takrorlanmaydi', () async {
    final debts = await c.read(debtServiceProvider.future);
    final d = await debts.add(
      creditorType: CreditorType.relative,
      creditorName: 'Togʻa',
      principal: som(3000000),
      scheduleType: DebtScheduleType.manual,
      manual: [
        Installment(
          dueOn: LocalDate(2026, 12, 1),
          amount: som(3000000),
          interest: som(0),
        ),
      ],
    );
    Future<Agreement> ensure() => s.ensureLoan(
      source: AgreementSource.debt,
      documentId: d.debt.meta.id,
      lender: 'Togʻa',
      borrower: 'Akmal',
      meIsLender: false,
      principal: som(3000000),
      start: today(),
      lastDue: LocalDate(2026, 12, 1),
    );
    final a = await ensure();
    expect((await ensure()).meta.id, a.meta.id);
    var v = await s.view(a);
    expect(v.current.meta.id, d.debt.meta.id, reason: 'versiya ID = qarz ID');
    expect(v.completeness.missing.map((q) => q.number), [6, 7, 8]);
    await debts.pay(d.debt, som(1000000));
    v = await s.view(a);
    expect(v.journal.map((e) => e.kind), [
      JournalKind.contribution,
      JournalKind.loanPayment,
    ]);
    expect(v.journal.last.partyId, borrowerPartyId);
    expect(v.brokenAt, isNull);
    v = await completeAgreement(s, AgreementSource.debt, d.debt.meta.id);
    expect(v.canSign, isTrue);
  });

  test('sheriklik: shartnoma = Agreement, 9/9 siz imzo yoʻq', () async {
    final p = await c.read(partnershipServiceProvider.future);
    final created = await p.create(
      title: 'Yetkazib berish',
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
              amount: som(3000000),
            ),
          ],
          isMe: true,
        ),
        PartnerDraft(
          name: 'Jasur',
          role: PartnerRole.both,
          profit: const ProfitShareInput.percent(5000),
          capital: [
            CapitalItem(
              kind: CapitalKind.cash,
              title: 'Naqd',
              amount: som(3000000),
            ),
          ],
        ),
      ],
      termMonths: 12,
      reportPeriod: ReportPeriod.monthly,
      endTerms: 'Mol sotilib, kapitalga mutanosib',
      disputeTerms: 'Oqsoqol',
    );
    var ag = (await s.bySource(
      AgreementSource.partnership,
      created.meta.id,
    ))!;
    var v = await s.view(ag);
    expect(v.current.meta.id, (await p.view(created)).contract.meta.id);
    expect(v.completeness.missing.map((q) => q.number), [3, 6, 7, 8]);
    final signer = (await p.view(created)).signers.first;
    await expectLater(
      p.sign(created, signer, signer.name, [1]),
      rule(PartnershipService.errAgreementIncomplete),
    );
    v = await completeAgreement(
      s,
      AgreementSource.partnership,
      created.meta.id,
    );
    expect(v.canSign, isTrue);
    // Hakam shartnoma imzolovchilariga qo'shildi.
    final pv = await p.view(created);
    expect(pv.signers.map((x) => x.role), contains(SignerRole.arbiter));
    for (final x in pv.signers) {
      await p.sign(created, x, x.name, [1]);
    }
    ag = (await s.find(ag.meta.id))!;
    expect(ag.status, AgreementStatus.signed);

    // O'zgarish — yangi versiya: 3, 6, 8-savollar saqlanadi, imzo qaytadan.
    await p.amend(created, termMonths: 18);
    v = await s.view(ag);
    expect(v.agreement.currentVersion, 2);
    expect(v.agreement.status, AgreementStatus.draft);
    expect(v.answers.arbiter?.name, 'Shavkat aka');
    expect(v.answers.duties, hasLength(2));
    expect(v.answers.term.termMonths, 18);
    expect(v.completeness.complete, isTrue);
  });
}
