import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/content/domain/chapter_unlock.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/domain/content_parser.dart';
import 'package:baraka_daftari/features/content/domain/content_records.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:meta/meta.dart';

@immutable
final class ChapterView {
  const ChapterView({
    required this.chapter,
    required this.unlocked,
    required this.unlockDate,
    this.tasksRemaining = 0,
    this.notBefore,
  });

  final Chapter chapter;
  final bool unlocked;

  /// `null` — sana hali aniq emas (oldingi bob vazifalari kutilmoqda).
  final LocalDate? unlockDate;

  /// Oldingi bobdan yana nechta vazifa bajarilishi kerak.
  final int tasksRemaining;

  /// Kun sharti bo'yicha eng erta ochilish sanasi.
  final LocalDate? notBefore;
}

/// Shu haftaning vazifalari (joriy — eng so'nggi ochilgan bob).
@immutable
final class WeekTasks {
  const WeekTasks({
    required this.chapter,
    required this.week,
    required this.done,
  });

  final Chapter chapter;
  final DateRange week;

  /// Bajarilgan vazifa ID'lari.
  final Set<String> done;
}

/// Kontent dvigateli: boblar, ochilish, «Daftar sahifasi», haftalik
/// vazifalar (SPEC 1.1, kickoff Vazifa 6).
class ContentService {
  ContentService({
    required Future<String> Function() loadJson,
    required HouseholdRepository households,
    required DaftarPageRepository pages,
    required TaskCompletionRepository completions,
    required SyncMetaFactory metaFactory,
    required Clock clock,
    this.unlockPolicy = const HabitUnlockPolicy(),
  }) : _loadJson = loadJson,
       _households = households,
       _pages = pages,
       _completions = completions,
       _meta = metaFactory,
       _clock = clock;

  final Future<String> Function() _loadJson;
  final HouseholdRepository _households;
  final DaftarPageRepository _pages;
  final TaskCompletionRepository _completions;
  final SyncMetaFactory _meta;
  final Clock _clock;
  final ChapterUnlockPolicy unlockPolicy;

  ContentLoadResult? _cached;

  /// Kontent (bir marta o'qiladi). Fayl o'qilmasa ham istisno tashlamaydi.
  Future<ContentLoadResult> content() async {
    final cached = _cached;
    if (cached != null) return cached;
    String json;
    try {
      json = await _loadJson();
    } on Object catch (e) {
      return _cached = ContentLoadResult(
        chapters: const [],
        errors: ['asset: ${e.runtimeType}'],
      );
    }
    return _cached = ContentParser.parse(json);
  }

  Future<UnlockContext> _context(Household h) async => UnlockContext(
    programStart: Tashkent.dateOf(h.meta.createdAt),
    today: Tashkent.dateOf(_clock.nowUtc()),
    calendar: h.calendar,
    taskFirstCompleted: {
      for (final MapEntry(:key, :value) in (await _completions.firstCompletions(
        h.meta.id,
      )).entries)
        key: Tashkent.dateOf(value),
    },
  );

  Future<List<ChapterView>> chapters() async {
    final h = await _households.current();
    final ctx = await _context(h);
    final list = (await content()).chapters;
    final unlocks = unlockPolicy.evaluate(list, ctx);
    return [
      for (final (i, c) in list.indexed)
        ChapterView(
          chapter: c,
          unlocked: unlocks[i].isUnlockedOn(ctx.today),
          unlockDate: unlocks[i].date,
          tasksRemaining: unlocks[i].tasksRemaining,
          notBefore: unlocks[i].notBefore,
        ),
    ];
  }

  Future<Chapter?> chapter(String id) async {
    for (final v in await chapters()) {
      if (v.chapter.id == id) return v.unlocked ? v.chapter : null;
    }
    return null;
  }

  /// Eng so'nggi ochilgan bob — shu haftaning vazifalari undan olinadi.
  Future<Chapter?> currentChapter() async {
    final open = [
      for (final v in await chapters())
        if (v.unlocked) v.chapter,
    ];
    return open.isEmpty ? null : open.last;
  }

  Future<WeekTasks?> thisWeek() async {
    final chapter = await currentChapter();
    if (chapter == null) return null;
    final h = await _households.current();
    final week = h.calendar.weekOf(Tashkent.dateOf(_clock.nowUtc()));
    final done = await _completions.forWeek(h.meta.id, week.start);
    return WeekTasks(
      chapter: chapter,
      week: week,
      done: {for (final d in done) d.taskId},
    );
  }

  /// Vazifani qo'lda belgilash / bekor qilish (shu hafta uchun).
  Future<void> setTaskDone(String taskId, {required bool done}) async {
    final h = await _households.current();
    final week = h.calendar.weekOf(Tashkent.dateOf(_clock.nowUtc()));
    final existing = await _completions.forWeek(h.meta.id, week.start);
    final matches = existing.where((c) => c.taskId == taskId).toList();
    if (done && matches.isEmpty) {
      await _completions.add(
        TaskCompletion(
          meta: _meta.create(h.meta.id),
          taskId: taskId,
          weekStart: week.start,
        ),
      );
    } else if (!done) {
      for (final m in matches) {
        await _completions.softDelete(m.meta.id);
      }
    }
  }

  /// Ilova hodisasi → joriy bobning mos vazifalari avtomatik belgilanadi.
  /// Belgilangan vazifalar ID'larini qaytaradi.
  Future<List<String>> recordEvent(TaskTrigger trigger) async {
    final week = await thisWeek();
    if (week == null) return const [];
    final hh = (await _households.current()).meta.id;
    final marked = <String>[];
    for (final t in week.chapter.weeklyTasks) {
      if (t.trigger != trigger || week.done.contains(t.id)) continue;
      await _completions.add(
        TaskCompletion(
          meta: _meta.create(hh),
          taskId: t.id,
          weekStart: week.week.start,
          isAuto: true,
        ),
      );
      marked.add(t.id);
    }
    return marked;
  }

  Future<DaftarPage?> daftarPage(String chapterId) async =>
      _pages.forChapter((await _households.current()).meta.id, chapterId);

  /// «Daftar sahifasi»ni saqlash (har bob uchun bitta, yangilanadi).
  Future<DaftarPage> saveDaftarPage(Chapter chapter, String body) async {
    final hh = (await _households.current()).meta.id;
    final existing = await _pages.forChapter(hh, chapter.id);
    if (existing == null) {
      return _pages.add(
        DaftarPage(
          meta: _meta.create(hh),
          chapterId: chapter.id,
          lawNumber: chapter.law.number,
          body: body,
        ),
      );
    }
    return _pages.update(existing.copyWith(body: body));
  }
}
