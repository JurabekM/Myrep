import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_screen.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/presentation/signature_pad.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/presentation/member_pin_prompt.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_contract_pdf.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnership_wizard_screen.dart';
import 'package:baraka_daftari/features/vault/data/vault_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';

/// Bitta sheriklik (SPEC 2E.1, 2E.2, 2E.6).
class PartnershipScreen extends ConsumerWidget {
  const PartnershipScreen({required this.id, super.key});

  final String id;

  void _refresh(WidgetRef ref) {
    ref
      ..invalidate(partnershipViewProvider(id))
      ..invalidate(partnershipsProvider);
    refreshMoneyViews(ref);
  }

  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function(PartnershipService s) action, {
    String? success,
  }) async {
    final messenger = ScaffoldMessenger.of(context);
    final l10n = context.l10n;
    final errorText = l10n.genericError;
    String message(String code) => switch (code) {
      PartnershipService.errGateClosed => l10n.pnGateClosed,
      PartnershipService.errContractUnsigned => l10n.pnSignFirst,
      PartnershipService.errNotDebtAck => l10n.pnNotDebtTitle,
      PartnershipService.errConsentRequired => l10n.pnConsentTitle,
      PartnershipService.errAgreementIncomplete => l10n.agSignLocked,
      PartnershipService.errAlreadySigned => l10n.pnAlreadySigned,
      _ => partnershipError(context, code),
    };
    try {
      await action(await ref.read(partnershipServiceProvider.future));
      if (success != null) {
        messenger.showSnackBar(SnackBar(content: Text(success)));
      }
    } on DomainRuleException catch (e) {
      AppLog.event('partnership_rejected_${e.code}');
      messenger.showSnackBar(SnackBar(content: Text(message(e.code))));
    } on Object {
      AppLog.event('partnership_action_failed');
      messenger.showSnackBar(SnackBar(content: Text(errorText)));
    }
    _refresh(ref);
  }

  Future<void> _sign(
    BuildContext context,
    WidgetRef ref,
    PartnershipView v,
    LoanSigner s,
  ) async {
    final result = await showSignDialog(
      context,
      role: context.l10n.signerRole(s.role),
      name: s.name,
    );
    if (result == null || !context.mounted) return;
    var signed = false;
    await _run(context, ref, (x) async {
      final after = await x.sign(v.partnership, s, result.$1, result.$2);
      signed =
          after.partnership.status == PartnershipStatus.signed &&
          v.partnership.status == PartnershipStatus.draft;
    });
    if (signed) await recordTaskEvent(ref, TaskTrigger.agreementSigned);
  }

  Future<void> _amend(
    BuildContext context,
    WidgetRef ref,
    PartnershipView v,
  ) async {
    final l10n = context.l10n;
    final text = await showTextPrompt(
      context,
      title: l10n.pnAmend,
      label: l10n.pnAmendTerm,
      fieldKey: const Key('pn-amend-term'),
      okKey: const Key('pn-amend-ok'),
      initial: '${v.partnership.termMonths}',
      keyboardType: TextInputType.number,
    );
    final months = int.tryParse(text?.trim() ?? '');
    if (months == null || !context.mounted) return;
    await _run(context, ref, (s) => s.amend(v.partnership, termMonths: months));
  }

  Future<void> _activate(
    BuildContext context,
    WidgetRef ref,
    PartnershipView v,
    bool gateOpen,
  ) async {
    final l10n = context.l10n;
    var bypass = false;
    if (v.meProvidesCapital && !gateOpen) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l10n.pnGateTitle),
          content: Text(l10n.pnGateClosed),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              key: const Key('pn-gate-bypass'),
              onPressed: () => Navigator.pop(context, true),
              child: Text(l10n.pnGateBypass),
            ),
          ],
        ),
      );
      if (ok != true || !context.mounted) return;
      bypass = true;
    }
    await _run(
      context,
      ref,
      (s) => s.activate(v.partnership, gateBypassConfirmed: bypass),
      success: l10n.pnActivated,
    );
  }

  Future<void> _consent(
    BuildContext context,
    WidgetRef ref,
    PartnershipView v,
    Member m,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    var pin = '';
    if (m.hasPersonalPin) {
      final entered = await showMemberPinPrompt(
        context,
        name: l10n.member(m),
        okLabel: l10n.pnConsent,
      );
      if (entered == null) return;
      pin = entered;
    }
    final check = await (await ref.read(
      partnershipServiceProvider.future,
    )).consent(v.partnership, m, pin);
    if (check case PinRejected(:final attemptsBeforeLockout)) {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.pinWrong(attemptsBeforeLockout))),
      );
    }
    _refresh(ref);
  }

  Future<void> _sharePdf(
    BuildContext context,
    WidgetRef ref,
    PartnershipView v,
  ) async {
    final l10n = context.l10n;
    final money = context.money;
    final messenger = ScaffoldMessenger.of(context);
    final t = v.terms;
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    final doc = PartnershipContractDoc(
      title: l10n.pnPdfTitle,
      subtitle: '${t.title} · ${l10n.partnershipType(t.type)}',
      partiesHeading: l10n.pnPdfParties,
      partyHeaders: [
        l10n.pnPdfName,
        l10n.pnPdfRole,
        l10n.pnPdfCapital,
        l10n.pnPdfShare,
      ],
      partyRows: [
        for (final p in t.partners)
          [
            p.name,
            l10n.partnerRole(p.role),
            money(p.capitalTotal(t.currency)),
            '${percentLabel(p.shareBp)} %',
          ],
      ],
      capitalLines: [
        for (final p in t.partners)
          for (final c in p.capital)
            _capitalLine(
              p.name,
              c.title,
              l10n.capitalKind(c.kind),
              money(c.amount),
            ),
      ],
      termsHeading: l10n.pnPdfTerms,
      terms: [
        (l10n.pnPdfType, l10n.partnershipType(t.type)),
        (l10n.pnPdfVersion, '${v.contract.version}'),
        (l10n.pnTermMonths, '${t.termMonths}'),
        (l10n.pnReportPeriod, l10n.reportPeriod(t.reportPeriod)),
        (
          l10n.pnPdfLoss,
          t.type == PartnershipType.mudaraba
              ? l10n.pnLossRuleMudaraba
              : l10n.pnLossRuleMusharaka(_lossRatios(v)),
        ),
        (l10n.pnEndTerms, t.endTerms),
        (l10n.pnDisputeTerms, t.disputeTerms),
      ],
      note: l10n.pnPdfNote,
      warning: v.template.isPending ? l10n.pnTemplatePending : null,
      signaturesHeading: l10n.receiptPdfSignatures,
      signatures: [
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
      ],
      footer: '${l10n.appTitle} · ${formatDate(today)}',
    );
    try {
      final bytes = await buildPartnershipContractPdf(
        await PdfFonts.load(rootBundle),
        doc,
      );
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile.fromData(
              bytes,
              mimeType: 'application/pdf',
              name: 'sheriklik_shartnomasi.pdf',
            ),
          ],
          fileNameOverrides: const ['sheriklik_shartnomasi.pdf'],
          subject: l10n.pnPdfTitle,
        ),
      );
    } on Object {
      AppLog.event('partnership_pdf_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  String _lossRatios(PartnershipView v) => [
    for (final p in v.partners)
      _ratio(p.name, ratioBasisPoints(v.capitalOf(p), v.totalCapital) ?? 0),
  ].join(', ');

  static String _ratio(String name, int bp) => '$name ${percentLabel(bp)} %';

  static String _capitalLine(
    String name,
    String title,
    String kind,
    String amount,
  ) => '$name: $title ($kind) — $amount';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final view = ref.watch(partnershipViewProvider(id));
    final gateOpen =
        ref.watch(vaultOverviewProvider).valueOrNull?.gate.isOpen ?? false;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.pnTitle)),
      body: switch (view) {
        AsyncData(:final value?) => () {
          final v = value;
          final p = v.partnership;
          final status = p.status;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text(p.title, style: theme.textTheme.titleLarge),
              Text(l10n.partnershipType(p.type)),
              Align(
                alignment: Alignment.centerLeft,
                child: Chip(
                  key: const Key('pn-status'),
                  label: Text(l10n.partnershipStatus(status)),
                ),
              ),
              if (v.template.isPending)
                Card(
                  color: theme.colorScheme.tertiaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(l10n.pnTemplatePending),
                  ),
                ),
              const SizedBox(height: 8),
              for (final x in v.partners)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(x.name),
                  subtitle: Text(
                    '${l10n.partnerRole(x.role)} · '
                    '${percentLabel(x.profitShareBp)} %',
                  ),
                  trailing: Text(money(v.capitalOf(x))),
                ),
              Text(
                p.type == PartnershipType.mudaraba
                    ? l10n.pnLossRuleMudaraba
                    : l10n.pnLossRuleMusharaka(_lossRatios(v)),
                style: theme.textTheme.bodySmall,
              ),
              _LossCalculator(view: v),
              const SizedBox(height: 12),
              // Telefon kengligida tugma matni uzun — qator o'raladi.
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(
                    l10n.pnContractVersion(v.contract.version),
                    key: const Key('pn-version'),
                    style: theme.textTheme.titleSmall,
                  ),
                  if (status != PartnershipStatus.closed)
                    TextButton(
                      key: const Key('pn-amend'),
                      onPressed: () => _amend(context, ref, v),
                      child: Text(l10n.pnAmend),
                    ),
                ],
              ),
              // 6-qonun: shartnoma = 9 savolli kelishuv; 9/9 dan keyin imzo.
              AgreementLinkCard(
                source: AgreementSource.partnership,
                sourceId: p.meta.id,
              ),
              if (v.needsResign)
                Text(
                  l10n.pnResign,
                  key: const Key('pn-resign'),
                  style: TextStyle(color: theme.colorScheme.error),
                ),
              for (final s in v.signers)
                ListTile(
                  key: Key('pn-signer-${s.meta.id}'),
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    s.isSigned ? Icons.check_circle : Icons.draw_outlined,
                    color: s.isSigned ? theme.colorScheme.primary : null,
                  ),
                  title: Text(s.name),
                  subtitle: Text(
                    '${l10n.signerRole(s.role)}'
                    '${s.isSigned ? ' · ${l10n.signed}' : ''}',
                  ),
                  // Imzolagan tomon qayta imzolamaydi (rad etiladi ham).
                  trailing: status == PartnershipStatus.closed || s.isSigned
                      ? null
                      : TextButton(
                          key: Key('pn-sign-${s.meta.id}'),
                          onPressed: () => _sign(context, ref, v, s),
                          child: Text(l10n.signAction),
                        ),
                ),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  key: const Key('pn-pdf'),
                  icon: const Icon(Icons.ios_share),
                  label: Text(l10n.pnPdf),
                  onPressed: () => _sharePdf(context, ref, v),
                ),
              ),
              const SizedBox(height: 12),
              if (status == PartnershipStatus.draft)
                Text(l10n.pnSignFirst, key: const Key('pn-sign-first')),
              if (status == PartnershipStatus.signed) ...[
                if (v.meProvidesCapital)
                  Card(
                    key: const Key('pn-gate'),
                    child: ListTile(
                      leading: Icon(
                        gateOpen ? Icons.lock_open : Icons.lock_outline,
                      ),
                      title: Text(l10n.pnGateTitle),
                      subtitle: Text(
                        gateOpen ? l10n.pnGateOpen : l10n.pnGateClosed,
                      ),
                    ),
                  ),
                if (v.meReceivesCapital)
                  _ReceiveCard(
                    view: v,
                    onAck: () => _run(
                      context,
                      ref,
                      (s) => s.acknowledgeNotDebt(p),
                    ),
                    onConsent: (m) => _consent(context, ref, v, m),
                  ),
                FilledButton(
                  key: const Key('pn-activate'),
                  onPressed:
                      v.meReceivesCapital &&
                          (!p.notDebtAcknowledged || !v.consentComplete)
                      ? null
                      : () => _activate(context, ref, v, gateOpen),
                  child: Text(l10n.pnActivate),
                ),
              ],
              if (status == PartnershipStatus.active) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: FilledButton.icon(
                    key: const Key('pn-ledger'),
                    icon: const Icon(Icons.menu_book_outlined),
                    label: Text(l10n.ledgerOpenButton),
                    onPressed: () =>
                        context.push(AppRoutes.partnershipLedger(p.meta.id)),
                  ),
                ),
                if (v.providerStake.isPositive)
                  _BuyoutCard(
                    view: v,
                    onSet: () async {
                      final m = await showAmountSheet(
                        context,
                        currency: v.currency,
                        title: l10n.pnBuyoutSet,
                        initial: p.buyoutMonthly,
                      );
                      if (m == null || !m.isPositive || !context.mounted) {
                        return;
                      }
                      await _run(context, ref, (s) => s.setBuyout(p, m));
                    },
                    onPay: () async {
                      final m = await showAmountSheet(
                        context,
                        currency: v.currency,
                        title: l10n.pnBuyoutPay,
                        initial: p.buyoutMonthly,
                        max: v.buyoutRemaining,
                      );
                      if (m == null || !m.isPositive || !context.mounted) {
                        return;
                      }
                      await _run(context, ref, (s) => s.recordBuyout(p, m));
                    },
                  ),
                // Buyout to'lovlari alohida ro'yxatda (kassa daftarida emas).
                if (v.providerStake.isPositive) _BuyoutHistoryCard(view: v),
                TextButton(
                  key: const Key('pn-close'),
                  onPressed: () => _run(context, ref, (s) => s.close(p)),
                  child: Text(l10n.pnClose),
                ),
              ],
            ],
          );
        }(),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

