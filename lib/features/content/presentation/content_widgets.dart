import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/domain/content_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Har bir ta'limiy ekranda (SPEC 3): «Ta'limiy material. Fatvo yoki
/// moliyaviy maslahat emas».
class ContentDisclaimer extends StatelessWidget {
  const ContentDisclaimer({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      key: const Key('content-disclaimer'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.info_outline,
            size: 18,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              context.l10n.contentDisclaimer,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Shu haftaning 3 ta vazifasi — checklist (bosh ekran va bob ekranida).
class WeeklyTasksCard extends ConsumerWidget {
  const WeeklyTasksCard({this.onOpenChapter, super.key});

  /// Bosh ekranda — bobga o'tish.
  final void Function(String chapterId)? onOpenChapter;

  Future<void> _toggle(
    WidgetRef ref,
    WeeklyTask t, {
    required bool done,
  }) async {
    try {
      await (await ref.read(
        contentServiceProvider.future,
      )).setTaskDone(t.id, done: done);
      ref.invalidate(weekTasksProvider);
    } on Object {
      AppLog.event('task_toggle_failed');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final lang = Localizations.localeOf(context).languageCode;
    final theme = Theme.of(context);
    final week = ref.watch(weekTasksProvider).valueOrNull;
    return Card(
      key: const Key('weekly-tasks'),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ListTile(
              leading: const Icon(Icons.checklist),
              title: Text(l10n.weeklyTasksTitle),
              subtitle: week == null
                  ? null
                  : Text(
                      '${week.chapter.title.of(lang)} · '
                      '${l10n.weeklyTasksProgress(_doneCount(week))}',
                    ),
              trailing: week != null && onOpenChapter != null
                  ? const Icon(Icons.chevron_right)
                  : null,
              onTap: week != null && onOpenChapter != null
                  ? () => onOpenChapter!(week.chapter.id)
                  : null,
            ),
            if (week != null)
              for (final t in week.chapter.weeklyTasks)
                CheckboxListTile(
                  key: Key('task-${t.id}'),
                  dense: true,
                  controlAffinity: ListTileControlAffinity.leading,
                  value: week.done.contains(t.id),
                  title: Text(t.text.of(lang)),
                  subtitle: t.trigger == null || !week.done.contains(t.id)
                      ? null
                      : Text(
                          l10n.taskAuto,
                          style: theme.textTheme.bodySmall,
                        ),
                  onChanged: (v) =>
                      unawaited(_toggle(ref, t, done: v ?? false)),
                ),
          ],
        ),
      ),
    );
  }

  static int _doneCount(WeekTasks w) =>
      w.chapter.weeklyTasks.where((t) => w.done.contains(t.id)).length;
}
