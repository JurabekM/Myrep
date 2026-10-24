import 'dart:convert';

import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:meta/meta.dart';

/// Hisob-kitob, ko'rik va nizo xato kodlari (SPEC 2F.4–2F.8).
abstract final class AccountabilityErrors {
  static const reviewLocked = 'agreement_review_locked';
  static const reviewOpen = 'agreement_review_open';
  static const noReview = 'agreement_review_not_open';
  static const reviewNotAllAcked = 'agreement_review_incomplete';
  static const reviewAlreadyAcked = 'agreement_review_already_acked';
  static const objectionRequired = 'agreement_objection_required';
  static const reasonRequired = 'duty_reason_required';
  static const dutyNotFound = 'duty_not_found';
  static const partyNotFound = 'party_not_found';
  static const inDispute = 'agreement_in_dispute';
  static const disputeNotFound = 'dispute_not_found';
  static const disputeDecided = 'dispute_already_decided';
  static const claimRequired = 'dispute_claim_required';
  static const spikeAckRequired = 'profit_spike_ack_required';
  static const alreadyAcked = 'agreement_already_acked';
  static const decisionRequired = 'dispute_decision_required';
}

/// Ko'rik, hodisa va nizo yozuvlarining matni — JSON. Matn jurnal xeshiga
/// kiradi, shuning uchun o'zgartirilsa zanjir buziladi.
Map<String, dynamic> _parse(String? note) {
  if (note == null) return const {};
  try {
    final v = jsonDecode(note);
    return v is Map<String, dynamic> ? v : const {};
  } on FormatException {
    return const {};
  }
}

/// «Vazifamni bajara olmayapman» matni (SPEC 2F.4).
@immutable
final class DutyIncidentNote {
  const DutyIncidentNote({required this.reason, required this.fix});

  factory DutyIncidentNote.parse(String? note) {
    final m = _parse(note);
    return m.isEmpty
        ? DutyIncidentNote(reason: note ?? '', fix: '')
        : DutyIncidentNote(
            reason: m['reason'] as String? ?? '',
            fix: m['fix'] as String? ?? '',
          );
  }

  final String reason;

  /// O'rniga taklif qilingan yechim.
  final String fix;

  String encode() => jsonEncode({'reason': reason, 'fix': fix});
}

enum ReviewVerdict { agree, object }

/// Tomonning ko'rik javobi: «ko'rdim, roziman» yoki «e'tirozim bor + izoh».
@immutable
final class ReviewAckNote {
  const ReviewAckNote({required this.verdict, this.objection});

  factory ReviewAckNote.parse(String? note) {
    final m = _parse(note);
    final verdict = m['verdict'] == 'object'
        ? ReviewVerdict.object
        : ReviewVerdict.agree;
    return ReviewAckNote(
      verdict: verdict,
      objection: m['objection'] as String?,
    );
  }

  final ReviewVerdict verdict;
  final String? objection;

  String encode() => jsonEncode({
    'verdict': verdict.name,
    if (objection != null) 'objection': objection,
  });
}

/// Ko'rik bayonnomasi: o'sha paytdagi zanjir boshi va e'tirozlar.
@immutable
final class ReviewMinutesNote {
  const ReviewMinutesNote({
    required this.chainHead,
    this.objections = const {},
  });

