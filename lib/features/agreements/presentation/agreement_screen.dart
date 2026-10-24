import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/paged_list.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/presentation/accountability_section.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';
import 'package:baraka_daftari/features/agreements/presentation/question_editor.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/presentation/signature_pad.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';

/// Hujjatdan avtomatik to'ldiriladigan savollar (o'zgartirish — asl
/// hujjatda: sheriklik shartnomasi yoki qarz yozuvi).
Set<AgreementQuestion> agAutoQuestions(Agreement a) => switch ((
  a.type,
  a.source,
)) {
  (AgreementType.partnership, AgreementSource.partnership) => const {
    AgreementQuestion.parties,
    AgreementQuestion.contributions,
    AgreementQuestion.profitRule,
    AgreementQuestion.lossRule,
  },
  (AgreementType.loan, _) when a.source != null => const {
    AgreementQuestion.parties,
    AgreementQuestion.contributions,
    AgreementQuestion.duties,
    AgreementQuestion.profitRule,
    AgreementQuestion.lossRule,
  },
  _ => const {},
};

/// Savolning qisqa mazmuni (ro'yxatda).
String agSummary(
  AppLocalizations l,
  String Function(Money) money,
  AgreementView v,
  AgreementQuestion q,
) {
  final a = v.answers;
  final s = a.statusOf(q);
  if (s.state == QuestionState.notApplicable) {
    return l.agNaSummary(s.reason);
  }
  String name(String? id) => a.party(id ?? '')?.name ?? '—';
  final loan = v.agreement.type == AgreementType.loan;
  return switch (q) {
    AgreementQuestion.parties => a.parties.map((p) => p.name).join(', '),
    AgreementQuestion.contributions => [
      for (final c in a.contributions)
        '${name(c.partyId)}: ${_contribution(l, money, c)}',
    ].join('; '),
    AgreementQuestion.duties =>
      loan && v.agreement.source != null
          ? l.agLoanSchedule
          : [
              for (final d in a.duties) '${d.title} — ${name(d.ownerPartyId)}',
            ].join('; '),
    AgreementQuestion.profitRule =>
      loan
          ? l.agLoanNoInterest
          : [
              for (final e in a.profit.shares.entries)
                '${name(e.key)} ${percentLabel(e.value)} %',
              if (a.profit.text.isNotEmpty) a.profit.text,
            ].join(', '),
    AgreementQuestion.lossRule =>
      a.lossAuto != null ? agLossAuto(l, a.lossAuto!) : a.lossText,
    AgreementQuestion.custody =>
      a.custody.where.isEmpty
          ? ''
          : '${a.custody.where} · ${name(a.custody.keeperPartyId)} · '
                '${agReviewEvery(l, a.custody.reviewEveryDays)}',
    AgreementQuestion.exitClause => [
      a.exit.valuation,
      a.exit.payout,
    ].where((x) => x.isNotEmpty).join(' · '),
    AgreementQuestion.arbiter => a.arbiter?.name ?? '',
    AgreementQuestion.term =>
      a.term.reviewDate == null
          ? ''
          : l.agReviewOn(formatDate(a.term.reviewDate!)),
  };
}

String _contribution(
  AppLocalizations l,
  String Function(Money) money,
  AgreementContribution c,
) => c.amount == null ? agContributionKind(l, c.kind) : money(c.amount!);

/// Kelishuvlar ro'yxati (SPEC 2F). Kelishuvlar markazi — Vazifa 14A.
class AgreementsScreen extends ConsumerWidget {
  const AgreementsScreen({super.key});

