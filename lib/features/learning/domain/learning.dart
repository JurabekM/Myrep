import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'learning.freezed.dart';

/// «Bir soatim qancha turadi?» hisobi (`HourlySnapshot`, SPEC 2H.1).
@freezed
abstract class HourlySnapshot with _$HourlySnapshot implements Synced {
  const factory HourlySnapshot({
    required SyncMeta meta,
    required Money income,
    required int minutesPerDay,
    required int daysPerMonth,
    required int maxMinutesPerDay,

    /// Saqlangan paytdagi soat qiymati.
    required Money hourly,
    String? memberId,
  }) = _HourlySnapshot;

  const HourlySnapshot._();

  /// To'liq natija (chegara, band qism) — kirishdan qayta hisoblanadi.
  HourlyValue get value => hourlyValue(
    income: income,
    minutesPerDay: minutesPerDay,
    daysPerMonth: daysPerMonth,
    maxMinutesPerDay: maxMinutesPerDay,
  );
}

/// O'qish maqsadi (`LearningGoal`, SPEC 2H.2).
@freezed
abstract class LearningGoal with _$LearningGoal implements Synced {
  const factory LearningGoal({
    required SyncMeta meta,
    required String title,
    required Money baseHourly,
    required Money targetHourly,
    required LearningGoalStatus status,
    String? why,
    String? memberId,

    /// `DONE` yoki `DROPPED` bo'lgan vaqt (UTC).
    DateTime? closedAt,
  }) = _LearningGoal;
}

/// O'qish yo'li (`LearningItem`, SPEC 2H.3).
@freezed
abstract class LearningItem with _$LearningItem implements Synced {
  const factory LearningItem({
    required SyncMeta meta,
    required String goalId,
    required LearningItemKind kind,
    required String title,

    /// «Buni o'rgangach nimani qila olaman?»
    required String purpose,
    required LearningItemStatus status,
    Money? cost,
    int? studyMinutes,
    String? outcome,

    /// Kurs tekshiruvi (SPEC 2H.5): javoblar JSON va baho.
    String? courseAnswersJson,
    OfferVerdict? courseVerdict,

    /// `DONE` bo'lgan vaqt (UTC).
    DateTime? completedAt,
  }) = _LearningItem;

  const LearningItem._();

  /// Hisobga olinadi: tashlab ketilmagan yo'l.
  bool get counts => status != LearningItemStatus.dropped;
}

/// «O'rgatganlarim» yozuvi (`TeachingEntry`, SPEC 2H.6).
@freezed
abstract class TeachingEntry with _$TeachingEntry implements Synced {
  const factory TeachingEntry({
    required SyncMeta meta,
    required String learner,
    required String topic,
    required LocalDate taughtOn,
    int? minutes,
    String? note,
    String? memberId,
  }) = _TeachingEntry;
}

abstract interface class HourlySnapshotRepository
    implements SyncedRepository<HourlySnapshot> {}

abstract interface class LearningGoalRepository
    implements SyncedRepository<LearningGoal> {}

abstract interface class LearningItemRepository
    implements SyncedRepository<LearningItem> {
  /// Qo'shilish tartibida.
  Future<List<LearningItem>> forGoal(String goalId);
}

abstract interface class TeachingEntryRepository
    implements SyncedRepository<TeachingEntry> {}
