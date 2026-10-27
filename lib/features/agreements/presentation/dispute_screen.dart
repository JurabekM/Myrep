import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_actions.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_pdf.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Nizo ekrani (SPEC 2F.8): tomonlarning talablari, hakam qarori va
/// «hakam uchun ish papkasi» (PDF).
class DisputeScreen extends ConsumerStatefulWidget {
  const DisputeScreen({
    required this.agreementId,
    required this.disputeId,
    super.key,
  });

  final String agreementId;
  final String disputeId;

  @override
  ConsumerState<DisputeScreen> createState() => _DisputeScreenState();
}

class _DisputeScreenState extends ConsumerState<DisputeScreen> {
  final _claim = TextEditingController();
  final _decision = TextEditingController();
  String? _party;

  @override
  void dispose() {
    _claim.dispose();
    _decision.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final view = ref.watch(accountabilityViewProvider(widget.agreementId));
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.acDisputeScreenTitle),
        actions: [
          if (view.valueOrNull case final v?)
            IconButton(
              key: const Key('ac-arbiter-pdf'),
              tooltip: l10n.acDisputePdf,
              icon: const Icon(Icons.picture_as_pdf_outlined),
              onPressed: () => _sharePdf(context, v),
            ),
        ],
      ),
      body: switch (view) {
        AsyncData(:final value?) => _body(context, value),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Future<void> _sharePdf(BuildContext context, AccountabilityView v) async {
    final dispute = _dispute(v);
    if (dispute == null) return;
    final l10n = context.l10n;
    final money = context.money;
    final messenger = ScaffoldMessenger.of(context);
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    try {
      final bytes = await buildArbiterFolderPdf(
        fonts: await PdfFonts.load(rootBundle),
        l: l10n,
        money: money,
        view: v.base,
        dispute: dispute,
        journal: v.base.journal,
        footer: '${l10n.appTitle} · ${formatDate(today)}',
      );
      await sharePdfFile(bytes, 'hakam-papkasi.pdf', v.agreement.title);
    } on Object {
      AppLog.event('arbiter_pdf_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  DisputeCase? _dispute(AccountabilityView v) {
    for (final d in v.disputes) {
      if (d.id == widget.disputeId) return d;
    }
    return null;
  }

  Future<void> _addClaim(
    BuildContext context,
    AccountabilityView v,
    String partyId,
  ) async {
    final ok = await runAccountability(
      context,
      ref,
      widget.agreementId,
      (s) => s.addDisputeClaim(
        v.agreement,
        disputeId: widget.disputeId,
        partyId: partyId,
        claim: _claim.text,
      ),
    );
    if (ok) _claim.clear();
  }

  Future<void> _decide(BuildContext context, AccountabilityView v) async {
    final ok = await runAccountability(
      context,
      ref,
      widget.agreementId,
      (s) => s.decideDispute(
        v.agreement,
        disputeId: widget.disputeId,
        decision: _decision.text,
      ),
    );
    if (ok) _decision.clear();
  }

  Widget _body(BuildContext context, AccountabilityView v) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final dispute = _dispute(v);
    if (dispute == null) return Center(child: Text(l10n.acDisputeNone));
    final answers = v.base.answers;
    final note = dispute.note;
    final open = dispute.isOpen;
    final decision = dispute.decision;
    final partyNames = {for (final p in answers.parties) p.id: p.name};
    _party ??= answers.parties.isEmpty ? null : answers.parties.first.id;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        Text(note.topic, style: theme.textTheme.titleLarge),
        const SizedBox(height: 4),
        Chip(
          key: const Key('ac-dispute-status'),
          label: Text(
            open ? l10n.acDisputeStatusOpen : l10n.acDisputeStatusDecided,
          ),
        ),
        if (note.clause.isNotEmpty)
          Text('${l10n.acDisputeClause}: ${note.clause}'),
        if (open) ...[
          const SizedBox(height: 8),
          Card(
            color: theme.colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(l10n.acDisputeInDispute),
            ),
          ),
        ],
        const SizedBox(height: 16),
        Text(l10n.acDisputeClaimsTitle, style: theme.textTheme.titleMedium),
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(partyNames[dispute.root.partyId] ?? '—'),
          subtitle: Text(note.claim),
        ),
        for (final c in dispute.claims)
          ListTile(
            key: Key('ac-claim-${c.meta.id}'),
            contentPadding: EdgeInsets.zero,
            title: Text(partyNames[c.partyId] ?? '—'),
            subtitle: Text(DisputeNote.parse(c.note).claim),
          ),
        if (open) ...[
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            key: const Key('ac-claim-party'),
            value: _party,
            decoration: InputDecoration(labelText: l10n.acDutyWho),
            items: [
              for (final p in answers.parties)
                DropdownMenuItem(value: p.id, child: Text(p.name)),
            ],
            onChanged: (id) => setState(() => _party = id),
          ),
          TextField(
            key: const Key('ac-claim-text'),
            controller: _claim,
            maxLines: 3,
            decoration: InputDecoration(labelText: l10n.acDisputeClaim),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            key: const Key('ac-claim-add'),
            onPressed: _party == null
                ? null
                : () => _addClaim(context, v, _party!),
            child: Text(l10n.acDisputeAddClaim),
          ),
        ],
        const SizedBox(height: 16),
        Text(l10n.acDisputeDecisionTitle, style: theme.textTheme.titleMedium),
        if (decision != null) ...[
          Text(decision.note ?? ''),
          const SizedBox(height: 4),
          Text(l10n.acDisputeDecidedNote),
        ] else ...[
          TextField(
            key: const Key('ac-decision-text'),
            controller: _decision,
            maxLines: 3,
            decoration: InputDecoration(labelText: l10n.acDisputeDecisionHint),
          ),
          const SizedBox(height: 8),
          FilledButton(
            key: const Key('ac-decide'),
            onPressed: () => _decide(context, v),
            child: Text(l10n.acDisputeDecide),
          ),
        ],
      ],
    );
  }
}
