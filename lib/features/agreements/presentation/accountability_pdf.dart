import 'dart:typed_data';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';

/// Ko'rik bayonnomasi va hakam papkasi bloklari (SPEC 2F.5, 2F.8). Matnlar
/// ARB'dan; jadval va sarlavhalar `core/pdf` orqali chiqadi.

String _short(String hash) => hash.length < 16 ? hash : hash.substring(0, 16);

String _partyName(AgreementAnswers answers, String? id) =>
    id == null ? '—' : (answers.party(id)?.name ?? '—');

/// Yozuvlar jadvali: sana, tur, tomon, summa, izoh.
PdfTable _ledgerTable(
  AppLocalizations l,
  String Function(Money) money,
  AgreementAnswers answers,
  List<JournalEntry> entries,
) => PdfTable(
  headers: [
    l.acPdfColDate,
    l.acPdfColKind,
    l.acPdfColParty,
    l.acPdfColAmount,
    l.acPdfColNote,
  ],
  rows: [
    for (final e in entries)
      [
        formatDate(e.date),
        agJournalKind(l, e.kind),
        _partyName(answers, e.partyId),
        if (e.amount != null) money(e.amount!) else '—',
        e.note ?? '',
      ],
  ],
  numericColumns: const {3},
);

/// Bayonnomadan oldingi davr yozuvlari: oxirgi bayonnomadan keyin, kesimgacha.
List<JournalEntry> _periodBefore(
  List<JournalEntry> journal,
  JournalEntry minutes,
) {
  final idx = journal.indexWhere((e) => e.meta.id == minutes.meta.id);
  final prior = journal.sublist(0, idx);
  var afterSeq = 0;
  for (final e in prior) {
    if (e.kind == JournalKind.accountReview) afterSeq = e.seq;
  }
  return periodEntries(prior, afterSeq: afterSeq, cutoff: minutes.date);
}

/// Ko'rik bayonnomasi bloklari: kesim, zanjir boshi, davr yozuvlari, hodisalar,
/// har bir tomonning javobi va e'tirozlari.
List<PdfBlock> reviewMinutesBlocks({
  required AppLocalizations l,
  required String Function(Money) money,
  required AgreementAnswers answers,
  required List<JournalEntry> journal,
  required JournalEntry minutes,
}) {
  final note = ReviewMinutesNote.parse(minutes.note);
  final entries = _periodBefore(journal, minutes);
  final incidents = [
    for (final e in entries)
      if (e.kind == JournalKind.dutyIncident) e,
  ];
  final ledger = [
    for (final e in entries)
      if (e.kind.isFinancial) e,
  ];
  final acks = {
    for (final e in journal)
      if (e.kind == JournalKind.reviewAck &&
          e.refId == minutes.refId &&
          e.partyId != null)
        e.partyId!: ReviewAckNote.parse(e.note),
  };
  final intact = minutesIntact(journal, minutes);
  return [
    PdfParagraph(l.acPdfCutoffLine(formatDate(minutes.date))),
    PdfKeyValues([
      (l.agChainHead, _short(note.chainHead)),
      (l.agJournal, '${minutes.seq}'),
    ]),
    PdfParagraph(
      intact
          ? l.acReviewChainOk(minutes.seq - 1)
          : l.acReviewChainBroken(verifyChain(journal) ?? minutes.seq),
    ),
    PdfHeading(l.acReviewPeriodTitle),
    if (ledger.isEmpty)
      PdfParagraph(l.acReviewPeriodEmpty)
    else
      _ledgerTable(l, money, answers, ledger),
    PdfHeading(l.acReviewIncidents),
    if (incidents.isEmpty)
      PdfParagraph(l.acPdfNone)
    else
      for (final e in incidents)
        PdfParagraph(
          l.acPdfIncidentLine(
            formatDate(e.date),
            _partyName(answers, e.partyId),
            DutyIncidentNote.parse(e.note).reason,
          ),
        ),
    PdfHeading(l.acReviewAcksTitle),
    for (final p in answers.parties)
      PdfParagraph(
        acks[p.id] == null
            ? '${p.name}: —'
            : acks[p.id]!.verdict == ReviewVerdict.agree
            ? l.acReviewVerdictAgree(p.name)
            : l.acReviewVerdictObject(p.name, acks[p.id]!.objection ?? ''),
      ),
    PdfNote(l.agPdfNote),
  ];
}

