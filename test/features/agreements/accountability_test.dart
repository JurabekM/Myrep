import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

/// Yozuvni qayta hisoblangan xeshlar bilan qurish (zanjirni «tuzatish»).
List<JournalEntry> rechain(List<JournalEntry> list) {
  var prev = genesisHash;
  final out = <JournalEntry>[];
  for (final e in list) {
    final draft = JournalEntry(
      meta: e.meta,
      agreementId: e.agreementId,
      seq: e.seq,
      kind: e.kind,
      date: e.date,
      prevHash: prev,
      hash: '',
      partyId: e.partyId,
      amount: e.amount,
      note: e.note,
      refId: e.refId,
    );
    final h = chainHash(prev, draft.canonical);
    out.add(
      JournalEntry(
        meta: e.meta,
        agreementId: e.agreementId,
        seq: e.seq,
        kind: e.kind,
        date: e.date,
        prevHash: prev,
        hash: h,
        partyId: e.partyId,
        amount: e.amount,
        note: e.note,
        refId: e.refId,
      ),
    );
    prev = h;
  }
  return out;
}

void main() {
  late TestDb t;
  late ProviderContainer c;
  late AgreementService s;
  late AccountabilityService acc;
  late JournalRepository journal;

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
    acc = await c.read(accountabilityServiceProvider.future);
    journal = await c.read(journalRepositoryProvider.future);
  });

  /// Ijara: ikki tomon, bitta vazifa (p1 mas'ul), ko'rik har 30 kunda.
  Future<Agreement> rent() async {
    final a = await s.create(
      type: AgreementType.rent,
      title: 'Doʻkon ijarasi',
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
        AgreementParty(id: 'p2', name: 'Bahodir'),
      ],
      effectiveFrom: today().plusDays(-40),
    );
    final v = await s.view(a);
    await s.saveAnswers(
      a,
      v.answers.copyWith(
        duties: const [
          AgreementDuty(
            id: 'd1',
            title: 'Ijara haqini 5-sanagacha toʻlash',
            ownerPartyId: 'p1',
            breachClause: '3-band: 1 kun ichida xabar berasiz',
          ),
        ],
        custody: const CustodyRule(keeperPartyId: 'p1'),
      ),
    );
    return a;
  }

  /// Imzolangan va faollashgan ijara (yillik yangilash uchun).
  Future<Agreement> activeRent() async {
    final a = await rent();
    var v = await s.view(a);
    v = await s.saveAnswers(
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
            description: 'Doʻkon binosi',
          ),
        ],
        duties: const [
          AgreementDuty(
            id: 'd1',
            title: 'Ijara haqini 5-sanagacha toʻlash',
            ownerPartyId: 'p1',
            breachClause: '3-band: 1 kun ichida xabar berasiz',
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
      ),
    );
    v = await s.prepareSigning(a);
    for (final x in v.signers) {
      v = await s.sign(a, x, x.name, [1]);
    }
    await s.activate(a);
    return a;
  }

  Future<void> money(Agreement a, int major) => journal.append(
    a.meta.id,
    JournalDraft(
      kind: JournalKind.openingBalance,
      date: today(),
      partyId: 'p1',
      amount: som(major),
    ),
  );

  test("kod nomlari jurnal va ko'rik sanasi uchun barqaror", () {
    expect(JournalKind.dutyIncident.code, 'DUTY_INCIDENT');
    expect(JournalKind.accountReview.code, 'ACCOUNT_REVIEW');
    expect(JournalKind.arbiterDecision.code, 'ARBITER_DECISION');
    expect(JournalKind.reviewOpened.isFinancial, isFalse);
    expect(JournalKind.ventureIncome.isFinancial, isTrue);
    expect(JournalKind.correction.isFinancial, isFalse);
  });

  test(
    "vazifa bajarilmadi: sabab va yechim jurnalda, keyingi ko'rikda",
    () async {
      final a = await rent();
      await acc.reportDuty(
        a,
        dutyId: 'd1',
        partyId: 'p1',
        reason: 'Kasal boʻldim',
        fix: '2 kundan keyin toʻlayman',
      );
      final v = await acc.view(a);
      expect(v.incidents, hasLength(1));
      final e = v.incidents.single;
      expect(e.kind, JournalKind.dutyIncident);
      expect(e.refId, 'd1');
      final note = DutyIncidentNote.parse(e.note);
      expect(note.reason, 'Kasal boʻldim');
      expect(note.fix, '2 kundan keyin toʻlayman');

      await expectLater(
        acc.reportDuty(a, dutyId: 'd1', partyId: 'p1', reason: ' ', fix: ''),
        rule(AccountabilityErrors.reasonRequired),
      );
      await expectLater(
        acc.reportDuty(a, dutyId: 'yoq', partyId: 'p1', reason: 'x', fix: ''),
        rule(AccountabilityErrors.dutyNotFound),
      );
    },
  );

  test("ko'rik: ochish → javoblar → bayonnoma chainHead bilan mos", () async {
    final a = await rent();
    await money(a, 1000000);
    await money(a, 250000);

    final id = await acc.openReview(a);
    expect(id, 'review-1');
    var v = await acc.view(a);
    expect(v.review.isOpen, isTrue);
    expect(v.review.openReview!.cutoff, today());
    expect(v.periodEntries.where((e) => e.kind.isFinancial), hasLength(2));
    await expectLater(acc.openReview(a), rule(AccountabilityErrors.reviewOpen));

    await expectLater(
      acc.completeReview(a, reviewId: id),
      rule(AccountabilityErrors.reviewNotAllAcked),
    );
    await acc.acknowledge(
      a,
      reviewId: id,
      partyId: 'p1',
      verdict: ReviewVerdict.agree,
    );
    await expectLater(
      acc.acknowledge(
        a,
        reviewId: id,
        partyId: 'p1',
        verdict: ReviewVerdict.agree,
      ),
      rule(AccountabilityErrors.reviewAlreadyAcked),
    );
    await expectLater(
      acc.acknowledge(
        a,
        reviewId: id,
        partyId: 'p2',
        verdict: ReviewVerdict.object,
        objection: ' ',
      ),
      rule(AccountabilityErrors.objectionRequired),
    );
    await acc.acknowledge(
      a,
      reviewId: id,
      partyId: 'p2',
      verdict: ReviewVerdict.object,
      objection: 'Kassa farqi 10 000 soʻm',
    );
    v = await acc.view(a);
    expect(v.acks['p2']!.verdict, ReviewVerdict.object);

    final minutes = await acc.completeReview(a, reviewId: id);
    final before = (await journal.forAgreement(
      a.meta.id,
    )).where((e) => e.seq < minutes.seq).last;
    final note = ReviewMinutesNote.parse(minutes.note);
    expect(
      note.chainHead,
      before.hash,
      reason: 'bayonnoma zanjir boshini qayd',
    );
    expect(note.objections, {'p2': 'Kassa farqi 10 000 soʻm'});

    final all = await journal.forAgreement(a.meta.id);
    expect(verifyChain(all), isNull);
    expect(minutesIntact(all, minutes), isTrue);
    v = await acc.view(a);
    expect(v.review.isOpen, isFalse);
    expect(v.review.minutesCount, 1);
    expect(v.periodEntries, isEmpty, reason: "yangi davr bo'sh");
  });

  test("o'zgartirilgan yozuv aniqlanadi (ikki usulda)", () async {
    final a = await rent();
    await money(a, 1000000);
    final id = await acc.openReview(a);
    await acc.acknowledge(
      a,
      reviewId: id,
      partyId: 'p1',
      verdict: ReviewVerdict.agree,
    );
    await acc.acknowledge(
      a,
      reviewId: id,
      partyId: 'p2',
      verdict: ReviewVerdict.agree,
    );
    final minutes = await acc.completeReview(a, reviewId: id);
    final all = await journal.forAgreement(a.meta.id);
    expect(minutesIntact(all, minutes), isTrue);

    // 1) Oddiy o'zgartirish: xesh mos kelmaydi — zanjir buziladi.
    final first = all.first;
    final tampered = [
      JournalEntry(
        meta: first.meta,
        agreementId: first.agreementId,
        seq: first.seq,
        kind: first.kind,
        date: first.date,
        prevHash: first.prevHash,
        hash: first.hash,
        partyId: first.partyId,
        amount: som(9999999),
        note: first.note,
        refId: first.refId,
      ),
      ...all.skip(1),
    ];
    expect(verifyChain(tampered), 1);

    // 2) Zanjir qayta hisoblangan: ichki zanjir butun, lekin bayonnomadagi
    // chainHead endi mos kelmaydi.
    final rebuilt = rechain(tampered);
    expect(verifyChain(rebuilt), isNull);
    final rebuiltMinutes = rebuilt.firstWhere(
      (e) => e.meta.id == minutes.meta.id,
    );
    expect(minutesIntact(rebuilt, rebuiltMinutes), isFalse);
  });

  test('bayonnomadan keyin: davrga faqat tuzatuvchi yozuv', () async {
    final a = await rent();
    await money(a, 1000000);
    final id = await acc.openReview(a);
    final open = await journal.forAgreement(a.meta.id);
    // Ochiq ko'rik davomida bugungi moliyaviy yozuv qulflangan.
    expect(
      () => assertWritable(open, JournalKind.ventureIncome, today()),
      rule(AccountabilityErrors.reviewLocked),
    );
    await acc.acknowledge(
      a,
      reviewId: id,
      partyId: 'p1',
      verdict: ReviewVerdict.agree,
    );
    await acc.acknowledge(
      a,
      reviewId: id,
      partyId: 'p2',
      verdict: ReviewVerdict.agree,
    );
    await acc.completeReview(a, reviewId: id);
    final all = await journal.forAgreement(a.meta.id);
    expect(
      () => assertWritable(all, JournalKind.ventureExpense, today()),
      rule(AccountabilityErrors.reviewLocked),
    );
    expect(
      () => assertWritable(all, JournalKind.correction, today()),
      returnsNormally,
    );
    expect(
      () => assertWritable(all, JournalKind.dutyIncident, today()),
      returnsNormally,
      reason: 'hodisa moliyaviy emas',
    );
  });

  test('nizo: IN_DISPUTE, hakam qarori ACTIVE ga qaytaradi', () async {
    final a = await rent();
    final draft = await s.view(a);
    expect(draft.agreement.status, AgreementStatus.draft);
    final disputeId = await acc.openDispute(
      a,
      partyId: 'p2',
      topic: 'Ijara haqi',
      clause: '3-band',
      claim: 'Toʻlov kech boʻldi',
    );
    var v = await acc.view(a);
    expect(v.agreement.status, AgreementStatus.inDispute);
    expect(v.openDisputes.single.id, disputeId);
    expect(v.openDisputes.single.note.topic, 'Ijara haqi');

    await acc.addDisputeClaim(
      a,
      disputeId: disputeId,
      partyId: 'p1',
      claim: 'Kech toʻlash sababli xabar berdim',
    );
    v = await acc.view(a);
    expect(v.disputes.single.claims, hasLength(1));
    expect(
      DisputeNote.parse(v.disputes.single.claims.single.note).claim,
      'Kech toʻlash sababli xabar berdim',
    );

    await expectLater(
      acc.renewUnchanged(a, note: 'x'),
      rule(AccountabilityErrors.inDispute),
    );
    await expectLater(
      acc.openDispute(a, partyId: 'p2', topic: '', clause: '', claim: 'x'),
      rule(AccountabilityErrors.claimRequired),
    );

    await acc.decideDispute(
      a,
      disputeId: disputeId,
      decision: 'Kechikish 3 kun',
    );
    v = await acc.view(a);
    expect(v.agreement.status, AgreementStatus.active);
    expect(v.disputes.single.isOpen, isFalse);
    expect(v.disputes.single.decision!.note, 'Kechikish 3 kun');
    await expectLater(
      acc.decideDispute(a, disputeId: disputeId, decision: 'yana'),
      rule(AccountabilityErrors.disputeDecided),
    );
  });

  test(
    'yillik yangilash: eslatma 30 kun oldin, tasdiq yangi versiya',
    () async {
      final a = await activeRent();
      final v0 = await s.view(a);
      final due = v0.agreement.reviewDate!;
      expect(renewalReminderOn(due), due.plusDays(-30));
      expect(renewalDue(due, due.plusDays(-31)), isFalse);
      expect(renewalDue(due, due.plusDays(-30)), isTrue);

      final renewed = await acc.renewUnchanged(
        a,
        note: 'Oʻzgarishsiz tasdiqlandi',
      );
      expect(renewed.agreement.currentVersion, 2);
      expect(
        renewed.agreement.status,
        AgreementStatus.draft,
        reason: 'qayta imzo',
      );
      expect(renewed.current.note, 'Oʻzgarishsiz tasdiqlandi');
      expect(renewed.agreement.reviewDate, due.plusMonths(12));
      expect(
        [for (final d in renewed.answers.duties) d.title],
        [for (final d in v0.answers.duties) d.title],
        reason: 'matn oʻzgarmadi',
      );
    },
  );

  test(
    "ko'rik davriyligi: boshlanish sanasidan, keyin oxirgi bayonnomadan",
    () async {
      final a = await rent();
      final v = await acc.view(a);
      expect(v.review.dueOn, a.effectiveFrom.plusDays(30));
      expect(
        v.review.isDue(today()),
        isTrue,
        reason: 'ijara 40 kun oldin boshlangan',
      );
    },
  );
}
