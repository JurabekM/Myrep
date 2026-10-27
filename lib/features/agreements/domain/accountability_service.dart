import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:meta/meta.dart';

/// Kelishuv ko'rinishi kengaytirilgan: ko'rik, hodisalar, nizolar (SPEC 2F.4,
/// 2F.5, 2F.8). Hammasi jurnal yozuvlari orqali — alohida jadval yo'q.
@immutable
final class AccountabilityView {
  const AccountabilityView({
    required this.base,
    required this.review,
    required this.periodEntries,
    required this.incidents,
    required this.acks,
    required this.disputes,
    required this.minutes,
  });

  final AgreementView base;
  final ReviewState review;

  /// Ko'rik davri yozuvlari (oxirgi bayonnomadan keyin, kesimgacha).
  final List<JournalEntry> periodEntries;

  /// Oxirgi bayonnomadan keyingi «bajarilmadi» hodisalari.
  final List<JournalEntry> incidents;

  /// Ochiq ko'rikdagi tomonlar javobi (tomon ID → javob).
  final Map<String, ReviewAckNote> acks;
  final List<DisputeCase> disputes;

  /// Barcha ko'rik bayonnomalari, eskisi birinchi.
  final List<JournalEntry> minutes;

  Agreement get agreement => base.agreement;

  List<DisputeCase> get openDisputes => [
    for (final d in disputes)
      if (d.isOpen) d,
  ];

  /// Yillik yangilash eslatmasi sanasi (`reviewDate` dan 30 kun oldin).
  LocalDate? get renewalOn {
    final r = agreement.reviewDate;
    return r == null ? null : renewalReminderOn(r);
  }
}

/// Kelishuvning ko'rik, «bajarilmadi», nizo va yangilash amallari
/// (SPEC 2F.4, 2F.5, 2F.8, 2F.10). Har bir amal jurnalga yozadi.
class AccountabilityService {
  AccountabilityService({
    required AgreementService agreements,
    required AgreementRepository repo,
    required JournalRepository journal,
    required Clock clock,
  }) : _agreements = agreements,
       _repo = repo,
       _journal = journal,
       _clock = clock;

  final AgreementService _agreements;
  final AgreementRepository _repo;
  final JournalRepository _journal;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  Future<AccountabilityView> view(Agreement agreement) async {
    final base = await _agreements.view(agreement);
    final a = base.agreement;
    final journal = base.journal;
    final review = reviewStateOf(
      journal,
      start: a.effectiveFrom,
      everyDays: base.answers.custody.reviewEveryDays,
    );
    final open = review.openReview;
    return AccountabilityView(
      base: base,
      review: review,
      periodEntries: periodEntries(
        journal,
        afterSeq: review.lastMinutesSeq,
        cutoff: open?.cutoff,
      ),
      incidents: openIncidents(journal, review.lastMinutesSeq),
      acks: open == null ? const {} : _acksOf(journal, open.id),
      disputes: disputesOf(journal),
      minutes: [
        for (final e in journal)
          if (e.kind == JournalKind.accountReview) e,
      ],
    );
  }

  /// Ko'rik davriga tegishli javoblar (tomon ID → javob).
  static Map<String, ReviewAckNote> _acksOf(
    List<JournalEntry> journal,
    String reviewId,
  ) => {
    for (final e in journal)
      if (e.kind == JournalKind.reviewAck &&
          e.refId == reviewId &&
          e.partyId != null)
        e.partyId!: ReviewAckNote.parse(e.note),
  };

  void _ensureNotClosed(Agreement a) {
    if (a.status == AgreementStatus.closed) {
      throw const DomainRuleException(AgreementService.errClosed);
    }
  }

