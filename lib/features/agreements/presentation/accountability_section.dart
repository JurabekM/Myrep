import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/renewal_reminders.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_actions.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Kelishuv ekranidagi «hisob» bo'limi: vazifalar («bajara olmayapman»),
/// oylik ko'rik, nizolar va yillik yangilash (SPEC 2F.4, 2F.5, 2F.8, 2F.10).
class AccountabilitySection extends ConsumerWidget {
  const AccountabilitySection({required this.acc, super.key});

  final AccountabilityView acc;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final a = acc.agreement;
    final linked = a.source != null;
    final answers = acc.base.answers;
    final partyNames = {for (final p in answers.parties) p.id: p.name};
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 16),
        Text(l10n.acDutiesTitle, style: theme.textTheme.titleMedium),
        for (final d in answers.duties)
          ListTile(
            key: Key('ac-duty-${d.id}'),
            contentPadding: EdgeInsets.zero,
            title: Text(d.title),
            subtitle: Text(partyNames[d.ownerPartyId] ?? ''),
            trailing: TextButton(
              key: Key('ac-duty-report-${d.id}'),
              onPressed: () => _reportDuty(context, ref, d),
              child: Text(l10n.acDutyReport),
            ),
          ),
        if (acc.incidents.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(l10n.acIncidentsTitle, style: theme.textTheme.labelLarge),
          for (final e in acc.incidents)
            ListTile(
              key: Key('ac-incident-${e.meta.id}'),
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.report_outlined),
              title: Text(_incident(l10n, e, partyNames)),
              subtitle: Text(formatDate(e.date)),
            ),
        ],
        const SizedBox(height: 16),
        _ReviewCard(acc: acc),
        const SizedBox(height: 16),
        _DisputeCard(acc: acc),
        if (!linked) ...[
          const SizedBox(height: 16),
          _RenewalCard(acc: acc),
        ],
      ],
    );
  }

  static String _incident(
    AppLocalizations l,
    JournalEntry e,
    Map<String, String> names,
  ) {
    final n = DutyIncidentNote.parse(e.note);
    final party = e.partyId == null ? null : names[e.partyId];
    final body = n.fix.isEmpty
        ? l.acIncidentNoFix(n.reason)
        : l.acIncidentLine(n.reason, n.fix);
    return party == null ? body : '$party: $body';
  }

  Future<void> _reportDuty(
    BuildContext context,
    WidgetRef ref,
    AgreementDuty d,
  ) async {
    final l10n = context.l10n;
    final form = await showDialog<(String, String, String)>(
      context: context,
      builder: (_) => _DutyReportDialog(
        title: l10n.acDutyReportTitle,
        parties: acc.base.answers.parties,
        initialParty: d.ownerPartyId,
      ),
    );
    if (form == null || !context.mounted) return;
    final ok = await runAccountability(
      context,
      ref,
      acc.agreement.meta.id,
      (s) => s.reportDuty(
        acc.agreement,
        dutyId: d.id,
        partyId: form.$1,
        reason: form.$2,
        fix: form.$3,
      ),
    );
    if (ok && context.mounted) {
      // Shartnoma bandi darhol ko'rsatiladi: ayblov emas, kelishilgan qoida.
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l10n.acDutyClauseTitle),
          content: Text(
            l10n.acDutyClauseBody(
              d.breachClause.isEmpty ? d.title : d.breachClause,
            ),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: Text(l10n.ok),
            ),
          ],
        ),
      );
    }
  }
}

class _ReviewCard extends ConsumerWidget {
  const _ReviewCard({required this.acc});

