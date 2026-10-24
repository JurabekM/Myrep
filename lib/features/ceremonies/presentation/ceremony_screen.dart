import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/features/ceremonies/data/ceremony_providers.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony_math.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony_service.dart';
import 'package:baraka_daftari/features/ceremonies/presentation/ceremonies_screen.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/presentation/member_pin_prompt.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';

/// Marosim rejasi (SPEC 2D.8): stsenariylar taqqoslashi, byudjet qatorlari,
/// «Buni qarzsiz qanday o'tkazamiz?» muhokamasi, to'yona o'rniga jamg'arma.
class CeremonyScreen extends ConsumerWidget {
  const CeremonyScreen({required this.planId, super.key});

  final String planId;

  Future<CeremonyService> _service(WidgetRef ref) =>
      ref.read(ceremonyServiceProvider.future);

  void _refresh(WidgetRef ref) => ref
    ..invalidate(ceremonyViewProvider(planId))
    ..invalidate(ceremonyPlansProvider);

  /// Xizmat amalini bajarib, xatoni xabar qilish.
  Future<void> _run(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function(CeremonyService s) action,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await action(await _service(ref));
    } on DomainRuleException catch (e) {
      AppLog.event('ceremony_rejected_${e.code}');
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            e.code == CeremonyService.errDiscussionRequired
                ? l10n.ceremonyConfirmBlocked
                : e.code == CeremonyService.errConfirmedLocked
                ? l10n.ceremonyLocked
                : l10n.genericError,
          ),
        ),
      );
    }
    _refresh(ref);
  }

  Future<void> _addScenario(
    BuildContext context,
    WidgetRef ref,
    CeremonyView v,
  ) async {
    final l10n = context.l10n;
    final name = await showTextPrompt(
      context,
      title: l10n.scenarioAdd,
      label: l10n.scenarioName,
      fieldKey: const Key('scenario-name'),
      okKey: const Key('scenario-name-ok'),
    );
    if (name == null || name.trim().isEmpty || !context.mounted) return;
    final from = v.selected?.scenario;
    await _run(
      context,
      ref,
      (s) => s.addScenario(
        v.plan,
        name: name,
        guests: from?.guests ?? 0,
        copyFrom: from,
      ),
    );
  }

  Future<void> _editGuests(
    BuildContext context,
    WidgetRef ref,
    CeremonyScenario scenario,
  ) async {
    final text = await showTextPrompt(
      context,
      title: context.l10n.ceremonyGuestsTitle,
      label: context.l10n.ceremonyGuestsTitle,
      fieldKey: const Key('guests-field'),
      okKey: const Key('guests-ok'),
      initial: '${scenario.guests}',
      keyboardType: TextInputType.number,
    );
    final guests = int.tryParse(text?.trim() ?? '');
    if (guests == null || !context.mounted) return;
    await _run(context, ref, (s) => s.updateScenario(scenario, guests: guests));
  }

  Future<void> _addLine(
    BuildContext context,
    WidgetRef ref,
    CeremonyScenario scenario,
    CurrencyCode currency,
  ) async {
    final l10n = context.l10n;
    final draft = await showDialog<(String, CeremonyLineKind, FundingSource)>(
      context: context,
      builder: (_) => const _LineDialog(),
    );
    if (draft == null || !context.mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: currency,
      title: draft.$2 == CeremonyLineKind.perGuest
          ? l10n.linePriceTitle
          : l10n.lineAmountTitle,
    );
    if (amount == null || !amount.isPositive || !context.mounted) return;
    await _run(
      context,
      ref,
      (s) => s.addLine(
        scenario,
        title: draft.$1,
        kind: draft.$2,
        amount: amount,
        source: draft.$3,
      ),
    );
  }

  Future<void> _changeSource(
    BuildContext context,
    WidgetRef ref,
    CeremonyBudgetLine line,
  ) async {
    final l10n = context.l10n;
    final source = await showDialog<FundingSource>(
      context: context,
      builder: (context) => SimpleDialog(
        title: Text(l10n.lineSourceTitle),
        children: [
          for (final f in FundingSource.values)
            SimpleDialogOption(
              key: Key('source-option-${f.name}'),
              onPressed: () => Navigator.pop(context, f),
              child: Text(l10n.fundingSource(f)),
            ),
        ],
      ),
    );
    if (source == null || !context.mounted) return;
    await _run(context, ref, (s) => s.updateLine(line, source: source));
  }

  Future<void> _debtTerms(
    BuildContext context,
    WidgetRef ref,
    CeremonyView v,
    Money? current,
  ) async {
    final monthly = await showAmountSheet(
      context,
      currency: v.plan.currency,
      title: context.l10n.ceremonyDebtMonthlyTitle,
      initial: current,
    );
    if (monthly == null || !monthly.isPositive || !context.mounted) return;
    await _run(
      context,
      ref,
      (s) => s.setDebtTerms(
        v.plan,
        monthly: monthly,
        annualRateBp: v.plan.debtAnnualRateBp ?? 0,
      ),
    );
  }

  Future<void> _mark(
    BuildContext context,
    WidgetRef ref,
    CeremonyView v,
    Member member,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    var pin = '';
    if (member.hasPersonalPin) {
      final entered = await showMemberPinPrompt(
        context,
        name: l10n.member(member),
        okLabel: l10n.discussionMark,
      );
      if (entered == null) return;
      pin = entered;
    }
    try {
      final (check, done) = await (await _service(
        ref,
      )).markDiscussed(v.plan, member, pin);
      final text = switch (check) {
        PinAccepted() when done => l10n.discussionDone,
        PinAccepted() => l10n.discussionMarkedSnack(l10n.member(member)),
        PinRejected(:final attemptsBeforeLockout) => l10n.pinWrong(
          attemptsBeforeLockout,
        ),
        PinLockedOut() => l10n.pinErrorGeneric,
      };
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(text)));
    } on Object {
      AppLog.event('ceremony_mark_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
    _refresh(ref);
  }

  Future<void> _confirm(
    BuildContext context,
    WidgetRef ref,
    CeremonyView v,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    final text = context.l10n.ceremonyConfirmedSnack;
    await _run(context, ref, (s) async {
      await s.confirm(v.plan);
      messenger.showSnackBar(SnackBar(content: Text(text)));
    });
  }

  Future<void> _createGift(
    BuildContext context,
    WidgetRef ref,
    CeremonyView v,
  ) async {
    final l10n = context.l10n;
    final title = await showTextPrompt(
      context,
      title: l10n.giftCreate,
      label: l10n.giftGoalName,
      fieldKey: const Key('gift-name'),
      okKey: const Key('gift-name-ok'),
    );
    if (title == null || title.trim().isEmpty || !context.mounted) return;
    final target = await showAmountSheet(
      context,
      currency: v.plan.currency,
      title: l10n.giftTargetTitle,
    );
    if (target == null || !target.isPositive || !context.mounted) return;
    await _run(
      context,
      ref,
      (s) => s.createGiftGoal(v.plan, title: title, target: target),
    );
  }

  Future<void> _addContribution(
    BuildContext context,
    WidgetRef ref,
    CeremonyView v,
  ) async {
    final l10n = context.l10n;
    final name = await showTextPrompt(
      context,
      title: l10n.giftAddContribution,
      label: l10n.giftContributorName,
      fieldKey: const Key('gift-contributor'),
      okKey: const Key('gift-contributor-ok'),
    );
    if (name == null || name.trim().isEmpty || !context.mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: v.plan.currency,
      title: l10n.giftAddContribution,
    );
    if (amount == null || !amount.isPositive || !context.mounted) return;
    await _run(
      context,
      ref,
      (s) => s.addContribution(v.giftGoal!, name: name, amount: amount),
    );
  }

  Future<void> _shareGift(BuildContext context, CeremonyView v) async {
    final money = context.money;
    final text = context.l10n.giftShareText(
      v.plan.title,
      v.giftGoal!.title,
      money(v.giftGoal!.target),
      money(v.giftCollected),
    );
    try {
      await SharePlus.instance.share(ShareParams(text: text));
    } on Object {
      AppLog.event('gift_share_failed');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final view = ref.watch(ceremonyViewProvider(planId));
    return Scaffold(
      appBar: AppBar(title: Text(l10n.ceremoniesTitle)),
      body: switch (view) {
        AsyncData(:final value?) => () {
          final v = value;
          final locked = v.isConfirmed;
          final selected = v.selected;
          final monthly = v.scenarios.isEmpty
              ? null
              : v.scenarios.first.debtMonthly;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text(v.plan.title, style: theme.textTheme.titleLarge),
              Text(
                [
                  l10n.ceremonyType(v.plan.type),
                  if (v.plan.eventDate != null)
                    l10n.ceremonyDate(formatDate(v.plan.eventDate!)),
                ].join(' · '),
              ),
              const SizedBox(height: 4),
              Align(
                alignment: Alignment.centerLeft,
                child: Chip(
                  key: const Key('ceremony-status'),
                  label: Text(l10n.ceremonyStatus(v.plan.status)),
                ),
              ),
              PressureCard(index: v.plan.title.length),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      l10n.scenarioCompare,
                      style: theme.textTheme.titleSmall,
                    ),
                  ),
                  if (!locked &&
                      v.scenarios.length < CeremonyService.maxScenarios)
                    TextButton(
                      key: const Key('scenario-add'),
                      onPressed: () => _addScenario(context, ref, v),
                      child: Text(l10n.scenarioAdd),
                    ),
                ],
              ),
              for (final s in v.scenarios)
                _ScenarioCard(
                  summary: s,
                  isSelected: s.scenario.meta.id == selected?.scenario.meta.id,
                  locked: locked,
                  canRemove: v.scenarios.length > 1,
                  onSelect: () =>
                      _run(context, ref, (x) => x.select(s.scenario)),
                  onGuests: () => _editGuests(context, ref, s.scenario),
                  onRemove: () =>
                      _run(context, ref, (x) => x.removeScenario(s.scenario)),
                ),
              if (v.scenarios.any((s) => s.hasDebt))
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    key: const Key('debt-terms'),
                    icon: const Icon(Icons.calendar_month_outlined),
                    label: Text(
                      monthly == null
                          ? l10n.ceremonyDebtTermsUnset
                          : l10n.ceremonyDebtTerms(money(monthly)),
                    ),
                    onPressed: () => _debtTerms(context, ref, v, monthly),
                  ),
                ),
              if (selected != null) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        selected.scenario.name,
                        style: theme.textTheme.titleSmall,
                      ),
                    ),
                    if (!locked)
                      TextButton(
                        key: const Key('line-add'),
                        onPressed: () => _addLine(
                          context,
                          ref,
                          selected.scenario,
                          v.plan.currency,
                        ),
                        child: Text(l10n.lineAdd),
                      ),
                  ],
                ),
                for (final line in selected.lines)
                  ListTile(
                    key: Key('line-${line.meta.id}'),
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      line.source == FundingSource.debt
                          ? Icons.flag
                          : Icons.circle_outlined,
                      size: 18,
                      color: line.source == FundingSource.debt
                          ? theme.colorScheme.error
                          : null,
                    ),
                    title: Text(line.title),
                    subtitle: Text(
                      [
                        l10n.fundingSource(line.source),
                        if (line.kind == CeremonyLineKind.perGuest)
                          l10n.linePerGuestValue(
                            money(line.amount),
                            selected.scenario.guests,
                            money(line.totalFor(selected.scenario.guests)),
                          ),
                      ].join(' · '),
                    ),
                    trailing: locked
                        ? Text(money(line.totalFor(selected.scenario.guests)))
                        : IconButton(
                            key: Key('line-remove-${line.meta.id}'),
                            tooltip: l10n.scenarioRemove,
                            icon: const Icon(Icons.close),
                            onPressed: () =>
                                _run(context, ref, (s) => s.removeLine(line)),
                          ),
                    onTap: locked
                        ? null
                        : () => _changeSource(context, ref, line),
                  ),
              ],
              if (v.needsDiscussion && !locked)
                _DiscussionCard(
                  view: v,
                  onMark: (m) => _mark(context, ref, v, m),
                ),
              const SizedBox(height: 12),
              if (locked) ...[
                Text(l10n.ceremonyLocked, key: const Key('ceremony-locked')),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    key: const Key('ceremony-reopen'),
                    onPressed: () =>
                        _run(context, ref, (s) => s.reopen(v.plan)),
                    child: Text(l10n.ceremonyReopen),
                  ),
                ),
              ] else ...[
                if (v.needsDiscussion &&
                    v.plan.status != CeremonyStatus.discussed)
                  Text(
                    l10n.ceremonyConfirmBlocked,
                    key: const Key('ceremony-confirm-blocked'),
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                FilledButton(
                  key: const Key('ceremony-confirm'),
                  onPressed: v.canConfirm
                      ? () => _confirm(context, ref, v)
                      : null,
                  child: Text(l10n.ceremonyConfirm),
                ),
              ],
              const SizedBox(height: 16),
              _GiftCard(
                view: v,
                onCreate: () => _createGift(context, ref, v),
                onAdd: () => _addContribution(context, ref, v),
                onShare: () => _shareGift(context, v),
              ),
            ],
          );
        }(),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _ScenarioCard extends StatelessWidget {
  const _ScenarioCard({
    required this.summary,
    required this.isSelected,
    required this.locked,
    required this.canRemove,
    required this.onSelect,
    required this.onGuests,
    required this.onRemove,
  });

  final ScenarioSummary summary;
  final bool isSelected;
  final bool locked;
  final bool canRemove;
  final VoidCallback onSelect;
  final VoidCallback onGuests;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final s = summary;
    final id = s.scenario.meta.id;
    final payoff = s.debtPayoff;
    return Card(
      key: Key('scenario-$id'),
      shape: isSelected
          ? RoundedRectangleBorder(
              side: BorderSide(color: theme.colorScheme.primary, width: 2),
              borderRadius: BorderRadius.circular(12),
            )
          : null,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    s.scenario.name,
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                ActionChip(
                  key: Key('scenario-guests-$id'),
                  avatar: const Icon(Icons.chair_outlined, size: 18),
                  label: Text(l10n.ceremonyGuests(s.scenario.guests)),
                  onPressed: locked ? null : onGuests,
                ),
              ],
            ),
            Text(
              l10n.scenarioTotal(money(s.total)),
              key: Key('scenario-total-$id'),
              style: theme.textTheme.titleMedium,
            ),
            Text(
              s.hasDebt
                  ? l10n.scenarioDebt(money(s.debt))
                  : l10n.scenarioNoDebt,
              style: TextStyle(
                color: s.hasDebt
                    ? theme.colorScheme.error
                    : theme.colorScheme.primary,
              ),
            ),
            if (s.hasDebt)
              Text(
                s.debtNeverEnds
                    ? l10n.scenarioPayoffNever
                    : payoff == null
                    ? l10n.scenarioPayoffUnknown
                    : [
                        l10n.scenarioPayoff(
                          payoff.months,
                          formatDate(payoff.endDate!),
                        ),
                        if (s.debtOverpayment.isPositive)
                          l10n.scenarioPayoffInterest(
                            money(s.debtOverpayment),
                          ),
                      ].join(' · '),
                key: Key('scenario-payoff-$id'),
                style: theme.textTheme.bodySmall,
              ),
            for (final (g, bp) in s.goalShares.take(2))
              Text(
                l10n.scenarioGoal(g.title, percentLabel(bp)),
                style: theme.textTheme.bodySmall,
              ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (!locked && canRemove)
                  TextButton(
                    key: Key('scenario-remove-$id'),
                    onPressed: onRemove,
                    child: Text(l10n.scenarioRemove),
                  ),
                if (isSelected)
                  Chip(
                    avatar: const Icon(Icons.check, size: 18),
                    label: Text(l10n.scenarioSelected),
                  )
                else if (!locked)
                  FilledButton.tonal(
                    key: Key('scenario-select-$id'),
                    onPressed: onSelect,
                    child: Text(l10n.scenarioSelect),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// «Buni qarzsiz qanday o'tkazamiz?» — savollar va kattalar belgisi.
class _DiscussionCard extends StatelessWidget {
  const _DiscussionCard({required this.view, required this.onMark});

  final CeremonyView view;
  final void Function(Member) onMark;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final questions = [
      l10n.discussionQ1,
      l10n.discussionQ2,
      l10n.discussionQ3,
      l10n.discussionQ4,
      l10n.discussionQ5,
    ];
    return Card(
      key: const Key('discussion-card'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.discussionTitle, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(l10n.discussionHint),
            const SizedBox(height: 8),
            for (final q in questions)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('•  '),
                    Expanded(child: Text(q)),
                  ],
                ),
              ),
            const Divider(),
            for (final m in view.adults)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: CircleAvatar(
                  child: Text(l10n.member(m).characters.first.toUpperCase()),
                ),
                title: Text(l10n.member(m)),
                trailing: view.markedBy.contains(m.meta.id)
                    ? Chip(
                        avatar: const Icon(Icons.check, size: 18),
                        label: Text(l10n.discussionMarked),
                      )
                    : FilledButton.tonal(
                        key: Key('discuss-${m.meta.id}'),
                        onPressed: () => onMark(m),
                        child: Text(l10n.discussionMark),
                      ),
              ),
            if (view.plan.status == CeremonyStatus.discussed)
              Text(
                l10n.discussionDone,
                style: TextStyle(color: theme.colorScheme.primary),
              ),
          ],
        ),
      ),
    );
  }
}