  /// «Vazifamni bajara olmayapman» (SPEC 2F.4). Ayblov emas: sabab, sana va
  /// o'rniga yechim yoziladi.
  Future<JournalEntry> reportDuty(
    Agreement agreement, {
    required String dutyId,
    required String partyId,
    required String reason,
    required String fix,
  }) async {
    final v = await _agreements.view(agreement);
    _ensureNotClosed(v.agreement);
    if (reason.trim().isEmpty) {
      throw const DomainRuleException(AccountabilityErrors.reasonRequired);
    }
    if (v.answers.duties.every((d) => d.id != dutyId)) {
      throw const DomainRuleException(AccountabilityErrors.dutyNotFound);
    }
    if (v.answers.party(partyId) == null) {
      throw const DomainRuleException(AccountabilityErrors.partyNotFound);
    }
    return _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.dutyIncident,
        date: today,
        partyId: partyId,
        note: DutyIncidentNote(reason: reason.trim(), fix: fix.trim()).encode(),
        refId: dutyId,
      ),
    );
  }

  /// Ochiq ko'rik boshlash (SPEC 2F.5). Kesim — bugun; shu sanagacha bo'lgan
  /// moliyaviy yozuvlar ko'rik tugaguncha qulflanadi. Qaytaradi — ko'rik ID.
  Future<String> openReview(Agreement agreement) async {
    final v = await _agreements.view(agreement);
    _ensureNotClosed(v.agreement);
    final state = reviewStateOf(
      v.journal,
      start: v.agreement.effectiveFrom,
      everyDays: v.answers.custody.reviewEveryDays,
    );
    if (state.isOpen) {
      throw const DomainRuleException(AccountabilityErrors.reviewOpen);
    }
    final id = nextReviewId(v.journal);
    await _journal.append(
      agreement.meta.id,
      JournalDraft(kind: JournalKind.reviewOpened, date: today, refId: id),
    );
    return id;
  }

  /// Tomonning javobi: «ko'rdim, roziman» yoki «e'tirozim bor + izoh».
  Future<void> acknowledge(
    Agreement agreement, {
    required String reviewId,
    required String partyId,
    required ReviewVerdict verdict,
    String? objection,
  }) async {
    final v = await _agreements.view(agreement);
    final open = _openReviewOrThrow(v, reviewId);
    if (v.answers.party(partyId) == null) {
      throw const DomainRuleException(AccountabilityErrors.partyNotFound);
    }
    if (_acksOf(v.journal, open.id).containsKey(partyId)) {
      throw const DomainRuleException(AccountabilityErrors.reviewAlreadyAcked);
    }
    final text = objection?.trim() ?? '';
    if (verdict == ReviewVerdict.object && text.isEmpty) {
      throw const DomainRuleException(AccountabilityErrors.objectionRequired);
    }
    await _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.reviewAck,
        date: open.cutoff,
        partyId: partyId,
        refId: open.id,
        note: ReviewAckNote(
          verdict: verdict,
          objection: verdict == ReviewVerdict.object ? text : null,
        ).encode(),
      ),
    );
  }

  /// Ko'rikni yakunlash: hamma tomon javob bergan bo'lishi kerak. Bayonnoma
  /// yozuvi `chainHead` (bayonnomadan oldingi zanjir boshi) va e'tirozlarni
  /// saqlaydi. Shundan keyin shu davrga faqat tuzatuvchi yozuv qo'shiladi.
  Future<JournalEntry> completeReview(
    Agreement agreement, {
    required String reviewId,
  }) async {
    final v = await _agreements.view(agreement);
    final open = _openReviewOrThrow(v, reviewId);
    final acks = _acksOf(v.journal, open.id);
    if (v.answers.parties.any((p) => !acks.containsKey(p.id))) {
      throw const DomainRuleException(AccountabilityErrors.reviewNotAllAcked);
    }
    final head = v.journal.isEmpty ? genesisHash : v.journal.last.hash;
    final objections = {
      for (final p in v.answers.parties)
        if (acks[p.id]!.verdict == ReviewVerdict.object)
          p.id: acks[p.id]!.objection ?? '',
    };
    return _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.accountReview,
        date: open.cutoff,
        refId: open.id,
        note: ReviewMinutesNote(
          chainHead: head,
          objections: objections,
        ).encode(),
      ),
    );
  }

  OpenReview _openReviewOrThrow(AgreementView v, String reviewId) {
    final open = reviewStateOf(
      v.journal,
      start: v.agreement.effectiveFrom,
      everyDays: v.answers.custody.reviewEveryDays,
    ).openReview;
    if (open == null || open.id != reviewId) {
      throw const DomainRuleException(AccountabilityErrors.noReview);
    }
    return open;
  }

  /// «Katta foyda»dan keyin: tomon 4–5-bandni qayta o'qiganini belgilaydi
  /// (SPEC 2F.7). [key] — `ProfitSpikeCheck.key` (davr va foyda bo'yicha).
  Future<void> acknowledgeSpike(
    Agreement agreement, {
    required String partyId,
    required String key,
  }) async {
    final v = await _agreements.view(agreement);
    if (v.answers.party(partyId) == null) {
      throw const DomainRuleException(AccountabilityErrors.partyNotFound);
    }
    if (profitSpikeAcks(v.journal, key).contains(partyId)) {
      throw const DomainRuleException(AccountabilityErrors.alreadyAcked);
    }
    await _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.profitSpikeAck,
        date: today,
        partyId: partyId,
        refId: key,
      ),
    );
  }

  /// Nizo ochish (SPEC 2F.8): kelishuv `IN_DISPUTE` bo'ladi va taqsimot
  /// to'xtaydi. Qaytaradi — nizo ID (ildiz yozuv ID si).
  Future<String> openDispute(
    Agreement agreement, {
    required String partyId,
    required String topic,
    required String clause,
    required String claim,
  }) async {
    final v = await _agreements.view(agreement);
    _ensureNotClosed(v.agreement);
    if (topic.trim().isEmpty || claim.trim().isEmpty) {
      throw const DomainRuleException(AccountabilityErrors.claimRequired);
    }
    if (v.answers.party(partyId) == null) {
      throw const DomainRuleException(AccountabilityErrors.partyNotFound);
    }
    final entry = await _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.disputeOpened,
        date: today,
        partyId: partyId,
        note: DisputeNote(
          topic: topic.trim(),
          clause: clause.trim(),
          claim: claim.trim(),
        ).encode(),
      ),
    );
    if (v.agreement.status != AgreementStatus.inDispute) {
      await _repo.update(
        v.agreement.copyWith(status: AgreementStatus.inDispute),
      );
    }
    return entry.meta.id;
  }

  /// Boshqa tomonning talabi (ochiq nizoga).
  Future<void> addDisputeClaim(
    Agreement agreement, {
    required String disputeId,
    required String partyId,
    required String claim,
  }) async {
    final v = await _agreements.view(agreement);
    final dispute = _openDisputeOrThrow(v, disputeId);
    if (claim.trim().isEmpty) {
      throw const DomainRuleException(AccountabilityErrors.claimRequired);
    }
    if (v.answers.party(partyId) == null) {
      throw const DomainRuleException(AccountabilityErrors.partyNotFound);
    }
    await _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.disputeOpened,
        date: today,
        partyId: partyId,
        refId: dispute.id,
        note: DisputeNote(topic: '', clause: '', claim: claim.trim()).encode(),
      ),
    );
  }

  DisputeCase _openDisputeOrThrow(AgreementView v, String disputeId) {
    final found = [
      for (final d in disputesOf(v.journal))
        if (d.id == disputeId) d,
    ];
    if (found.isEmpty) {
      throw const DomainRuleException(AccountabilityErrors.disputeNotFound);
    }
    if (!found.single.isOpen) {
      throw const DomainRuleException(AccountabilityErrors.disputeDecided);
    }
    return found.single;
  }

  /// Hakam qarori (SPEC 2F.8). Qaror kelishuv tarixiga yoziladi; boshqa ochiq
  /// nizo qolmasa, kelishuv `ACTIVE` ga qaytadi. Matn o'zgarishi kerak bo'lsa,
  /// «Yangi versiya» orqali qayta imzolanadi (versiya o'zgarmasdan qaytmaydi).
  Future<void> decideDispute(
    Agreement agreement, {
    required String disputeId,
    required String decision,
  }) async {
    final v = await _agreements.view(agreement);
    final dispute = _openDisputeOrThrow(v, disputeId);
    if (decision.trim().isEmpty) {
      throw const DomainRuleException(AccountabilityErrors.decisionRequired);
    }
    await _journal.append(
      agreement.meta.id,
      JournalDraft(
        kind: JournalKind.arbiterDecision,
        date: today,
        refId: dispute.id,
        note: decision.trim(),
      ),
    );
    final after = await _agreements.view(agreement);
    final stillOpen = disputesOf(after.journal).any((d) => d.isOpen);
    if (!stillOpen && after.agreement.status == AgreementStatus.inDispute) {
      await _repo.update(
        after.agreement.copyWith(status: AgreementStatus.active),
      );
    }
  }

  /// Yillik yangilash: «o'zgarishsiz tasdiqlash» — yangi versiya (qayta imzo)
  /// va `reviewDate` bir yilga suriladi (SPEC 6-qonun, 9-savol).
  Future<AgreementView> renewUnchanged(
    Agreement agreement, {
    required String note,
  }) async {
    final v = await _agreements.view(agreement);
    if (v.agreement.status == AgreementStatus.inDispute) {
      throw const DomainRuleException(AccountabilityErrors.inDispute);
    }
    final from = v.answers.term.reviewDate ?? v.agreement.reviewDate ?? today;
    final next = from.plusMonths(12);
    return _agreements.newVersion(
      v.agreement,
      answers: v.answers.copyWith(
        term: TermRule(
          termMonths: v.answers.term.termMonths,
          reviewDate: next,
        ),
      ),
      note: note,
    );
  }
}