  Future<void> _create(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final type = await showModalBottomSheet<Object>(
      context: context,
      builder: (context) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            for (final t in const [
              AgreementType.rent,
              AgreementType.service,
              AgreementType.family,
              AgreementType.other,
            ])
              ListTile(
                key: Key('ag-new-${t.name}'),
                leading: const Icon(Icons.history_edu_outlined),
                title: Text(agType(l10n, t)),
                onTap: () => Navigator.pop(context, t),
              ),
            const Divider(),
            ListTile(
              key: const Key('ag-new-oral'),
              leading: const Icon(Icons.mic_none_outlined),
              title: Text(l10n.agOralTitle),
              subtitle: Text(l10n.agOralHint),
              onTap: () => Navigator.pop(context, 'oral'),
            ),
          ],
        ),
      ),
    );
    if (type == null || !context.mounted) return;
    if (type == 'oral') {
      await context.push(AppRoutes.agreementOral);
      ref.invalidate(agreementsProvider);
      return;
    }
    final draft = await showDialog<_NewDraft>(
      context: context,
      builder: (_) => _NewAgreementDialog(type: type as AgreementType),
    );
    if (draft == null || !context.mounted) return;
    try {
      final s = await ref.read(agreementServiceProvider.future);
      final a = await s.create(
        type: draft.type,
        title: draft.title,
        parties: [
          AgreementParty(id: 'p1', name: draft.me, isMe: true),
          AgreementParty(id: 'p2', name: draft.other),
        ],
      );
      ref
        ..invalidate(agreementsProvider)
        ..invalidate(agreementCenterProvider);
      if (draft.type == AgreementType.family) {
        await recordTaskEvent(ref, TaskTrigger.familyAgreementCreated);
      }
      if (context.mounted) await context.push(AppRoutes.agreement(a.meta.id));
    } on DomainRuleException catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(agError(l10n, e.code))));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final list = ref.watch(agreementCenterProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.agTitle)),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('ag-new'),
        icon: const Icon(Icons.add),
        label: Text(l10n.agNew),
        onPressed: () => _create(context, ref),
      ),
      body: switch (list) {
        AsyncData(:final value) when value.isEmpty => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(l10n.agEmpty, textAlign: TextAlign.center),
          ),
        ),
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.agIntro),
            const SizedBox(height: 8),
            PagedList(
              count: value.length,
              itemBuilder: (context, i) {
                final row = value[i];
                final a = row.agreement;
                final head =
                    '${agType(l10n, a.type)} · ${agStatus(l10n, a.status)}'
                    '${a.oral ? ' · ${l10n.agOralBadge}' : ''}';
                return Card(
                  child: ListTile(
                    key: Key('ag-item-${a.meta.id}'),
                    leading: const Icon(Icons.history_edu_outlined),
                    title: Text(a.title),
                    subtitle: Text(
                      [
                        head,
                        if (row.review.openReview == null)
                          l10n.acCenterNextReview(formatDate(row.review.dueOn)),
                        if (row.incidents.isNotEmpty)
                          l10n.acCenterOpenIncidents(row.incidents.length),
                        if (row.openDisputes.isNotEmpty)
                          l10n.acCenterDisputes(row.openDisputes.length),
                      ].join('\n'),
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () async {
                      await context.push(AppRoutes.agreement(a.meta.id));
                      ref
                        ..invalidate(agreementsProvider)
                        ..invalidate(agreementCenterProvider);
                    },
                  ),
                );
              },
            ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

typedef _NewDraft = ({
  AgreementType type,
  String title,
  String me,
  String other,
  _FamilyTemplate? template,
});

/// Oilaviy kelishuv shablonlari (SPEC 2F.10). Matn va ohang — ARB'dan.
enum _FamilyTemplate { chores, money, havas, council }

String _familyTitle(AppLocalizations l, _FamilyTemplate t) => switch (t) {
  _FamilyTemplate.chores => l.agTplChores,
  _FamilyTemplate.money => l.agTplMoney,
  _FamilyTemplate.havas => l.agTplHavas,
  _FamilyTemplate.council => l.agTplCouncil,
};

String _familyHint(AppLocalizations l, _FamilyTemplate t) => switch (t) {
  _FamilyTemplate.chores => l.agTplChoresHint,
  _FamilyTemplate.money => l.agTplMoneyHint,
  _FamilyTemplate.havas => l.agTplHavasHint,
  _FamilyTemplate.council => l.agTplCouncilHint,
};

class _NewAgreementDialog extends ConsumerStatefulWidget {
  const _NewAgreementDialog({required this.type});

  final AgreementType type;

  @override
  ConsumerState<_NewAgreementDialog> createState() =>
      _NewAgreementDialogState();
}

class _NewAgreementDialogState extends ConsumerState<_NewAgreementDialog> {
  final _title = TextEditingController();
  final _me = TextEditingController();
  final _other = TextEditingController();
  _FamilyTemplate? _template;

  @override
  void dispose() {
    _title.dispose();
    _me.dispose();
    _other.dispose();
    super.dispose();
  }

  bool get _ok =>
      _title.text.trim().isNotEmpty &&
      _me.text.trim().isNotEmpty &&
      _other.text.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final tpl = _template;
    return AlertDialog(
      title: Text(agType(l10n, widget.type)),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.type == AgreementType.family) ...[
              Text(l10n.agFamilyHint),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final t in _FamilyTemplate.values)
                    ChoiceChip(
                      key: Key('ag-family-${t.name}'),
                      label: Text(_familyTitle(l10n, t)),
                      selected: _template == t,
                      onSelected: (_) => setState(() {
                        _template = t;
                        if (_title.text.trim().isEmpty) {
                          _title.text = _familyTitle(l10n, t);
                        }
                      }),
                    ),
                ],
              ),
              if (tpl != null) Text(_familyHint(l10n, tpl)),
              const SizedBox(height: 8),
            ],
            TextField(
              key: const Key('ag-new-title'),
              controller: _title,
              decoration: InputDecoration(labelText: l10n.agFieldTitle),
              onChanged: (_) => setState(() {}),
            ),
            TextField(
              key: const Key('ag-new-me'),
              controller: _me,
              decoration: InputDecoration(labelText: l10n.agFieldMe),
              onChanged: (_) => setState(() {}),
            ),
            TextField(
              key: const Key('ag-new-other'),
              controller: _other,
              decoration: InputDecoration(labelText: l10n.agFieldOther),
              onChanged: (_) => setState(() {}),
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
          key: const Key('ag-new-ok'),
          onPressed: _ok
              ? () => Navigator.pop<_NewDraft>(context, (
                  type: widget.type,
                  title: _title.text.trim(),
                  me: _me.text.trim(),
                  other: _other.text.trim(),
                  template: _template,
                ))
              : null,
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

/// Modul ekranlarida (tilxat, sheriklik) — «Kelishuv: N / 9» kartasi.
class AgreementLinkCard extends ConsumerWidget {
  const AgreementLinkCard({
    required this.source,
    required this.sourceId,
    super.key,
  });

  final AgreementSource source;
  final String sourceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final v = ref
        .watch(agreementBySourceProvider(source, sourceId))
        .valueOrNull;
    if (v == null) return const SizedBox.shrink();
    final c = v.completeness;
    final ready = v.canSign;
    return Card(
      key: const Key('ag-link-card'),
      color: ready ? null : theme.colorScheme.tertiaryContainer,
      child: ListTile(
        leading: const Icon(Icons.history_edu_outlined),
        title: Text(l10n.agProgress(c.answered)),
        subtitle: Text(
          v.agreement.legacy && !c.complete
              ? l10n.agLegacyHint
              : ready
              ? l10n.agReadyHint
              : l10n.agSignLocked,
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () async {
          await context.push(AppRoutes.agreement(v.agreement.meta.id));
          ref.invalidate(agreementBySourceProvider(source, sourceId));
        },
      ),
    );
  }
}

/// Kelishuv (9 savol, to'liqlik, imzolar, jurnal, PDF).
class AgreementScreen extends ConsumerWidget {
  const AgreementScreen({required this.id, super.key});

  final String id;

  void _refresh(WidgetRef ref, AgreementView v) {
    ref
      ..invalidate(agreementViewProvider(id))
      ..invalidate(agreementsProvider);
    final s = v.agreement.source;
    final sid = v.agreement.sourceId;
    if (s != null && sid != null) {
      ref.invalidate(agreementBySourceProvider(s, sid));
    }
  }

  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    AgreementView v,
    Future<void> Function(AgreementService s) action,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await action(await ref.read(agreementServiceProvider.future));
    } on DomainRuleException catch (e) {
      AppLog.event('agreement_rejected_${e.code}');
      messenger.showSnackBar(SnackBar(content: Text(agError(l10n, e.code))));
    } on Object {
      AppLog.event('agreement_action_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
    _refresh(ref, v);
  }

  /// Uy xo'jaligining asosiy valyutasi: summalar shu valyutada kiritiladi.
  Future<CurrencyCode> _baseCurrency(WidgetRef ref) async =>
      (await (await ref.read(
        householdServiceProvider.future,
      )).household()).baseCurrency;

  Future<void> _edit(
    BuildContext context,
    WidgetRef ref,
    AgreementView v,
    AgreementQuestion q,
  ) async {
    final l10n = context.l10n;
    if (agAutoQuestions(v.agreement).contains(q)) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.agAutoHint)));
      return;
    }
    if (!v.editable) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.agErrSigned)));
      return;
    }
    final currency = await _baseCurrency(ref);
    if (!context.mounted) return;
    final next = await editQuestion(
      context,
      type: v.agreement.type,
      question: q,
      answers: v.answers,
      currency: currency,
    );
    if (next == null || !context.mounted) return;
    await _run(context, ref, v, (s) => s.saveAnswers(v.agreement, next));
  }

  Future<void> _sign(
    BuildContext context,
    WidgetRef ref,
    AgreementView v,
    LoanSigner signer,
  ) async {
    final result = await showSignDialog(
      context,
      role: context.l10n.signerRole(signer.role),
      name: signer.name,
    );
    if (result == null || !context.mounted) return;
    var signed = false;
    await _run(context, ref, v, (s) async {
      final after = await s.sign(v.agreement, signer, result.$1, result.$2);
      signed =
          after.agreement.status == AgreementStatus.signed &&
          v.agreement.status == AgreementStatus.draft;
    });
    if (signed) await recordTaskEvent(ref, TaskTrigger.agreementSigned);
  }

  Future<void> _sharePdf(
    BuildContext context,
    WidgetRef ref,
    AgreementView v,
  ) async {
    final l10n = context.l10n;
    final money = context.money;
    final messenger = ScaffoldMessenger.of(context);
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    final a = v.agreement;
    try {
      final bytes = await BarakaPdf.build(
        fonts: await PdfFonts.load(rootBundle),
        title: '${agType(l10n, a.type)}: ${a.title}',
        subtitle: l10n.agPdfSubtitle(
          a.currentVersion,
          formatDate(a.effectiveFrom),
        ),
        footer: '${l10n.appTitle} · ${formatDate(today)}',
        blocks: [
          PdfParagraph(l10n.agPdfIntro),
          for (final q in AgreementQuestion.values) ...[
            PdfHeading('${q.number}. ${agQuestion(l10n, q)}'),
            PdfParagraph(
              _orDash(agSummary(l10n, money, v, q)),
            ),
            if (q == AgreementQuestion.duties)
              for (final d in v.answers.duties)
                PdfKeyValues([(d.title, d.breachClause)]),
          ],
          if (v.current.note != null) PdfNote(v.current.note!),
          if (v.journal.isNotEmpty)
            PdfKeyValues([
              (l10n.agJournal, '${v.journal.length}'),
              (l10n.agChainHead, v.journal.last.hash.substring(0, 16)),
            ]),
          PdfNote(l10n.agPdfNote),
          PdfHeading(l10n.receiptPdfSignatures),
          PdfSignatures([
            for (final s in v.signers)
              PdfSignature(
                role: l10n.signerRole(s.role),
                name: s.name,
                image: s.signaturePng == null
                    ? null
                    : Uint8List.fromList(s.signaturePng!),
                signedAt: s.signedAt == null
                    ? null
                    : formatDate(Tashkent.dateOf(s.signedAt!)),
              ),
          ]),
        ],
      );
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile.fromData(
              bytes,
              mimeType: 'application/pdf',
              name: 'kelishuv.pdf',
            ),
          ],
          fileNameOverrides: const ['kelishuv.pdf'],
          subject: a.title,
        ),
      );
    } on Object {
      AppLog.event('agreement_pdf_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  static String _orDash(String s) => s.trim().isEmpty ? '—' : s;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final view = ref.watch(agreementViewProvider(id));
    final acc = ref.watch(accountabilityViewProvider(id)).valueOrNull;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.agScreenTitle),
        actions: [
          if (view.valueOrNull case final v?)
            IconButton(
              key: const Key('ag-pdf'),
              tooltip: l10n.agPdfShare,
              icon: const Icon(Icons.picture_as_pdf_outlined),
              onPressed: () => _sharePdf(context, ref, v),
            ),
        ],
      ),
      body: switch (view) {
        AsyncData(:final value?) => _body(context, ref, value, acc),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  Widget _body(
    BuildContext context,
    WidgetRef ref,
    AgreementView v,
    AccountabilityView? acc,
  ) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final a = v.agreement;
    final c = v.completeness;
    final auto = agAutoQuestions(a);
    final linked = a.source != null;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        Text(a.title, style: theme.textTheme.titleLarge),
        Wrap(
          spacing: 8,
          children: [
            Chip(label: Text(agType(l10n, a.type))),
            Chip(
              key: const Key('ag-status'),
              label: Text(agStatus(l10n, a.status)),
            ),
            Chip(label: Text(l10n.agVersion(a.currentVersion))),
            if (a.oral) Chip(label: Text(l10n.agOralBadge)),
          ],
        ),
        if (a.oral) Text(l10n.agEffectiveFrom(formatDate(a.effectiveFrom))),
        if (a.legacy)
          Card(
            color: theme.colorScheme.surfaceContainerHigh,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(l10n.agLegacyHint),
            ),
          ),
        const SizedBox(height: 8),
        Text(
          l10n.agProgress(c.answered),
          key: const Key('ag-progress'),
          style: theme.textTheme.titleMedium,
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(value: c.answered / 9),
        const SizedBox(height: 8),
        Card(
          color: theme.colorScheme.secondaryContainer,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Text(l10n.agAdvisorTip),
          ),
        ),
        for (final w in c.warnings)
          Text(
            agIssue(l10n, w.code),
            style: TextStyle(color: theme.colorScheme.tertiary),
          ),
        for (final q in AgreementQuestion.values)
          _questionTile(context, ref, v, q, auto.contains(q), money),
        const SizedBox(height: 16),
        Text(l10n.agSignatures, style: theme.textTheme.titleMedium),
        if (!v.canSign)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(
              l10n.agSignLocked,
              key: const Key('ag-sign-locked'),
              style: TextStyle(color: theme.colorScheme.error),
            ),
          )
        else if (a.type == AgreementType.partnership && linked)
          ListTile(
            key: const Key('ag-open-partnership'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.agSignInPartnership),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRoutes.partnership(a.sourceId!)),
          )
        else if (v.signers.isEmpty)
          FilledButton(
            key: const Key('ag-prepare-sign'),
            onPressed: () => _run(context, ref, v, (s) => s.prepareSigning(a)),
            child: Text(l10n.agPrepareSign),
          )
        else
          for (final s in v.signers)
            ListTile(
              key: Key('ag-signer-${s.meta.id}'),
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                s.isSigned ? Icons.check_circle : Icons.draw_outlined,
              ),
              title: Text(s.name),
              subtitle: Text(context.l10n.signerRole(s.role)),
              trailing: s.isSigned
                  ? null
                  : TextButton(
                      key: Key('ag-sign-${s.meta.id}'),
                      onPressed: () => _sign(context, ref, v, s),
                      child: Text(l10n.signAction),
                    ),
            ),
        if (!linked && a.status == AgreementStatus.signed)
          FilledButton(
            key: const Key('ag-activate'),
            onPressed: () => _run(context, ref, v, (s) => s.activate(a)),
            child: Text(l10n.agActivate),
          ),
        if (!linked &&
            (a.status == AgreementStatus.signed ||
                a.status == AgreementStatus.active)) ...[
          const SizedBox(height: 8),
          OutlinedButton(
            key: const Key('ag-new-version'),
            onPressed: () => _run(context, ref, v, (s) => s.newVersion(a)),
            child: Text(l10n.agNewVersion),
          ),
        ],
        if (acc != null) AccountabilitySection(acc: acc),
        const SizedBox(height: 16),
        Text(l10n.agJournal, style: theme.textTheme.titleMedium),
        Text(
          v.brokenAt == null
              ? l10n.agChainOk(v.journal.length)
              : l10n.agChainBroken(v.brokenAt!),
          key: const Key('ag-chain'),
          style: TextStyle(
            color: v.brokenAt == null ? null : theme.colorScheme.error,
          ),
        ),
        PagedList(
          count: v.journal.length,
          itemBuilder: (context, i) {
            final e = v.journal[v.journal.length - 1 - i];
            return ListTile(
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
                  if (e.partyId != null) v.answers.party(e.partyId!)?.name,
                  if (e.note != null) e.note,
                  '#${e.seq} ${e.hash.substring(0, 8)}',
                ].whereType<String>().join(' · '),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _questionTile(
    BuildContext context,
    WidgetRef ref,
    AgreementView v,
    AgreementQuestion q,
    bool auto,
    String Function(Money) money,
  ) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final c = v.completeness;
    final errors = [
      for (final e in c.errors)
        if (e.question == q) agIssue(l10n, e.code),
    ];
    final done = c.isAnswered(q);
    final summary = agSummary(l10n, money, v, q);
    return Card(
      child: ListTile(
        key: Key('ag-q-${q.number}'),
        leading: CircleAvatar(
          backgroundColor: done
              ? theme.colorScheme.primaryContainer
              : theme.colorScheme.surfaceContainerHigh,
          child: Text('${q.number}'),
        ),
        title: Text(agQuestion(l10n, q)),
        subtitle: Text(
          [
            if (errors.isNotEmpty) errors.join(' · '),
            if (summary.trim().isNotEmpty)
              summary
            else if (!done)
              l10n.agNeedsAnswer,
            if (auto) l10n.agAutoBadge,
          ].join('\n'),
          style: errors.isEmpty
              ? null
              : TextStyle(color: theme.colorScheme.error),
        ),
        trailing: Icon(
          done ? Icons.check_circle : Icons.radio_button_unchecked,
          color: done ? theme.colorScheme.primary : null,
        ),
        onTap: () => _edit(context, ref, v, q),
      ),
    );
  }
}