  final AccountabilityView acc;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final id = acc.agreement.meta.id;
    final review = acc.review;
    final open = review.openReview;
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    return Card(
      key: const Key('ac-review-card'),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.acReviewTitle, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            if (open != null)
              Text(l10n.acReviewOpenInfo(formatDate(open.cutoff)))
            else ...[
              Text(
                l10n.acReviewNext(formatDate(review.dueOn)),
                key: const Key('ac-review-next'),
              ),
              if (review.isDue(today))
                Text(
                  l10n.acReviewDue,
                  style: TextStyle(color: theme.colorScheme.error),
                ),
            ],
            if (review.minutesCount > 0)
              Text(l10n.acReviewMinutesCount(review.minutesCount)),
            const SizedBox(height: 8),
            if (open != null)
              FilledButton(
                key: const Key('ac-review-continue'),
                onPressed: () => context.push(AppRoutes.agreementReview(id)),
                child: Text(l10n.acReviewContinue),
              )
            else
              FilledButton(
                key: const Key('ac-review-start'),
                onPressed: () async {
                  final ok = await runAccountability(
                    context,
                    ref,
                    id,
                    (s) async {
                      await s.openReview(acc.agreement);
                    },
                  );
                  if (ok && context.mounted) {
                    await context.push(AppRoutes.agreementReview(id));
                  }
                },
                child: Text(l10n.acReviewStart),
              ),
          ],
        ),
      ),
    );
  }
}

class _DisputeCard extends ConsumerWidget {
  const _DisputeCard({required this.acc});

  final AccountabilityView acc;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final id = acc.agreement.meta.id;
    final names = {for (final p in acc.base.answers.parties) p.id: p.name};
    return Card(
      key: const Key('ac-dispute-card'),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.acDisputesTitle, style: theme.textTheme.titleMedium),
            if (acc.disputes.isEmpty)
              Text(l10n.acDisputeNone)
            else
              for (final d in acc.disputes)
                ListTile(
                  key: Key('ac-dispute-${d.id}'),
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    d.isOpen
                        ? Icons.gavel_outlined
                        : Icons.check_circle_outline,
                  ),
                  title: Text(d.note.topic),
                  subtitle: Text(_disputeSubtitle(l10n, d, names)),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(
                    AppRoutes.agreementDispute(id, d.id),
                  ),
                ),
            const SizedBox(height: 8),
            OutlinedButton(
              key: const Key('ac-dispute-open'),
              onPressed: () => _open(context, ref),
              child: Text(l10n.acDisputeOpen),
            ),
          ],
        ),
      ),
    );
  }

  static String _disputeSubtitle(
    AppLocalizations l,
    DisputeCase d,
    Map<String, String> names,
  ) {
    final status = d.isOpen ? l.acDisputeStatusOpen : l.acDisputeStatusDecided;
    return '$status · ${names[d.root.partyId] ?? ''}';
  }

  Future<void> _open(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final form = await showDialog<(String, String, String, String)>(
      context: context,
      builder: (_) => _DisputeOpenDialog(
        title: l10n.acDisputeOpen,
        parties: acc.base.answers.parties,
      ),
    );
    if (form == null || !context.mounted) return;
    final id = acc.agreement.meta.id;
    String? disputeId;
    final ok = await runAccountability(context, ref, id, (s) async {
      disputeId = await s.openDispute(
        acc.agreement,
        partyId: form.$1,
        topic: form.$2,
        clause: form.$3,
        claim: form.$4,
      );
    });
    if (ok && disputeId != null && context.mounted) {
      await context.push(AppRoutes.agreementDispute(id, disputeId!));
    }
  }
}

class _RenewalCard extends ConsumerWidget {
  const _RenewalCard({required this.acc});

