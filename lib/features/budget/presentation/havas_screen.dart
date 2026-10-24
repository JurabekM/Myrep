import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/text_prompt.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/budget/domain/budget.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/budget/domain/havas_service.dart';
import 'package:baraka_daftari/features/budget/presentation/rollup_card.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/presentation/member_pin_prompt.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:baraka_daftari/features/prices/data/price_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

/// Hafta kuni nomi (joriy tilda): 5 → «juma».
String weekdayName(BuildContext context, int weekday) {
  // 2026-10-05 — dushanba.
  final date = DateTime(2026, 10, 4 + weekday);
  return DateFormat.EEEE(
    Localizations.localeOf(context).languageCode,
  ).format(date);
}

/// Haftalik eslatmalar (WorkManager): faol shirinliklar va «Narx daftari»
/// (savatda mahsulot bo'lsa — har shanba, SPEC 2C.1).
Future<void> syncTreatReminders(WidgetRef ref, AppLocalizations l10n) async {
  try {
    final service = await ref.read(insightsServiceProvider.future);
    final prices = await (await ref.read(
      priceBookServiceProvider.future,
    )).overview();
    final list = [
      if (prices.items.isNotEmpty)
        TreatReminder(
          id: 'price_book',
          weekday: DateTime.saturday,
          title: l10n.priceReminderTitle,
          body: l10n.priceReminderBody,
        ),
      for (final t in await service.treats())
        if (t.isActive)
          TreatReminder(
            id: t.meta.id,
            weekday: t.weekday,
            title: l10n.treatNotifTitle(t.title),
            body: l10n.treatNotifBody,
          ),
    ];
    await ref.read(reminderApiProvider).syncTreats(list, l10n.treatChannel);
  } on Object {
    AppLog.event('treat_sync_failed');
  }
}

/// Havas chegarasi (oilaviy kelishuv), isrof tahlili, «Juma shirinligi» va
/// odatlar (SPEC 2B.3, 2B.4, 2B.8, 2B.9).
class HavasScreen extends ConsumerWidget {
  const HavasScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final overview = ref.watch(havasOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.havasTitle)),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: switch (overview) {
            AsyncData(:final value) => ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                Text(l10n.havasRule),
                const SizedBox(height: 8),
                HavasStatusCard(overview: value),
                if (value.pending != null) ...[
                  const SizedBox(height: 8),
                  _ProposalCard(proposal: value.pending!),
                ],
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    key: const Key('havas-propose'),
                    icon: const Icon(Icons.edit_note),
                    label: Text(l10n.havasPropose),
                    onPressed: () => _propose(context, ref),
                  ),
                ),
                const SizedBox(height: 12),
                _AnalysisCard(overview: value),
                const SizedBox(height: 12),
                const _TreatsCard(),
                const SizedBox(height: 12),
                const _HabitsCard(),
                const SizedBox(height: 12),
                const RollupCard(),
              ],
            ),
            AsyncError() => Center(child: Text(l10n.genericError)),
            _ => const Center(child: CircularProgressIndicator()),
          },
        ),
      ),
    );
  }

  Future<void> _propose(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final amount = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: l10n.havasProposeTitle,
    );
    if (amount == null || !amount.isPositive) return;
    try {
      await (await ref.read(havasServiceProvider.future)).propose(amount);
      ref.invalidate(havasOverviewProvider);
    } on Object {
      AppLog.event('havas_propose_failed');
    }
  }
}

/// Holat: sarflangan / chegara, 80 % va 100 % da yumshoq ogohlantirish.
/// Rang neytral (qizil emas).
class HavasStatusCard extends StatelessWidget {
  const HavasStatusCard({required this.overview, super.key});