/// To'yona o'rniga jamg'arma (yosh oila maqsadi).
class _GiftCard extends StatelessWidget {
  const _GiftCard({
    required this.view,
    required this.onCreate,
    required this.onAdd,
    required this.onShare,
  });

  final CeremonyView view;
  final VoidCallback onCreate;
  final VoidCallback onAdd;
  final VoidCallback onShare;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final goal = view.giftGoal;
    return Card(
      key: const Key('gift-card'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.giftTitle, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(l10n.giftHint, style: theme.textTheme.bodySmall),
            const SizedBox(height: 8),
            if (goal == null)
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.tonal(
                  key: const Key('gift-create'),
                  onPressed: onCreate,
                  child: Text(l10n.giftCreate),
                ),
              )
            else ...[
              Text(goal.title, style: theme.textTheme.titleSmall),
              Text(
                l10n.giftProgress(
                  money(view.giftCollected),
                  money(goal.target),
                ),
                key: const Key('gift-progress'),
              ),
              const SizedBox(height: 4),
              LinearProgressIndicator(
                value: goal.target.isPositive
                    ? (view.giftCollected.minorUnits / goal.target.minorUnits)
                          .clamp(0, 1)
                          .toDouble()
                    : 0,
              ),
              for (final c in view.giftContributions)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(c.contributorName),
                  subtitle: Text(formatDate(c.receivedOn)),
                  trailing: Text(money(c.amount)),
                ),
              Wrap(
                spacing: 8,
                children: [
                  OutlinedButton.icon(
                    key: const Key('gift-add'),
                    icon: const Icon(Icons.add),
                    label: Text(l10n.giftAddContribution),
                    onPressed: onAdd,
                  ),
                  OutlinedButton.icon(
                    key: const Key('gift-share'),
                    icon: const Icon(Icons.ios_share),
                    label: Text(l10n.giftShare),
                    onPressed: onShare,
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Yangi byudjet qatori: nomi, turi (bir martalik / kishi boshiga), manba.
class _LineDialog extends StatefulWidget {
  const _LineDialog();

  @override
  State<_LineDialog> createState() => _LineDialogState();
}

class _LineDialogState extends State<_LineDialog> {
  final _title = TextEditingController();
  CeremonyLineKind _kind = CeremonyLineKind.oneTime;
  FundingSource _source = FundingSource.savings;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.lineAdd),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              key: const Key('line-title'),
              controller: _title,
              autofocus: true,
              decoration: InputDecoration(labelText: l10n.lineTitle),
              inputFormatters: [LengthLimitingTextInputFormatter(60)],
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                for (final (k, label) in [
                  (CeremonyLineKind.oneTime, l10n.lineOneTime),
                  (CeremonyLineKind.perGuest, l10n.linePerGuest),
                ])
                  ChoiceChip(
                    key: Key('line-kind-${k.name}'),
                    label: Text(label),
                    selected: _kind == k,
                    onSelected: (_) => setState(() => _kind = k),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Text(l10n.lineSourceTitle),
            Wrap(
              spacing: 8,
              children: [
                for (final f in FundingSource.values)
                  ChoiceChip(
                    key: Key('line-source-${f.name}'),
                    label: Text(l10n.fundingSource(f)),
                    selected: _source == f,
                    onSelected: (_) => setState(() => _source = f),
                  ),
              ],
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
          key: const Key('line-save'),
          onPressed: _title.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (
                  _title.text.trim(),
                  _kind,
                  _source,
                )),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