  final AccountabilityView acc;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final a = acc.agreement;
    final r = a.reviewDate;
    final pending = a.status == AgreementStatus.draft && a.currentVersion > 1;
    return Card(
      key: const Key('ac-renewal-card'),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.acRenewalTitle, style: theme.textTheme.titleMedium),
            if (r != null) Text(l10n.acRenewalDue(formatDate(r))),
            if (pending) Text(l10n.acRenewalNeedsSign),
            const SizedBox(height: 8),
            if (a.status == AgreementStatus.signed ||
                a.status == AgreementStatus.active)
              OutlinedButton(
                key: const Key('ag-renew-unchanged'),
                onPressed: () async {
                  final ok = await runAccountability(
                    context,
                    ref,
                    a.meta.id,
                    (s) async {
                      await s.renewUnchanged(a, note: l10n.agUnchangedNote);
                    },
                  );
                  if (ok) await syncAgreementRenewals(ref, l10n);
                },
                child: Text(l10n.acRenewalUnchanged),
              ),
          ],
        ),
      ),
    );
  }
}

class _DutyReportDialog extends StatefulWidget {
  const _DutyReportDialog({
    required this.title,
    required this.parties,
    required this.initialParty,
  });

  final String title;
  final List<AgreementParty> parties;
  final String? initialParty;

  @override
  State<_DutyReportDialog> createState() => _DutyReportDialogState();
}

class _DutyReportDialogState extends State<_DutyReportDialog> {
  final _reason = TextEditingController();
  final _fix = TextEditingController();
  late String? _party = widget.initialParty;

  @override
  void dispose() {
    _reason.dispose();
    _fix.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(widget.title),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              key: const Key('ac-duty-party'),
              value: _party,
              decoration: InputDecoration(labelText: l10n.acDutyWho),
              items: [
                for (final p in widget.parties)
                  DropdownMenuItem(value: p.id, child: Text(p.name)),
              ],
              onChanged: (id) => setState(() => _party = id),
            ),
            TextField(
              key: const Key('ac-duty-reason'),
              controller: _reason,
              decoration: InputDecoration(labelText: l10n.acDutyReason),
            ),
            TextField(
              key: const Key('ac-duty-fix'),
              controller: _fix,
              decoration: InputDecoration(labelText: l10n.acDutyFix),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ac-duty-save'),
          onPressed: _party == null
              ? null
              : () => Navigator.pop(context, (
                  _party!,
                  _reason.text.trim(),
                  _fix.text.trim(),
                )),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

class _DisputeOpenDialog extends StatefulWidget {
  const _DisputeOpenDialog({required this.title, required this.parties});

  final String title;
  final List<AgreementParty> parties;

  @override
  State<_DisputeOpenDialog> createState() => _DisputeOpenDialogState();
}

class _DisputeOpenDialogState extends State<_DisputeOpenDialog> {
  final _topic = TextEditingController();
  final _clause = TextEditingController();
  final _claim = TextEditingController();
  String? _party;

  @override
  void initState() {
    super.initState();
    _party = widget.parties.isEmpty ? null : widget.parties.first.id;
  }

  @override
  void dispose() {
    _topic.dispose();
    _clause.dispose();
    _claim.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(widget.title),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              key: const Key('ac-dispute-party'),
              value: _party,
              decoration: InputDecoration(labelText: l10n.acDutyWho),
              items: [
                for (final p in widget.parties)
                  DropdownMenuItem(value: p.id, child: Text(p.name)),
              ],
              onChanged: (id) => setState(() => _party = id),
            ),
            TextField(
              key: const Key('ac-dispute-topic'),
              controller: _topic,
              decoration: InputDecoration(labelText: l10n.acDisputeTopic),
            ),
            TextField(
              key: const Key('ac-dispute-clause'),
              controller: _clause,
              decoration: InputDecoration(labelText: l10n.acDisputeClause),
            ),
            TextField(
              key: const Key('ac-dispute-claim'),
              controller: _claim,
              maxLines: 3,
              decoration: InputDecoration(labelText: l10n.acDisputeClaim),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ac-dispute-save'),
          onPressed: _party == null
              ? null
              : () => Navigator.pop(context, (
                  _party!,
                  _topic.text.trim(),
                  _clause.text.trim(),
                  _claim.text.trim(),
                )),
          child: Text(l10n.acDisputeOpen),
        ),
      ],
    );
  }
}