/// «Bu qarz emas» va oilaviy rozilik (kapital qabul qiluvchi, SPEC 2E.6).
class _ReceiveCard extends StatelessWidget {
  const _ReceiveCard({
    required this.view,
    required this.onAck,
    required this.onConsent,
  });

  final PartnershipView view;
  final VoidCallback onAck;
  final void Function(Member) onConsent;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Card(
      key: const Key('pn-receive'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.pnNotDebtTitle, style: theme.textTheme.titleMedium),
            Text(l10n.pnNotDebtBody),
            if (!view.partnership.notDebtAcknowledged)
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  key: const Key('pn-ack'),
                  onPressed: onAck,
                  child: Text(l10n.pnNotDebtAck),
                ),
              )
            else ...[
              const Divider(),
              Text(l10n.pnConsentTitle, style: theme.textTheme.titleSmall),
              for (final m in view.adults)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.member(m)),
                  trailing: view.consentedBy.contains(m.meta.id)
                      ? Chip(
                          avatar: const Icon(Icons.check, size: 18),
                          label: Text(l10n.pnConsented),
                        )
                      : FilledButton.tonal(
                          key: Key('pn-consent-${m.meta.id}'),
                          onPressed: () => onConsent(m),
                          child: Text(l10n.pnConsent),
                        ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Kamayib boruvchi musharaka: qolgan ulush va jadval.
class _BuyoutCard extends StatelessWidget {
  const _BuyoutCard({
    required this.view,
    required this.onSet,
    required this.onPay,
  });

  final PartnershipView view;
  final VoidCallback onSet;
  final VoidCallback onPay;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final rows = view.buyout;
    final shareBp =
        ratioBasisPoints(view.buyoutRemaining, view.totalCapital) ?? 0;
    return Card(
      key: const Key('pn-buyout'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.pnBuyoutTitle, style: theme.textTheme.titleMedium),
            Text(l10n.pnBuyoutHint, style: theme.textTheme.bodySmall),
            const SizedBox(height: 8),
            Text(
              l10n.pnBuyoutRemaining(
                money(view.buyoutRemaining),
                percentLabel(shareBp),
              ),
              key: const Key('pn-buyout-remaining'),
            ),
            const SizedBox(height: 4),
            LinearProgressIndicator(value: shareBp / basisPointsWhole),
            if (rows.isNotEmpty)
              Text(
                l10n.pnBuyoutEnd(formatDate(rows.last.dueOn), rows.length),
                key: const Key('pn-buyout-end'),
              ),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton(
                  key: const Key('pn-buyout-set'),
                  onPressed: onSet,
                  child: Text(
                    view.partnership.buyoutMonthly == null
                        ? l10n.pnBuyoutSet
                        : l10n.pnBuyoutMonthly(
                            money(view.partnership.buyoutMonthly!),
                          ),
                  ),
                ),
                if (view.buyoutRemaining.isPositive)
                  OutlinedButton(
                    key: const Key('pn-buyout-pay'),
                    onPressed: onPay,
                    child: Text(l10n.pnBuyoutPay),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Buyout to'lovlari tarixi — kassa daftaridan alohida (OPEN 123).
class _BuyoutHistoryCard extends StatelessWidget {
  const _BuyoutHistoryCard({required this.view});

  final PartnershipView view;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final payments = view.buyoutPayments;
    return Card(
      key: const Key('pn-buyout-history'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.pnBuyoutHistory,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            if (payments.isEmpty)
              Text(l10n.pnBuyoutNone)
            else
              for (final p in payments)
                Text(
                  l10n.pnBuyoutPaidRow(money(p.amount), formatDate(p.paidOn)),
                ),
          ],
        ),
      ),
    );
  }
}

/// «Zarar bo'lsa kim ko'taradi?» — qoidaning jonli ko'rinishi.
class _LossCalculator extends StatefulWidget {
  const _LossCalculator({required this.view});

  final PartnershipView view;

  @override
  State<_LossCalculator> createState() => _LossCalculatorState();
}

class _LossCalculatorState extends State<_LossCalculator> {
  Money? _loss;
  bool _negligence = false;
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final v = widget.view;
    final loss = _loss;
    List<Money>? shares;
    String? error;
    if (loss != null && loss.isPositive) {
      try {
        shares = PartnershipRules.lossShares(
          type: v.partnership.type,
          roles: [for (final p in v.partners) p.role],
          capital: [for (final p in v.partners) v.capitalOf(p)],
          loss: loss,
          negligence: _negligence,
          note: _note.text,
        );
      } on DomainRuleException catch (e) {
        error = partnershipError(context, e.code);
      }
    }
    return ExpansionTile(
      key: const Key('pn-loss-calc'),
      tilePadding: EdgeInsets.zero,
      title: Text(l10n.pnLossCalc, style: theme.textTheme.titleSmall),
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(
            key: const Key('pn-loss-amount'),
            onPressed: () async {
              final m = await showAmountSheet(
                context,
                currency: v.currency,
                title: l10n.pnLossCalc,
                initial: _loss,
              );
              if (m != null) setState(() => _loss = m);
            },
            child: Text(
              l10n.pnLossAmount(money(loss ?? Money.zero(v.currency))),
            ),
          ),
        ),
        if (v.partnership.type == PartnershipType.mudaraba) ...[
          SwitchListTile(
            key: const Key('pn-negligence'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.pnNegligence),
            value: _negligence,
            onChanged: (x) => setState(() => _negligence = x),
          ),
          if (_negligence)
            TextField(
              key: const Key('pn-negligence-note'),
              controller: _note,
              decoration: InputDecoration(labelText: l10n.pnNegligenceNote),
              onChanged: (_) => setState(() {}),
            ),
        ],
        if (error != null)
          Text(error, style: TextStyle(color: theme.colorScheme.error)),
        if (shares != null)
          for (final (i, p) in v.partners.indexed)
            ListTile(
              key: Key('pn-loss-${p.meta.id}'),
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(p.name),
              trailing: Text(money(shares[i])),
            ),
      ],
    );
  }
}
