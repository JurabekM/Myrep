import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'budget.freezed.dart';

/// Havas uchun oylik chegara taklifi (SPEC 2B.3).
@freezed
abstract class HavasLimit with _$HavasLimit implements Synced {
  const factory HavasLimit({
    required SyncMeta meta,
    required Money amount,
    String? proposedBy,
  }) = _HavasLimit;
}

/// A'zoning chegaraga roziligi.
@freezed
abstract class LimitConsent with _$LimitConsent implements Synced {
  const factory LimitConsent({
    required SyncMeta meta,
    required String limitId,
    required String memberId,
  }) = _LimitConsent;
}

/// «Juma shirinligi» (SPEC 2B.4).
@freezed
abstract class ScheduledTreat with _$ScheduledTreat implements Synced {
  const factory ScheduledTreat({
    required SyncMeta meta,
    required String title,
    required Money amount,

    /// `DateTime.monday` … `DateTime.sunday`.
    @Default(DateTime.friday) int weekday,
    @Default(true) bool isActive,
  }) = _ScheduledTreat;
}

/// Kuzatiladigan odat (SPEC 2B.9) — faqat statistika.
@freezed
abstract class Habit with _$Habit implements Synced {
  const factory Habit({
    required SyncMeta meta,
    required String title,
    @Default(false) bool isArchived,
  }) = _Habit;
}

abstract interface class HavasLimitRepository
    implements SyncedRepository<HavasLimit> {}

abstract interface class LimitConsentRepository
    implements SyncedRepository<LimitConsent> {
  Future<List<LimitConsent>> forLimit(String limitId);
}

abstract interface class ScheduledTreatRepository
    implements SyncedRepository<ScheduledTreat> {}

abstract interface class HabitRepository implements SyncedRepository<Habit> {}
