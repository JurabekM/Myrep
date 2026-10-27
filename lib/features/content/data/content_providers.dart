import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/content/data/drift_content_repositories.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/domain/content_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'content_providers.g.dart';

const contentAsset = 'assets/content/chapters.json';

/// Kontent manbasi (testlarda almashtiriladi). `ContentService` natijani
/// o'zi keshlaydi; bundle keshi o'chiq — keshlangan Future eski zonaga
/// bog'lanib qolmasin (testlarda ketma-ket osilish shundan edi).
@Riverpod(keepAlive: true)
Future<String> Function() contentSource(Ref ref) =>
    () => rootBundle.loadString(contentAsset, cache: false);

/// Tasdiqlanmagan diniy bloklar faqat debug/profile'da (kontent tekshiruvi
/// uchun) ko'rinadi; release'da hech qachon (SPEC 3).
@Riverpod(keepAlive: true)
bool showPendingReligious(Ref ref) => !kReleaseMode;

@Riverpod(keepAlive: true)
Future<ContentService> contentService(Ref ref) async {
  final db = await ref.watch(appDatabaseProvider.future);
  final clock = ref.watch(clockProvider);
  return ContentService(
    loadJson: ref.watch(contentSourceProvider),
    households: await ref.watch(householdRepositoryProvider.future),
    pages: DriftDaftarPageRepository(db, clock),
    completions: DriftTaskCompletionRepository(db, clock),
    metaFactory: ref.watch(syncMetaFactoryProvider),
    clock: clock,
  );
}

@riverpod
Future<List<ChapterView>> chapterList(Ref ref) async =>
    (await ref.watch(contentServiceProvider.future)).chapters();

@riverpod
Future<WeekTasks?> weekTasks(Ref ref) async =>
    (await ref.watch(contentServiceProvider.future)).thisWeek();

/// Ilova hodisasi → mos haftalik vazifa avtomatik belgilanadi.
Future<void> recordTaskEvent(WidgetRef ref, TaskTrigger trigger) async {
  try {
    final marked = await (await ref.read(
      contentServiceProvider.future,
    )).recordEvent(trigger);
    if (marked.isNotEmpty) ref.invalidate(weekTasksProvider);
  } on Object {
    // Vazifa belgilanmasa ham asosiy amal davom etadi.
  }
}
