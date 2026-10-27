import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:baraka_daftari/features/learning/data/learning_providers.dart';
import 'package:baraka_daftari/features/learning/presentation/learning_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// «Bilimga sarmoya» (8-qonun, SPEC 2H): soat qiymati, o'qish maqsadlari,
/// «o'rgatganlarim» va «bilim odam bilan qoladi».
class LearningScreen extends ConsumerWidget {
  const LearningScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final data = ref.watch(learningOverviewProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.lnTitle)),
      body: switch (data) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Text(l10n.lnHint),
            const ContentDisclaimer(),
            _HourlyCard(overview: value),
            const SizedBox(height: 16),
            _GoalsSection(overview: value),
            const SizedBox(height: 16),
            _TeachingSection(overview: value),
            const SizedBox(height: 16),
            const _KeepCard(),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _HourlyCard extends ConsumerWidget {
  const _HourlyCard({required this.overview});

  final LearningOverview overview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final latest = overview.latest;
    final previous = overview.snapshots.length > 1
        ? overview.snapshots[1].hourly
        : null;
    return Card(
      key: const Key('ln-hourly-card'),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.lnHourlyTitle, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            if (latest == null)
              Text(l10n.lnHourlyEmpty)
            else
              HourlyResultView(value: latest.value, previous: previous),
            const SizedBox(height: 8),
            FilledButton.tonal(
              key: const Key('ln-hourly-open'),
              onPressed: () async {
                await context.push(AppRoutes.learningHourly);
                ref.invalidate(learningOverviewProvider);
              },
              child: Text(
                latest == null ? l10n.lnHourlyCalc : l10n.lnHourlyRecalc,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GoalsSection extends ConsumerWidget {
  const _GoalsSection({required this.overview});

  final LearningOverview overview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    final latest = overview.latest;
    final active = overview.goals
        .where((g) => g.goal.status == LearningGoalStatus.active)
        .length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                l10n.lnGoalsTitle,
                style: theme.textTheme.titleMedium,
              ),
            ),
            TextButton.icon(
              key: const Key('ln-goal-new'),
              icon: const Icon(Icons.add),
              label: Text(l10n.lnGoalNew),
              onPressed: latest == null
                  ? null
                  : () async {
                      final goal = await showLearningGoalDialog(
                        context,
                        ref,
                        baseHourly: latest.hourly,
                      );
                      if (goal != null && context.mounted) {
                        await context.push(
                          AppRoutes.learningGoal(goal.meta.id),
                        );
                        ref.invalidate(learningOverviewProvider);
                      }
                    },
            ),
          ],
        ),
        if (latest == null)
          Text(l10n.lnGoalsNeedHourly, key: const Key('ln-goals-need-hourly'))
        else if (overview.goals.isEmpty)
          Text(l10n.lnGoalsEmpty),
        if (active > 1)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(l10n.lnGoalFocus, style: theme.textTheme.bodySmall),
          ),
        for (final v in overview.goals)
          Card(
            child: ListTile(
              key: Key('ln-goal-${v.goal.meta.id}'),
              leading: Icon(
                v.goal.status == LearningGoalStatus.done
                    ? Icons.check_circle_outline
                    : Icons.school_outlined,
              ),
              title: Text(v.goal.title),
              subtitle: Text(
                [
                  l10n.lnGoalRange(
                    money(v.goal.baseHourly),
                    money(v.goal.targetHourly),
                  ),
                  l10n.lnGoalItems(v.items.where((i) => i.counts).length),
                  learningGoalStatusLabel(l10n, v.goal.status),
                ].join(' · '),
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await context.push(AppRoutes.learningGoal(v.goal.meta.id));
                ref.invalidate(learningOverviewProvider);
              },
            ),
          ),
      ],
    );
  }
}

class _TeachingSection extends StatelessWidget {
  const _TeachingSection({required this.overview});

  final LearningOverview overview;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                l10n.lnTeachTitle,
                style: theme.textTheme.titleMedium,
              ),
            ),
            TextButton.icon(
              key: const Key('ln-teach-add'),
              icon: const Icon(Icons.add),
              label: Text(l10n.lnTeachAdd),
              onPressed: () => showTeachingDialog(context),
            ),
          ],
        ),
        Text(l10n.lnTeachHint, style: theme.textTheme.bodySmall),
        if (overview.teachings.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(l10n.lnTeachEmpty),
          ),
        for (final t in overview.teachings.take(20))
          ListTile(
            key: Key('ln-teach-${t.meta.id}'),
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.forum_outlined),
            title: Text(t.topic),
            subtitle: Text(
              [
                t.learner,
                formatDate(t.taughtOn),
                if (t.minutes case final m?) l10n.lnItemHours(hoursLabel(m)),
                if (t.note case final n?) n,
              ].join(' · '),
            ),
          ),
      ],
    );
  }
}

/// «Bilim odam bilan qoladi» (SPEC 2H.7).
class _KeepCard extends StatelessWidget {
  const _KeepCard();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Card(
      key: const Key('ln-keep'),
      color: theme.colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.lnKeepTitle, style: theme.textTheme.titleSmall),
            const SizedBox(height: 4),
            Text(l10n.lnKeepBody),
          ],
        ),
      ),
    );
  }
}