/// Og'zaki kelishuvni yozib olish ustasi (SPEC 2F.9).
class OralAgreementScreen extends ConsumerStatefulWidget {
  const OralAgreementScreen({super.key});

  @override
  ConsumerState<OralAgreementScreen> createState() =>
      _OralAgreementScreenState();
}

class _OralAgreementScreenState extends ConsumerState<OralAgreementScreen> {
  AgreementType _type = AgreementType.partnership;
  final _title = TextEditingController();
  final _me = TextEditingController();
  final _other = TextEditingController();
  final _note = TextEditingController();
  LocalDate? _from;
  Money? _mine;
  Money? _theirs;
  var _busy = false;

  @override
  void dispose() {
    _title.dispose();
    _me.dispose();
    _other.dispose();
    _note.dispose();
    super.dispose();
  }

  bool get _ok =>
      _title.text.trim().isNotEmpty &&
      _me.text.trim().isNotEmpty &&
      _other.text.trim().isNotEmpty &&
      _from != null &&
      !_busy;

  Future<void> _save() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    setState(() => _busy = true);
    try {
      final s = await ref.read(agreementServiceProvider.future);
      final a = await s.recordOral(
        type: _type,
        title: _title.text.trim(),
        parties: [
          AgreementParty(id: 'p1', name: _me.text.trim(), isMe: true),
          AgreementParty(id: 'p2', name: _other.text.trim()),
        ],
        effectiveFrom: _from!,
        opening: [
          if (_mine case final m? when !m.isZero)
            OpeningLine(partyId: 'p1', amount: m),
          if (_theirs case final m? when !m.isZero)
            OpeningLine(partyId: 'p2', amount: m),
        ],
        openingNote: _note.text.trim().isEmpty ? null : _note.text.trim(),
      );
      await recordTaskEvent(ref, TaskTrigger.oralAgreementRecorded);
      ref.invalidate(agreementsProvider);
      unawaited(router.pushReplacement(AppRoutes.agreement(a.meta.id)));
    } on DomainRuleException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(agError(l10n, e.code))));
      if (mounted) setState(() => _busy = false);
    } on Object {
      AppLog.event('oral_agreement_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _amount(bool mine) async {
    final currency = (await (await ref.read(
      householdServiceProvider.future,
    )).household()).baseCurrency;
    if (!mounted) return;
    final m = await showAmountSheet(
      context,
      currency: currency,
      title: mine ? context.l10n.agOralMine : context.l10n.agOralTheirs,
      initial: mine ? _mine : _theirs,
    );
    if (m == null) return;
    setState(() => mine ? _mine = m : _theirs = m);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.agOralTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(l10n.agOralIntro),
          const SizedBox(height: 12),
          DropdownButtonFormField<AgreementType>(
            key: const Key('oral-type'),
            value: _type,
            decoration: InputDecoration(labelText: l10n.agFieldType),
            items: [
              for (final t in AgreementType.values)
                DropdownMenuItem(value: t, child: Text(agType(l10n, t))),
            ],
            onChanged: (t) => setState(() => _type = t ?? _type),
          ),
          TextField(
            key: const Key('oral-title'),
            controller: _title,
            decoration: InputDecoration(labelText: l10n.agFieldTitle),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('oral-me'),
            controller: _me,
            decoration: InputDecoration(labelText: l10n.agFieldMe),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('oral-other'),
            controller: _other,
            decoration: InputDecoration(labelText: l10n.agFieldOther),
            onChanged: (_) => setState(() {}),
          ),
          ListTile(
            key: const Key('oral-from'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.agOralSince),
            subtitle: Text(_from == null ? '—' : formatDate(_from!)),
            trailing: const Icon(Icons.event),
            onTap: () async {
              final now = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
              final picked = await showDatePicker(
                context: context,
                initialDate: DateTime(now.year, now.month, now.day),
                firstDate: DateTime(now.year - 30),
                lastDate: DateTime(now.year, now.month, now.day),
              );
              if (picked == null) return;
              setState(
                () => _from = LocalDate(picked.year, picked.month, picked.day),
              );
            },
          ),
          const Divider(),
          Text(
            l10n.agOralOpening,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(l10n.agOralOpeningHint),
          ListTile(
            key: const Key('oral-mine'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.agOralMine),
            subtitle: Text(_mine == null ? '—' : money(_mine!)),
            onTap: () => _amount(true),
          ),
          ListTile(
            key: const Key('oral-theirs'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.agOralTheirs),
            subtitle: Text(_theirs == null ? '—' : money(_theirs!)),
            onTap: () => _amount(false),
          ),
          TextField(
            key: const Key('oral-note'),
            controller: _note,
            maxLines: 3,
            decoration: InputDecoration(labelText: l10n.agOralNote),
          ),
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('oral-save'),
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(52),
            ),
            onPressed: _ok ? _save : null,
            child: Text(l10n.agOralSave),
          ),
        ],
      ),
    );
  }
}