  final HavasOverview overview;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final usage = overview.usage;
    return Card(
      key: const Key('havas-status'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (usage == null) ...[
              Text(l10n.havasNoLimit),
              const SizedBox(height: 4),
              Text(
                l10n.havasSpent(money(overview.spent)),
                style: theme.textTheme.titleMedium,
              ),
            ] else ...[
              Text(
                l10n.havasOfLimit(money(usage.spent), money(usage.limit)),
                key: const Key('havas-of-limit'),
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              LinearProgressIndicator(
                value: (usage.basisPoints / 10000).clamp(0, 1).toDouble(),
                minHeight: 8,
                borderRadius: BorderRadius.circular(4),
                color: theme.colorScheme.tertiary,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
              ),
              const SizedBox(height: 8),
              Text(
                switch (usage.level) {
                  LimitLevel.ok => l10n.havasOk(money(usage.remaining)),
                  LimitLevel.near => l10n.havasNear(
                    percentLabel(usage.basisPoints),
                  ),
                  LimitLevel.over => l10n.havasOver(
                    money(usage.remaining.abs()),
                  ),
                },
                key: Key('havas-level-${usage.level.name}'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ProposalCard extends ConsumerWidget {
  const _ProposalCard({required this.proposal});

  final LimitProposal proposal;

  Future<void> _consent(
    BuildContext context,
    WidgetRef ref,
    Member member,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    var pin = '';
    if (member.hasPersonalPin) {
      final entered = await showMemberPinPrompt(
        context,
        name: l10n.member(member),
        okLabel: l10n.havasConsent,
      );
      if (entered == null) return;
      pin = entered;
    }
    try {
      final service = await ref.read(havasServiceProvider.future);
      final (check, agreed) = await service.consent(
        proposal.limit,
        member,
        pin,
      );
      final text = switch (check) {
        PinAccepted() when agreed => l10n.havasAgreed,
        PinAccepted() => l10n.havasConsentSaved(l10n.member(member)),
        PinRejected(:final attemptsBeforeLockout) => l10n.pinWrong(
          attemptsBeforeLockout,
        ),
        PinLockedOut() => l10n.pinErrorGeneric,
      };
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(text)));
      if (agreed) await recordTaskEvent(ref, TaskTrigger.havasLimitAgreed);
      ref.invalidate(havasOverviewProvider);
    } on Object {
      AppLog.event('havas_consent_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final consented = proposal.consentedBy;
    return Card(
      key: const Key('havas-pending'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.havasPending(context.money(proposal.limit.amount))),
            const SizedBox(height: 8),
            for (final m in proposal.adults)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: CircleAvatar(
                  child: Text(l10n.member(m).characters.first.toUpperCase()),
                ),
                title: Text(l10n.member(m)),
                trailing: consented.contains(m.meta.id)
                    ? Chip(
                        avatar: const Icon(Icons.check, size: 18),
                        label: Text(l10n.havasConsented),
                      )
                    : FilledButton.tonal(
                        key: Key('consent-${m.meta.id}'),
                        onPressed: () => _consent(context, ref, m),
                        child: Text(l10n.havasConsent),
                      ),
              ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                key: const Key('havas-withdraw'),
                onPressed: () async {
                  await (await ref.read(
                    havasServiceProvider.future,
                  )).withdraw(proposal.limit);
                  ref.invalidate(havasOverviewProvider);
                },
                child: Text(l10n.havasWithdraw),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AnalysisCard extends StatelessWidget {
  const _AnalysisCard({required this.overview});

  final HavasOverview overview;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    final debt = overview.debtFundedHavas.isEmpty
        ? null
        : Money.sum(
            overview.debtFundedHavas.map((e) => e.amount),
            overview.spent.currency,
          );
    Widget row(String label, Money amount, {Widget? leading, Key? key}) =>
        ListTile(
          key: key,
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: leading,
          title: Text(label),
          trailing: Text(money(amount), style: theme.textTheme.titleSmall),
        );
    return Card(
      key: const Key('havas-analysis'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.analysisTitle, style: theme.textTheme.titleMedium),
            if (debt != null)
              row(
                l10n.analysisDebtHavas,
                debt,
                key: const Key('analysis-debt'),
                leading: Icon(Icons.flag, color: theme.colorScheme.error),
              ),
            row(
              l10n.analysisOstentation,
              overview.ostentation,
              key: const Key('analysis-ostentation'),
              leading: const Icon(Icons.visibility_outlined),
            ),
            row(
              l10n.analysisGifts,
              overview.gifts,
              leading: const Icon(Icons.card_giftcard),
            ),
            row(
              l10n.analysisSadaqa,
              overview.sadaqa,
              key: const Key('analysis-sadaqa'),
              leading: const Icon(Icons.favorite_outline),
            ),
          ],
        ),
      ),
    );
  }
}

class _TreatsCard extends ConsumerWidget {
  const _TreatsCard();

  Future<void> _add(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final result = await showDialog<(String, int)>(
      context: context,
      builder: (_) => _TreatDialog(defaultTitle: l10n.treatTitleDefault),
    );
    if (result == null || !context.mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: result.$1,
    );
    if (amount == null || !amount.isPositive) return;
    try {
      await (await ref.read(insightsServiceProvider.future)).addTreat(
        title: result.$1,
        amount: amount,
        weekday: result.$2,
      );
      ref.invalidate(treatsProvider);
      await syncTreatReminders(ref, l10n);
    } on Object {
      AppLog.event('treat_add_failed');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final treats = ref.watch(treatsProvider).valueOrNull ?? const [];
    return Card(
      key: const Key('treats-card'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.cake_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.treatsTitle,
                    style: theme.textTheme.titleMedium,
                  ),
                ),
                TextButton(
                  key: const Key('treat-add'),
                  onPressed: () => _add(context, ref),
                  child: Text(l10n.treatAdd),
                ),
              ],
            ),
            Text(l10n.treatsHint, style: theme.textTheme.bodySmall),
            for (final ScheduledTreat t in treats)
              SwitchListTile(
                key: Key('treat-${t.meta.id}'),
                contentPadding: EdgeInsets.zero,
                title: Text(t.title),
                subtitle: Text(
                  l10n.treatLine(
                    weekdayName(context, t.weekday),
                    context.money(t.amount),
                  ),
                ),
                value: t.isActive,
                onChanged: (on) async {
                  await (await ref.read(
                    insightsServiceProvider.future,
                  )).setTreatActive(t, on: on);
                  ref.invalidate(treatsProvider);
                  await syncTreatReminders(ref, l10n);
                },
              ),
          ],
        ),
      ),
    );
  }
}

class _TreatDialog extends StatefulWidget {
  const _TreatDialog({required this.defaultTitle});