  factory ReviewMinutesNote.parse(String? note) {
    final m = _parse(note);
    final raw =
        (m['objections'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    return ReviewMinutesNote(
      chainHead: m['chainHead'] as String? ?? '',
      objections: {for (final e in raw.entries) e.key: e.value as String},
    );
  }

  /// Bayonnoma yozilgan paytdagi zanjir boshi (oxirgi yozuv xeshi, bayonnoma
  /// yozuvidan oldin). Keyingi `verifyChain` shu xeshni saqlashi kerak.
  final String chainHead;

  /// Tomon ID → e'tiroz matni.
  final Map<String, String> objections;

  String encode() => jsonEncode({
    'chainHead': chainHead,
    'objections': objections,
  });
}

/// Nizo matni: mavzu, tegishli band va talab.
@immutable
final class DisputeNote {
  const DisputeNote({
    required this.topic,
    required this.clause,
    required this.claim,
  });

  factory DisputeNote.parse(String? note) {
    final m = _parse(note);
    if (m.isEmpty) return DisputeNote(topic: '', clause: '', claim: note ?? '');
    return DisputeNote(
      topic: m['topic'] as String? ?? '',
      clause: m['clause'] as String? ?? '',
      claim: m['claim'] as String? ?? '',
    );
  }

  final String topic;
  final String clause;
  final String claim;

  String encode() => jsonEncode({
    'topic': topic,
    'clause': clause,
    'claim': claim,
  });
}

/// Ochiq ko'rik (kesim sanasi bilan).
@immutable
final class OpenReview {
  const OpenReview({
    required this.id,
    required this.cutoff,
    required this.openedSeq,
  });

  final String id;

  /// Kesim: shu sanagacha bo'lgan yozuvlar ko'rib chiqiladi.
  final LocalDate cutoff;
  final int openedSeq;
}

/// Ko'rik holati (SPEC 2F.5), jurnaldan hisoblanadi.
@immutable
final class ReviewState {
  const ReviewState({
    required this.dueOn,
    required this.lastMinutesOn,
    required this.lastMinutesSeq,
    required this.minutesCount,
    this.openReview,
  });

  /// Keyingi ko'rik sanasi: oxirgi bayonnoma (yoki kuchga kirish) + davriylik.
  final LocalDate dueOn;
  final LocalDate? lastMinutesOn;

  /// Oxirgi bayonnoma yozuvining tartib raqami (0 — bayonnoma yo'q).
  final int lastMinutesSeq;
  final int minutesCount;
  final OpenReview? openReview;

  bool get isOpen => openReview != null;

  bool isDue(LocalDate today) => !isOpen && !today.isBefore(dueOn);
}

/// Ko'rik holatini jurnaldan chiqaradi. [journal] — `seq` tartibida.
ReviewState reviewStateOf(
  List<JournalEntry> journal, {
  required LocalDate start,
  required int everyDays,
}) {
  final minutes = [
    for (final e in journal)
      if (e.kind == JournalKind.accountReview) e,
  ];
  final closedIds = {for (final m in minutes) m.refId};
  final opened = [
    for (final e in journal)
      if (e.kind == JournalKind.reviewOpened && !closedIds.contains(e.refId)) e,
  ];
  final last = minutes.isEmpty ? null : minutes.last;
  final base = last?.date ?? start;
  final open = opened.isEmpty ? null : opened.last;
  return ReviewState(
    dueOn: base.plusDays(everyDays),
    lastMinutesOn: last?.date,
    lastMinutesSeq: last?.seq ?? 0,
    minutesCount: minutes.length,
    openReview: open == null
        ? null
        : OpenReview(id: open.refId!, cutoff: open.date, openedSeq: open.seq),
  );
}

/// Keyingi ko'rik ID si: har ochilish bitta ko'rik (`review-1`, `review-2`…).
String nextReviewId(List<JournalEntry> journal) {
  final opened = journal.where((e) => e.kind == JournalKind.reviewOpened);
  return 'review-${opened.length + 1}';
}

/// Davr qulfi: ko'rik ochilgan yoki bayonnoma yozilgan eng oxirgi kesim.
/// Shu sanagacha bo'lgan moliyaviy yozuv qo'shilmaydi (faqat tuzatuvchi).
LocalDate? lockedThrough(List<JournalEntry> journal) {
  LocalDate? latest;
  for (final e in journal) {
    if (e.kind != JournalKind.reviewOpened &&
        e.kind != JournalKind.accountReview) {
      continue;
    }
    if (latest == null || e.date.isAfter(latest)) latest = e.date;
  }
  return latest;
}

/// Moliyaviy yozuv [date] sanasi bilan qo'shilishi mumkinmi (SPEC 2F.5).
void assertWritable(
  List<JournalEntry> journal,
  JournalKind kind,
  LocalDate date,
) {
  if (!kind.isFinancial) return;
  final locked = lockedThrough(journal);
  if (locked != null && !date.isAfter(locked)) {
    throw const DomainRuleException(AccountabilityErrors.reviewLocked);
  }
}

/// Oxirgi bayonnomadan keyingi hodisalar (keyingi ko'rikda ko'rinadi).
List<JournalEntry> openIncidents(List<JournalEntry> journal, int sinceSeq) => [
  for (final e in journal)
    if (e.kind == JournalKind.dutyIncident && e.seq > sinceSeq) e,
];

/// Ko'rik uchun davr yozuvlari: oxirgi bayonnomadan keyin, [cutoff] gacha.
List<JournalEntry> periodEntries(
  List<JournalEntry> journal, {
  required int afterSeq,
  LocalDate? cutoff,
}) => [
  for (final e in journal)
    if (e.seq > afterSeq &&
        (e.kind.isFinancial || e.kind == JournalKind.dutyIncident) &&
        (cutoff == null || !e.date.isAfter(cutoff)))
      e,
];

/// «Katta foyda» kaliti: davr tugashi va foyda (minor) bo'yicha — foyda
/// o'zgarsa, tasdiq qayta talab qilinadi.
String profitSpikeKey(LocalDate periodEnd, int actualMinor) =>
    'spike:$periodEnd:$actualMinor';

/// Shu kalit bo'yicha tasdiqlagan tomonlar.
Set<String> profitSpikeAcks(List<JournalEntry> journal, String key) => {
  for (final e in journal)
    if (e.kind == JournalKind.profitSpikeAck &&
        e.refId == key &&
        e.partyId != null)
      e.partyId!,
};

/// Nizo: ildiz yozuv, boshqa tomonlarning talablari va hakam qarori.
@immutable
final class DisputeCase {
  const DisputeCase({
    required this.root,
    required this.claims,
    this.decision,
  });

  final JournalEntry root;
  final List<JournalEntry> claims;
  final JournalEntry? decision;

  String get id => root.meta.id;
  bool get isOpen => decision == null;
  DisputeNote get note => DisputeNote.parse(root.note);
}

/// Barcha nizolar (ochiq va yopilgan), ochilish tartibida.
List<DisputeCase> disputesOf(List<JournalEntry> journal) => [
  for (final r in journal)
    if (r.kind == JournalKind.disputeOpened && r.refId == null)
      DisputeCase(
        root: r,
        claims: [
          for (final e in journal)
            if (e.kind == JournalKind.disputeOpened && e.refId == r.meta.id) e,
        ],
        decision: _decisionFor(journal, r.meta.id),
      ),
];

JournalEntry? _decisionFor(List<JournalEntry> journal, String rootId) {
  JournalEntry? found;
  for (final e in journal) {
    if (e.kind == JournalKind.arbiterDecision && e.refId == rootId) found = e;
  }
  return found;
}

/// Yillik yangilash eslatmasi sanasi: `reviewDate` dan 30 kun oldin
/// (SPEC 2F, 6-qonun). Eslatma 09:00 da (Asia/Tashkent) ko'rsatiladi.
LocalDate renewalReminderOn(LocalDate reviewDate) => reviewDate.plusDays(-30);

/// Yangilash vaqti kelganmi (eslatma sanasi bugun yoki o'tgan).
bool renewalDue(LocalDate reviewDate, LocalDate today) =>
    !today.isBefore(renewalReminderOn(reviewDate));

/// Bayonnoma zanjiri (SPEC 2F.6): [minutes] dan oldingi yozuvlar buzilmagan
/// va ularning oxirgi xeshi bayonnomadagi `chainHead` bilan mos. O'zgartirilgan
/// yozuv (hatto zanjir qayta hisoblangan bo'lsa ham) shu yerda aniqlanadi.
bool minutesIntact(List<JournalEntry> journal, JournalEntry minutes) {
  final idx = journal.indexWhere((e) => e.meta.id == minutes.meta.id);
  if (idx < 0) return false;
  final before = journal.sublist(0, idx);
  if (verifyChain(before) != null) return false;
  final head = before.isEmpty ? genesisHash : before.last.hash;
  return head == ReviewMinutesNote.parse(minutes.note).chainHead;
}
