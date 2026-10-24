import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Foyda qanday belgilanadi — faqat foiz qabul qilinadi (SPEC 2E.1).
enum ProfitMethod { percent, fixed, guaranteed }

/// Domen xatosi kodini foydalanuvchi matniga.
String partnershipError(BuildContext context, String code) {
  final l10n = context.l10n;
  return switch (code) {
    PartnershipRules.errNotPartnership => l10n.pnNotPartnership,
    PartnershipRules.errSharesTotal ||
    PartnershipRules.errShareNegative => l10n.pnErrorShares,
    PartnershipRules.errMusharakaCapital => l10n.pnErrorCapital,
    PartnershipRules.errNoCapital => l10n.pnErrorNoCapital,
    PartnershipRules.errMudarabaRoles ||
    PartnershipRules.errMudarabaWorkerCapital => l10n.pnErrorRoles,
    PartnershipRules.errNegligenceNote => l10n.pnNegligenceNoteRequired,
    _ => l10n.genericError,
  };
}

/// «Hunardan ishga» g'oyasidan shartnoma qoralamasi (SPEC 2E.4): men —
/// mehnat egasi, CAPEX — sherik kiritadigan uskunalar.
@immutable
final class PartnershipPrefill {
  const PartnershipPrefill({required this.title, required this.capital});

  final String title;
  final List<CapitalItem> capital;
}

/// Shartnoma ustasi (SPEC 2E.2): tomonlar, tur, kapital, ulushlar, zarar
/// qoidalari, muddat, hisobot, muddat tugashi, nizolar, guvohlar.
class PartnershipWizardScreen extends ConsumerStatefulWidget {
  const PartnershipWizardScreen({this.prefill, super.key});

  final PartnershipPrefill? prefill;

  @override
  ConsumerState<PartnershipWizardScreen> createState() =>
      _PartnershipWizardScreenState();
}