/// Hakam uchun ish papkasi (SPEC 2F.8): kelishuv va versiyalar, tomonlar,
/// hisob yozuvlari va zanjir tekshiruvi, ko'rik bayonnomalari, hodisalar,
/// ikki tomonning talablari va hakam qarorlari.
List<PdfBlock> arbiterFolderBlocks({
  required AppLocalizations l,
  required String Function(Money) money,
  required AgreementView view,
  required DisputeCase dispute,
  required List<JournalEntry> journal,
}) {
  final answers = view.answers;
  final a = view.agreement;
  final intBroken = verifyChain(journal);
  final minutes = [
    for (final e in journal)
      if (e.kind == JournalKind.accountReview) e,
  ];
  final incidents = [
    for (final e in journal)
      if (e.kind == JournalKind.dutyIncident) e,
  ];
  final decisions = [
    for (final e in journal)
      if (e.kind == JournalKind.arbiterDecision && e.refId == dispute.id) e,
  ];
  final financial = [
    for (final e in journal)
      if (e.kind.isFinancial) e,
  ];
  final head = journal.isEmpty ? genesisHash : journal.last.hash;
  final note = dispute.note;
  return [
    PdfHeading(l.acPdfFolderAgreement),
    PdfParagraph(
      '${agType(l, a.type)} · ${agStatus(l, a.status)} · '
      '${l.agVersion(a.currentVersion)}',
    ),
    PdfHeading(l.acPdfFolderVersions),
    PdfTable(
      headers: [l.acPdfColDate, l.acPdfColNote],
      rows: [
        for (final v in view.versions)
          [
            formatDate(Tashkent.dateOf(v.meta.createdAt)),
            '${l.agVersion(v.version)}${v.note == null ? '' : ' · ${v.note}'}',
          ],
      ],
    ),
    PdfHeading(l.acPdfFolderParties),
    PdfParagraph([for (final p in answers.parties) p.name].join(', ')),
    PdfHeading(l.acPdfFolderLedger),
    PdfParagraph(
      intBroken == null
          ? l.acReviewChainOk(journal.length)
          : l.acReviewChainBroken(intBroken),
    ),
    if (financial.isEmpty)
      PdfParagraph(l.acReviewPeriodEmpty)
    else
      _ledgerTable(l, money, answers, financial),
    PdfHeading(l.acPdfFolderMinutes),
    if (minutes.isEmpty)
      PdfParagraph(l.acPdfNone)
    else
      for (final m in minutes) ...[
        PdfParagraph(
          l.acPdfMinutesLine(
            formatDate(m.date),
            m.refId ?? '—',
            _short(ReviewMinutesNote.parse(m.note).chainHead),
          ),
        ),
        for (final o in ReviewMinutesNote.parse(m.note).objections.values)
          PdfParagraph(l.acPdfObjection(o)),
      ],
    PdfHeading(l.acPdfFolderIncidents),
    if (incidents.isEmpty)
      PdfParagraph(l.acPdfNone)
    else
      for (final e in incidents)
        PdfParagraph(
          l.acPdfIncidentLine(
            formatDate(e.date),
            _partyName(answers, e.partyId),
            DutyIncidentNote.parse(e.note).reason,
          ),
        ),
    PdfHeading(l.acPdfFolderClaims),
    PdfKeyValues([
      (l.acDisputeTopic, note.topic),
      (l.acDisputeClause, note.clause.isEmpty ? '—' : note.clause),
    ]),
    for (final c in dispute.claims)
      PdfParagraph(
        l.acPdfClaimLine(
          _partyName(answers, c.partyId),
          DisputeNote.parse(c.note).claim,
        ),
      ),
    PdfParagraph(
      l.acPdfClaimLine(
        _partyName(answers, dispute.root.partyId),
        note.claim,
      ),
    ),
    PdfHeading(l.acPdfFolderDecision),
    if (decisions.isEmpty)
      PdfParagraph(l.acPdfNoDecision)
    else
      for (final d in decisions)
        PdfParagraph(l.acPdfDecisionLine(formatDate(d.date), d.note ?? '')),
    PdfHeading(l.acPdfFolderIntegrity),
    PdfKeyValues([(l.agChainHead, _short(head))]),
    PdfNote(l.agPdfNote),
  ];
}

Future<Uint8List> buildReviewMinutesPdf({
  required PdfFonts fonts,
  required AppLocalizations l,
  required String Function(Money) money,
  required Agreement agreement,
  required List<JournalEntry> journal,
  required AgreementAnswers answers,
  required JournalEntry minutes,
  required String footer,
}) => BarakaPdf.build(
  fonts: fonts,
  title: l.acReviewTitle,
  subtitle: '${agreement.title} · ${minutes.refId ?? ''}',
  footer: footer,
  blocks: reviewMinutesBlocks(
    l: l,
    money: money,
    answers: answers,
    journal: journal,
    minutes: minutes,
  ),
);

Future<Uint8List> buildArbiterFolderPdf({
  required PdfFonts fonts,
  required AppLocalizations l,
  required String Function(Money) money,
  required AgreementView view,
  required DisputeCase dispute,
  required List<JournalEntry> journal,
  required String footer,
}) => BarakaPdf.build(
  fonts: fonts,
  title: l.acDisputePdf,
  subtitle: view.agreement.title,
  footer: footer,
  blocks: arbiterFolderBlocks(
    l: l,
    money: money,
    view: view,
    dispute: dispute,
    journal: journal,
  ),
);
