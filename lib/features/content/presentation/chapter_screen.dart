import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'chapter_screen.g.dart';

/// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
@riverpod
Future<Chapter?> chapterById(Ref ref, String id) async =>
    (await ref.watch(contentServiceProvider.future)).chapter(id);

@riverpod
Future<bool> hasDaftarPage(Ref ref, String chapterId) async =>
    await (await ref.watch(
      contentServiceProvider.future,
    )).daftarPage(chapterId) !=
    null;

/// Bob: matn, maslahatchi maslahati, qonun, «Daftar sahifasi»,
/// haftalik vazifalar.
class ChapterScreen extends ConsumerWidget {
  const ChapterScreen({required this.chapterId, super.key});

  final String chapterId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final chapter = ref.watch(chapterByIdProvider(chapterId));
    return Scaffold(
      appBar: AppBar(title: Text(l10n.contentTitle)),
      body: switch (chapter) {
        AsyncData(:final value?) => _ChapterBody(value),
        AsyncData() || AsyncError() => Center(
          child: Text(l10n.contentLoadError),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _ChapterBody extends ConsumerWidget {
  const _ChapterBody(this.c);

  final Chapter c;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final lang = Localizations.localeOf(context).languageCode;
    final theme = Theme.of(context);
    final showPending = ref.watch(showPendingReligiousProvider);
    final written = ref.watch(hasDaftarPageProvider(c.id)).valueOrNull ?? false;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(c.title.of(lang), style: theme.textTheme.headlineSmall),
            const ContentDisclaimer(),
            const SizedBox(height: 8),
            for (final b in c.visibleBlocks(showPendingReligious: showPending))
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: switch (b) {
                  ParagraphBlock(:final text) => Text(
                    text.of(lang),
                    style: theme.textTheme.bodyLarge,
                  ),
                  QuoteBlock(:final text) => Container(
                    padding: const EdgeInsets.fromLTRB(12, 4, 4, 4),
                    decoration: BoxDecoration(
                      border: Border(
                        left: BorderSide(
                          color: theme.colorScheme.primary,
                          width: 3,
                        ),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.tips_and_updates_outlined,
                              size: 18,
                              color: theme.colorScheme.primary,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              l10n.contentAdvisor,
                              key: const Key('advisor-label'),
                              style: theme.textTheme.labelLarge?.copyWith(
                                color: theme.colorScheme.primary,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          text.of(lang),
                          style: theme.textTheme.bodyLarge?.copyWith(
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    ),
                  ),
                  ReligiousBlock(:final text, :final source, :final status) =>
                    Card(
                      key: const Key('religious-block'),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (status == ReligiousReviewStatus.pending)
                              Text(
                                l10n.religiousPending,
                                key: const Key('religious-pending'),
                                style: theme.textTheme.labelSmall?.copyWith(
                                  color: theme.colorScheme.error,
                                ),
                              ),
                            Text(
                              text.of(lang),
                              style: theme.textTheme.bodyLarge,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              l10n.religiousSource(source.of(lang)),
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                },
              ),
            Card(
              color: theme.colorScheme.primaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.lawLabel(c.law.number),
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      c.law.text.of(lang),
                      key: const Key('law-text'),
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              key: const Key('open-daftar'),
              icon: Icon(written ? Icons.edit_note : Icons.draw_outlined),
              label: Text(
                written
                    ? '${l10n.daftarPageTitle} · ${l10n.daftarPageWritten}'
                    : l10n.daftarPageTitle,
              ),
              onPressed: () => context.push(AppRoutes.daftar(c.id)),
            ),
            const SizedBox(height: 16),
            const WeeklyTasksCard(),
          ],
        ),
      ),
    );
  }
}