class _PartnershipWizardScreenState
    extends ConsumerState<PartnershipWizardScreen> {
  static const _steps = 6;
  int _step = 0;
  bool _saving = false;

  final _title = TextEditingController();
  final _myName = TextEditingController();
  final _partnerName = TextEditingController();
  final _myShare = TextEditingController(text: '50');
  final _term = TextEditingController(text: '12');
  final _endTerms = TextEditingController();
  final _dispute = TextEditingController();

  PartnershipType _type = PartnershipType.mudaraba;
  PartnerRole _myRole = PartnerRole.capitalProvider;
  PartnerRole _partnerRole = PartnerRole.worker;
  ProfitMethod _method = ProfitMethod.percent;
  ReportPeriod _period = ReportPeriod.monthly;
  final List<CapitalItem> _myCapital = [];
  final List<CapitalItem> _partnerCapital = [];
  final List<String> _witnesses = [];
  bool _defaultsFilled = false;

  @override
  void initState() {
    super.initState();
    final pre = widget.prefill;
    if (pre != null) {
      _title.text = pre.title;
      _myRole = PartnerRole.worker;
      _partnerRole = PartnerRole.capitalProvider;
      _partnerCapital.addAll(pre.capital);
    }
  }

  @override
  void dispose() {
    for (final c in [
      _title,
      _myName,
      _partnerName,
      _myShare,
      _term,
      _endTerms,
      _dispute,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  CurrencyCode get _currency => CurrencyCode.uzs;

  int? get _myShareBp => parsePercentBp(_myShare.text);

  /// Mudarabada sherikning roli — mening rolimga teskari.
  void _setType(PartnershipType t) => setState(() {
    _type = t;
    if (t == PartnershipType.mudaraba) {
      if (_myRole == PartnerRole.both) _myRole = PartnerRole.capitalProvider;
      _partnerRole = _myRole == PartnerRole.worker
          ? PartnerRole.capitalProvider
          : PartnerRole.worker;
    } else {
      _myRole = PartnerRole.both;
      _partnerRole = PartnerRole.both;
    }
  });

  void _setMyRole(PartnerRole r) => setState(() {
    _myRole = r;
    if (_type == PartnershipType.mudaraba) {
      _partnerRole = r == PartnerRole.worker
          ? PartnerRole.capitalProvider
          : PartnerRole.worker;
    }
  });

  List<PartnerDraft> _drafts() {
    final mine = _myShareBp ?? 0;
    final ProfitShareInput my;
    final ProfitShareInput theirs;
    switch (_method) {
      case ProfitMethod.percent:
        my = ProfitShareInput.percent(mine);
        theirs = ProfitShareInput.percent(basisPointsWhole - mine);
      case ProfitMethod.fixed:
        // Urinish domen tomonidan rad etiladi («bu sheriklik emas»).
        final fixed = ProfitShareInput.fixed(Money.major(1, _currency));
        my = _myRole == PartnerRole.worker
            ? ProfitShareInput.percent(mine)
            : fixed;
        theirs = _myRole == PartnerRole.worker
            ? fixed
            : ProfitShareInput.percent(basisPointsWhole - mine);
      case ProfitMethod.guaranteed:
        my = ProfitShareInput.guaranteed(mine);
        theirs = ProfitShareInput.guaranteed(basisPointsWhole - mine);
    }
    return [
      PartnerDraft(
        name: _myName.text.trim(),
        role: _myRole,
        profit: my,
        capital: List.of(_myCapital),
        isMe: true,
      ),
      PartnerDraft(
        name: _partnerName.text.trim(),
        role: _partnerRole,
        profit: theirs,
        capital: List.of(_partnerCapital),
      ),
    ];
  }

  /// Qadamdagi domen tekshiruvi (kapital, ulushlar) — xato matni yoki null.
  String? _stepError() {
    if (_step < 2) return null;
    try {
      if (_step == 2) {
        // Ulushlarni hali tekshirmaymiz — faqat rollar va kapital.
        PartnershipRules.validate(_type, [
          for (final d in _drafts())
            PartnerDraft(
              name: d.name,
              role: d.role,
              profit: const ProfitShareInput.percent(5000),
              capital: d.capital,
              isMe: d.isMe,
            ),
        ], _currency);
      } else {
        PartnershipRules.validate(_type, _drafts(), _currency);
      }
    } on DomainRuleException catch (e) {
      return partnershipError(context, e.code);
    }
    return null;
  }

  bool get _canNext => switch (_step) {
    0 => _title.text.trim().isNotEmpty,
    1 => _myName.text.trim().isNotEmpty && _partnerName.text.trim().isNotEmpty,
    2 => _stepError() == null,
    3 =>
      _method == ProfitMethod.percent &&
          _myShareBp != null &&
          _myShareBp! <= basisPointsWhole &&
          _stepError() == null,
    4 =>
      (int.tryParse(_term.text) ?? 0) > 0 &&
          _endTerms.text.trim().isNotEmpty &&
          _dispute.text.trim().isNotEmpty,
    _ => true,
  };

  Future<void> _addCapital(List<CapitalItem> target) async {
    final l10n = context.l10n;
    final draft = await showDialog<(String, CapitalKind)>(
      context: context,
      builder: (_) => const _CapitalDialog(),
    );
    if (draft == null || !mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: _currency,
      title: l10n.pnCapitalAmount,
    );
    if (amount == null || !amount.isPositive) return;
    setState(
      () => target.add(
        CapitalItem(kind: draft.$2, title: draft.$1, amount: amount),
      ),
    );
  }

  Future<void> _addWitness() async {
    final l10n = context.l10n;
    final name = await showTextPrompt(
      context,
      title: l10n.pnWitnessAdd,
      label: l10n.memberName,
      fieldKey: const Key('pn-witness-name'),
      okKey: const Key('pn-witness-ok'),
    );
    if (name == null || name.trim().isEmpty) return;
    setState(() => _witnesses.add(name.trim()));
  }

  Future<void> _create() async {
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    final errorText = context.l10n.genericError;
    setState(() => _saving = true);
    try {
      final p = await (await ref.read(partnershipServiceProvider.future))
          .create(
            title: _title.text,
            type: _type,
            partners: _drafts(),
            termMonths: int.parse(_term.text),
            reportPeriod: _period,
            endTerms: _endTerms.text,
            disputeTerms: _dispute.text,
            witnesses: _witnesses,
          );
      ref.invalidate(partnershipsProvider);
      unawaited(router.pushReplacement(AppRoutes.partnership(p.meta.id)));
    } on DomainRuleException catch (e) {
      AppLog.event('partnership_rejected_${e.code}');
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(partnershipError(context, e.code))),
      );
      setState(() => _saving = false);
    } on Object {
      AppLog.event('partnership_create_failed');
      messenger.showSnackBar(SnackBar(content: Text(errorText)));
      if (mounted) setState(() => _saving = false);
    }
  }

  static String _ratioText(String name, int bp) =>
      '$name ${percentLabel(bp)} %';

  Widget _chips<T>(
    List<T> values,
    T selected,
    String Function(T) label,
    ValueChanged<T> onSelected,
    String keyPrefix,
  ) => Wrap(
    spacing: 8,
    runSpacing: 4,
    children: [
      for (final v in values)
        ChoiceChip(
          key: Key('$keyPrefix-${v is Enum ? v.name : v}'),
          label: Text(label(v)),
          selected: v == selected,
          onSelected: (_) => onSelected(v),
        ),
    ],
  );

  Widget _capitalList(String name, List<CapitalItem> items, String keyId) {
    final l10n = context.l10n;
    final money = context.money;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.pnCapitalOf(
                name,
                money(Money.sum(items.map((x) => x.amount), _currency)),
              ),
              style: Theme.of(context).textTheme.titleSmall,
            ),
            for (final (i, x) in items.indexed)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(x.title),
                subtitle: Text(
                  '${l10n.capitalKind(x.kind)} · ${money(x.amount)}',
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => setState(() => items.removeAt(i)),
                ),
              ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                key: Key('pn-capital-add-$keyId'),
                icon: const Icon(Icons.add),
                label: Text(l10n.pnCapitalAdd),
                onPressed: () => _addCapital(items),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _content() {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final roles = _type == PartnershipType.mudaraba
        ? const [PartnerRole.capitalProvider, PartnerRole.worker]
        : const [PartnerRole.capitalProvider, PartnerRole.both];
    switch (_step) {
      case 0:
        return [
          TextField(
            key: const Key('pn-title'),
            controller: _title,
            decoration: InputDecoration(labelText: l10n.pnName),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          _chips(
            PartnershipType.values,
            _type,
            l10n.partnershipType,
            _setType,
            'pn-type',
          ),
          const SizedBox(height: 8),
          Text(
            _type == PartnershipType.mudaraba
                ? l10n.pnTypeMudarabaHint
                : l10n.pnTypeMusharakaHint,
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          Text(l10n.pnMyRole, style: theme.textTheme.titleSmall),
          _chips(roles, _myRole, l10n.partnerRole, _setMyRole, 'pn-myrole'),
        ];
      case 1:
        return [
          TextField(
            key: const Key('pn-my-name'),
            controller: _myName,
            decoration: InputDecoration(labelText: l10n.pnMyName),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('pn-partner-name'),
            controller: _partnerName,
            decoration: InputDecoration(labelText: l10n.pnPartnerName),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          Text(l10n.pnPartnerRole, style: theme.textTheme.titleSmall),
          if (_type == PartnershipType.mudaraba)
            Text(l10n.partnerRole(_partnerRole))
          else
            _chips(
              roles,
              _partnerRole,
              l10n.partnerRole,
              (r) => setState(() => _partnerRole = r),
              'pn-partnerrole',
            ),
        ];
      case 2:
        final err = _stepError();
        return [
          if (_myRole != PartnerRole.worker)
            _capitalList(_myName.text, _myCapital, 'me'),
          if (_partnerRole != PartnerRole.worker)
            _capitalList(_partnerName.text, _partnerCapital, 'partner'),
          if (err != null)
            Text(err, style: TextStyle(color: theme.colorScheme.error)),
        ];
      case 3:
        final err = _method == ProfitMethod.percent ? _stepError() : null;
        final mine = _myShareBp;
        final capitals = [
          Money.sum(_myCapital.map((x) => x.amount), _currency),
          Money.sum(_partnerCapital.map((x) => x.amount), _currency),
        ];
        final total = capitals[0] + capitals[1];
        return [
          Text(l10n.pnProfitMethod, style: theme.textTheme.titleSmall),
          _chips(
            ProfitMethod.values,
            _method,
            (m) => switch (m) {
              ProfitMethod.percent => l10n.pnProfitPercent,
              ProfitMethod.fixed => l10n.pnProfitFixed,
              ProfitMethod.guaranteed => l10n.pnProfitGuaranteed,
            },
            (m) => setState(() => _method = m),
            'pn-profit',
          ),
          if (_method != ProfitMethod.percent)
            Card(
              key: const Key('pn-not-partnership'),
              color: theme.colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  l10n.pnNotPartnership,
                  style: TextStyle(color: theme.colorScheme.onErrorContainer),
                ),
              ),
            )
          else ...[
            TextField(
              key: const Key('pn-my-share'),
              controller: _myShare,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: InputDecoration(labelText: l10n.pnMyShare),
              onChanged: (_) => setState(() {}),
            ),
            if (mine != null && mine <= basisPointsWhole)
              Text(
                l10n.pnPartnerShare(percentLabel(basisPointsWhole - mine)),
              ),
            if (err != null)
              Text(err, style: TextStyle(color: theme.colorScheme.error)),
          ],
          const SizedBox(height: 12),
          Text(
            _type == PartnershipType.mudaraba
                ? l10n.pnLossRuleMudaraba
                : l10n.pnLossRuleMusharaka(
                    [
                      for (final (i, name) in [
                        _myName.text,
                        _partnerName.text,
                      ].indexed)
                        _ratioText(
                          name,
                          ratioBasisPoints(capitals[i], total) ?? 0,
                        ),
                    ].join(', '),
                  ),
            key: const Key('pn-loss-rule'),
            style: theme.textTheme.bodySmall,
          ),
        ];
      case 4:
        if (!_defaultsFilled) {
          _endTerms.text = l10n.pnEndTermsDefault;
          _dispute.text = l10n.pnDisputeTermsDefault;
          _defaultsFilled = true;
        }
        return [
          TextField(
            key: const Key('pn-term'),
            controller: _term,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: InputDecoration(labelText: l10n.pnTermMonths),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          Text(l10n.pnReportPeriod, style: theme.textTheme.titleSmall),
          _chips(
            ReportPeriod.values,
            _period,
            l10n.reportPeriod,
            (p) => setState(() => _period = p),
            'pn-period',
          ),
          TextField(
            key: const Key('pn-end-terms'),
            controller: _endTerms,
            maxLines: 3,
            minLines: 1,
            decoration: InputDecoration(labelText: l10n.pnEndTerms),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('pn-dispute'),
            controller: _dispute,
            maxLines: 3,
            minLines: 1,
            decoration: InputDecoration(labelText: l10n.pnDisputeTerms),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          Text(l10n.pnWitnesses, style: theme.textTheme.titleSmall),
          for (final (i, w) in _witnesses.indexed)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(w),
              trailing: IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => setState(() => _witnesses.removeAt(i)),
              ),
            ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const Key('pn-witness-add'),
              icon: const Icon(Icons.add),
              label: Text(l10n.pnWitnessAdd),
              onPressed: _addWitness,
            ),
          ),
        ];
      default:
        final drafts = _drafts();
        return [
          Text(_title.text, style: theme.textTheme.titleLarge),
          Text(l10n.partnershipType(_type)),
          const SizedBox(height: 8),
          for (final d in drafts)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(d.name),
              subtitle: Text(
                '${l10n.partnerRole(d.role)} · '
                '${percentLabel(d.profit.basisPoints ?? 0)} %',
              ),
              trailing: Text(
                money(PartnershipRules.capitalOf(d, _currency)),
              ),
            ),
          Text(
            '${l10n.pnTermMonths}: ${_term.text} · '
            '${l10n.reportPeriod(_period)}',
          ),
          const SizedBox(height: 8),
          Card(
            color: theme.colorScheme.tertiaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                l10n.pnTemplatePending,
                key: const Key('pn-template-pending'),
              ),
            ),
          ),
        ];
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final owner = ref.watch(membersProvider).valueOrNull;
    if (_myName.text.isEmpty && owner != null && owner.isNotEmpty) {
      _myName.text = l10n.member(owner.first);
    }
    final titles = [
      l10n.pnStepType,
      l10n.pnStepParties,
      l10n.pnStepCapital,
      l10n.pnStepProfit,
      l10n.pnStepTerms,
      l10n.pnStepReview,
    ];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.pnNew)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          LinearProgressIndicator(value: (_step + 1) / _steps),
          const SizedBox(height: 8),
          Text(
            '${_step + 1} / $_steps · ${titles[_step]}',
            key: const Key('pn-step-title'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          ..._content(),
          const SizedBox(height: 16),
          // Tor ekranda (yoki katta shriftda) tugmalar ikki qatorga o'tadi.
          OverflowBar(
            alignment: MainAxisAlignment.spaceBetween,
            overflowAlignment: OverflowBarAlignment.end,
            overflowSpacing: 8,
            children: [
              if (_step > 0)
                TextButton(
                  key: const Key('pn-back'),
                  onPressed: () => setState(() => _step--),
                  child: Text(l10n.pnBack),
                )
              else
                const SizedBox.shrink(),
              if (_step < _steps - 1)
                FilledButton(
                  key: const Key('pn-next'),
                  onPressed: _canNext ? () => setState(() => _step++) : null,
                  child: Text(l10n.pnNext),
                )
              else
                FilledButton(
                  key: const Key('pn-create'),
                  onPressed: _saving ? null : _create,
                  child: Text(l10n.pnCreate),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CapitalDialog extends StatefulWidget {
  const _CapitalDialog();

  @override
  State<_CapitalDialog> createState() => _CapitalDialogState();
}

class _CapitalDialogState extends State<_CapitalDialog> {
  final _title = TextEditingController();
  CapitalKind _kind = CapitalKind.cash;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.pnCapitalAdd),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Wrap(
            spacing: 8,
            children: [
              for (final k in CapitalKind.values)
                ChoiceChip(
                  key: Key('pn-capital-kind-${k.name}'),
                  label: Text(l10n.capitalKind(k)),
                  selected: _kind == k,
                  onSelected: (_) => setState(() => _kind = k),
                ),
            ],
          ),
          TextField(
            key: const Key('pn-capital-title'),
            controller: _title,
            autofocus: true,
            decoration: InputDecoration(labelText: l10n.pnCapitalTitle),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('pn-capital-ok'),
          onPressed: _title.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (_title.text.trim(), _kind)),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
