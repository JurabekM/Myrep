import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_actions.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_pdf.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Oylik ochiq hisob ko'rigi sessiyasi (SPEC 2F.5): davr yozuvlari, zanjir
/// tekshiruvi, hodisalar; har tomon «roziman» yoki «e'tiroz» deydi; keyin
/// bayonnoma (PDF).
class ReviewScreen extends ConsumerWidget {
  const ReviewScreen({required this.agreementId, super.key});

  final String agreementId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final view = ref.watch(accountabilityViewProvider(agreementId));
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.acReviewScreenTitle),
        actions: [
          if (view.valueOrNull case final v? when v.minutes.isNotEmpty)
            IconButton(
              key: const Key('ac-minutes-pdf'),
              tooltip: l10n.acReviewMinutesShare,
              icon: const Icon(Icons.picture_as_pdf_outlined),
              onPressed: () => _sharePdf(context, ref, v),
            ),
        ],
      ),
      body: switch (view) {
        AsyncData(:final value?) => _body(context, ref, value),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Future<bool> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function(AccountabilityService s) action,
  ) => runAccountability(context, ref, agreementId, action);

  Future<void> _ack(
    BuildContext context,
    WidgetRef ref,
    AccountabilityView v,
    AgreementParty party,
    ReviewVerdict verdict,
  ) async {
    final reviewId = v.review.openReview!.id;
    String? objection;
    if (verdict == ReviewVerdict.object) {
      objection = await _askObjection(context);
      if (objection == null || !context.mounted) return;
    }
    await _run(
      context,
      ref,
      (s) => s.acknowledge(
        v.agreement,
        reviewId: reviewId,
        partyId: party.id,
        verdict: verdict,
        objection: objection,
      ),
    );
  }

  Future<String?> _askObjection(BuildContext context) => showDialog<String>(
    context: context,
    builder: (_) => const _ObjectionDialog(),
  );

  Future<void> _complete(
    BuildContext context,
    WidgetRef ref,
    AccountabilityView v,
  ) async {
    final reviewId = v.review.openReview!.id;
    final done = await _run(context, ref, (s) async {
      await s.completeReview(v.agreement, reviewId: reviewId);
    });
    if (!done || !context.mounted) return;
    await recordTaskEvent(ref, TaskTrigger.accountReviewCompleted);
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(context.l10n.acReviewDone)));
    }
  }

  Future<void> _sharePdf(
    BuildContext context,
    WidgetRef ref,
    AccountabilityView v,
  ) async {
    final l10n = context.l10n;
    final money = context.money;
    final messenger = ScaffoldMessenger.of(context);
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    try {
      final minutes = v.minutes.last;
      final bytes = await buildReviewMinutesPdf(
        fonts: await PdfFonts.load(rootBundle),
        l: l10n,
        money: money,
        agreement: v.agreement,
        journal: v.base.journal,
        answers: v.base.answers,
        minutes: minutes,
        footer: '${l10n.appTitle} · ${formatDate(today)}',
      );
      await sharePdfFile(bytes, 'koriq-bayonnoma.pdf', v.agreement.title);
    } on Object {
      AppLog.event('review_pdf_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  Widget _body(BuildContext context, WidgetRef ref, AccountabilityView v) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final open = v.review.openReview;
    final answers = v.base.answers;
    final chain = verifyChain(v.base.journal);
    final income = _sum(v.periodEntries, JournalKind.ventureIncome);
    final expense = _sum(v.periodEntries, JournalKind.ventureExpense);
    final allAcked =
        open != null &&
        answers.parties.isNotEmpty &&
        answers.parties.every((p) => v.acks.containsKey(p.id));
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        Text(v.agreement.title, style: theme.textTheme.titleLarge),
        const SizedBox(height: 4),
        Text(
          open == null
              ? (v.minutes.isEmpty ? '' : l10n.acReviewLockedNote)
              : l10n.acReviewCutoff(formatDate(open.cutoff)),
          key: const Key('ac-cutoff'),
        ),
        const SizedBox(height: 8),
        Text(
          chain == null
              ? l10n.acReviewChainOk(v.base.journal.length)
              : l10n.acReviewChainBroken(chain),
          key: const Key('ac-chain'),
          style: TextStyle(
            color: chain == null ? null : theme.colorScheme.error,
          ),
        ),
        const SizedBox(height: 16),
        Text(l10n.acReviewPeriodTitle, style: theme.textTheme.titleMedium),
        if (v.periodEntries.isEmpty)
          Text(l10n.acReviewPeriodEmpty)
        else ...[
          Text(
            l10n.acReviewTotals(money(income), money(expense)),
            key: const Key('ac-totals'),
          ),
          for (final e in v.periodEntries)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(
                [
                  agJournalKind(l10n, e.kind),
                  if (e.amount != null) money(e.amount!),
                ].join(' · '),
              ),
              subtitle: Text(
                [
                  formatDate(e.date),
                  if (e.partyId != null) answers.party(e.partyId!)?.name,
                  if (e.note != null) e.note,
                ].whereType<String>().join(' · '),
              ),
            ),
        ],
        const SizedBox(height: 16),
        Text(l10n.acReviewIncidents, style: theme.textTheme.titleMedium),
        if (v.incidents.isEmpty)
          Text(l10n.acPdfNone)
        else
          for (final e in v.incidents)
            ListTile(
              key: Key('ac-incident-${e.meta.id}'),
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.report_outlined),
              title: Text(_incidentLine(l10n, answers, e)),
              subtitle: Text(formatDate(e.date)),
            ),
        const SizedBox(height: 16),
        Text(l10n.acReviewAcksTitle, style: theme.textTheme.titleMedium),
        for (final p in answers.parties) _partyRow(context, ref, v, p, open),
        const SizedBox(height: 16),
        if (open != null) ...[
          if (!allAcked)
            Text(l10n.acReviewWaiting, style: theme.textTheme.bodySmall),
          const SizedBox(height: 8),
          FilledButton(
            key: const Key('ac-review-complete'),
            onPressed: allAcked ? () => _complete(context, ref, v) : null,
            child: Text(l10n.acReviewComplete),
          ),
        ] else if (v.minutes.isNotEmpty)
          OutlinedButton.icon(
            key: const Key('ac-minutes-share'),
            icon: const Icon(Icons.picture_as_pdf_outlined),
            label: Text(l10n.acReviewMinutesShare),
            onPressed: () => _sharePdf(context, ref, v),
          ),
      ],
    );
  }

  Widget _partyRow(
    BuildContext context,
    WidgetRef ref,
    AccountabilityView v,
    AgreementParty p,
    OpenReview? open,
  ) {
    final l10n = context.l10n;
    final ack = v.acks[p.id];
    if (open == null) return const SizedBox.shrink();
    if (ack != null) {
      return ListTile(
        key: Key('ac-ack-${p.id}'),
        contentPadding: EdgeInsets.zero,
        leading: Icon(
          ack.verdict == ReviewVerdict.agree
              ? Icons.check_circle_outline
              : Icons.report_outlined,
        ),
        title: Text(p.name),
        subtitle: Text(
          ack.verdict == ReviewVerdict.agree
              ? l10n.acReviewVerdictAgree(p.name)
              : l10n.acReviewVerdictObject(p.name, ack.objection ?? ''),
        ),
      );
    }
    return ListTile(
      key: Key('ac-party-${p.id}'),
      contentPadding: EdgeInsets.zero,
      title: Text(p.name),
      subtitle: Wrap(
        spacing: 8,
        children: [
          FilledButton.tonal(
            key: Key('ac-ack-agree-${p.id}'),
            onPressed: () => _ack(context, ref, v, p, ReviewVerdict.agree),
            child: Text(l10n.acReviewAgree),
          ),
          OutlinedButton(
            key: Key('ac-ack-object-${p.id}'),
            onPressed: () => _ack(context, ref, v, p, ReviewVerdict.object),
            child: Text(l10n.acReviewObject),
          ),
        ],
      ),
    );
  }

  static String _incidentLine(
    AppLocalizations l,
    AgreementAnswers answers,
    JournalEntry e,
  ) {
    final n = DutyIncidentNote.parse(e.note);
    final party = e.partyId == null ? null : answers.party(e.partyId!)?.name;
    final body = n.fix.isEmpty
        ? l.acIncidentNoFix(n.reason)
        : l.acIncidentLine(n.reason, n.fix);
    return party == null ? body : '$party: $body';
  }

  static Money _sum(List<JournalEntry> entries, JournalKind kind) {
    final amounts = [
      for (final e in entries)
        if (e.kind == kind && e.amount != null) e.amount!,
    ];
    if (amounts.isEmpty) return const Money.zero(CurrencyCode.uzs);
    return Money.sum(amounts, amounts.first.currency);
  }
}

/// E'tiroz izohi. Kontrollerni o'zi yopadi — yopilish animatsiyasidan keyin
/// ishlatilmasin.
class _ObjectionDialog extends StatefulWidget {
  const _ObjectionDialog();

  @override
  State<_ObjectionDialog> createState() => _ObjectionDialogState();
}

class _ObjectionDialogState extends State<_ObjectionDialog> {
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.acReviewObjectTitle),
      content: TextField(
        key: const Key('ac-object-note'),
        controller: _note,
        autofocus: true,
        maxLines: 3,
        decoration: InputDecoration(labelText: l10n.acReviewObjectHint),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ac-object-save'),
          onPressed: () => Navigator.pop(context, _note.text.trim()),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
