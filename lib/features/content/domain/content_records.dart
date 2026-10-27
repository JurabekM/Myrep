import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'content_records.freezed.dart';

/// Foydalanuvchi o'z qo'li bilan yozgan qonun (SPEC 5: `DaftarPage`).
@freezed
abstract class DaftarPage with _$DaftarPage implements Synced {
  const factory DaftarPage({
    required SyncMeta meta,
    required String chapterId,
    required int lawNumber,
    required String body,
  }) = _DaftarPage;
}

/// Haftalik vazifa bajarilishi (SPEC 5: `TaskCompletion`).
@freezed
abstract class TaskCompletion with _$TaskCompletion implements Synced {
  const factory TaskCompletion({
    required SyncMeta meta,
    required String taskId,
    required LocalDate weekStart,
    @Default(false) bool isAuto,
  }) = _TaskCompletion;
}

abstract interface class DaftarPageRepository
    implements SyncedRepository<DaftarPage> {
  Future<DaftarPage?> forChapter(String householdId, String chapterId);
}

abstract interface class TaskCompletionRepository
    implements SyncedRepository<TaskCompletion> {
  Future<List<TaskCompletion>> forWeek(String householdId, LocalDate weekStart);

  /// Har vazifa birinchi marta qachon bajarilgan (o'chirilganlari ham —
  /// ochilgan bob qayta yopilmasligi uchun). UTC vaqt.
  Future<Map<String, DateTime>> firstCompletions(String householdId);
}
