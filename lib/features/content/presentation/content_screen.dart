import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Boblar ro'yxati: ochiq va yopiq (ochilish sanasi bilan).
class ContentScreen extends ConsumerWidget {
  const ContentScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final lang = Localizations.localeOf(context).languageCode;
    final list = ref.watch(chapterListProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.contentTitle),
        actions: const [SettingsActions()],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const ContentDisclaimer(),
              const SizedBox(height: 8),
              switch (list) {
                AsyncData(:final value) when value.isEmpty => Text(
                  l10n.contentLoadError,
                  key: const Key('content-error'),
                ),
                AsyncData(:final value) => Card(
                  child: Column(
                    children: [
                      for (final (i, v) in value.indexed) ...[
                        if (i > 0) const Divider(height: 1),
                        ListTile(
                          key: Key('chapter-${v.chapter.id}'),
                          enabled: v.unlocked,
                          leading: CircleAvatar(
                            child: Text('${v.chapter.order}'),
                          ),
                          title: Text(v.chapter.title.of(lang)),
                          subtitle: Text(
                            v.unlocked
                                ? l10n.lawLabel(v.chapter.law.number)
                                : switch (v.unlockDate) {
                                    final date? => l10n.chapterLocked(
                                      formatDate(date),
                                    ),
                                    null => l10n.chapterLockedTasks(
                                      v.tasksRemaining,
                                    ),
                                  },
                          ),
                          trailing: Icon(
                            v.unlocked ? Icons.chevron_right : Icons.lock_clock,
                          ),
                          onTap: v.unlocked
                              ? () => context.push(
                                  AppRoutes.chapter(v.chapter.id),
                                )
                              : null,
                        ),
                      ],
                    ],
                  ),
                ),
                AsyncError() => Text(l10n.contentLoadError),
                _ => const Center(child: CircularProgressIndicator()),
              },
            ],
          ),
        ),
      ),
    );
  }
}