  final String defaultTitle;

  @override
  State<_TreatDialog> createState() => _TreatDialogState();
}

class _TreatDialogState extends State<_TreatDialog> {
  late final _title = TextEditingController(text: widget.defaultTitle);
  int _weekday = DateTime.friday;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.treatAdd),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: const Key('treat-title'),
            controller: _title,
            decoration: InputDecoration(labelText: l10n.titleLabel),
          ),
          const SizedBox(height: 8),
          DropdownButton<int>(
            key: const Key('treat-weekday'),
            isExpanded: true,
            value: _weekday,
            items: [
              for (var d = DateTime.monday; d <= DateTime.sunday; d++)
                DropdownMenuItem(
                  value: d,
                  child: Text(weekdayName(context, d)),
                ),
            ],
            onChanged: (d) => setState(() => _weekday = d ?? _weekday),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('treat-next'),
          onPressed: _title.text.trim().isEmpty
              ? null
              : () => Navigator.pop(context, (_title.text.trim(), _weekday)),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

class _HabitsCard extends ConsumerWidget {
  const _HabitsCard();

  Future<void> _add(BuildContext context, WidgetRef ref) async {
    final l10n = context.l10n;
    final title = await showTextPrompt(
      context,
      title: l10n.habitAdd,
      label: l10n.titleLabel,
      fieldKey: const Key('habit-title'),
      okKey: const Key('habit-save'),
    );
    if (title == null || title.trim().isEmpty) return;
    await (await ref.read(insightsServiceProvider.future)).addHabit(title);
    ref.invalidate(habitStatsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final habits = ref.watch(habitStatsProvider).valueOrNull ?? const [];
    return Card(
      key: const Key('habits-card'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.insights_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.habitsTitle,
                    style: theme.textTheme.titleMedium,
                  ),
                ),
                TextButton(
                  key: const Key('habit-add'),
                  onPressed: () => _add(context, ref),
                  child: Text(l10n.habitAdd),
                ),
              ],
            ),
            Text(l10n.habitsHint, style: theme.textTheme.bodySmall),
            for (final h in habits)
              ListTile(
                key: Key('habit-row-${h.subject.meta.id}'),
                contentPadding: EdgeInsets.zero,
                title: Text(h.subject.title),
                subtitle: Text(
                  l10n.habitLine(
                    money(h.rollup.perMonth),
                    money(h.rollup.perYear),
                  ),
                ),
                trailing: IconButton(
                  tooltip: l10n.habitArchive,
                  icon: const Icon(Icons.archive_outlined),
                  onPressed: () async {
                    await (await ref.read(
                      insightsServiceProvider.future,
                    )).archiveHabit(h.subject);
                    refreshMoneyViews(ref);
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
