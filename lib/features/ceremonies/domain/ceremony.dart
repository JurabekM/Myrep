import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'ceremony.freezed.dart';

/// Marosim rejasi (`CeremonyPlan`, SPEC 2D.8).
@freezed
abstract class CeremonyPlan with _$CeremonyPlan implements Synced {
  const factory CeremonyPlan({
    required SyncMeta meta,
    required String title,
    required CeremonyType type,
    required CurrencyCode currency,
    @Default(CeremonyStatus.draft) CeremonyStatus status,
    LocalDate? eventDate,
    String? selectedScenarioId,

    /// «To'yona o'rniga jamg'arma» maqsadi (`Goal`).
    String? giftGoalId,

    /// Qarz qismini oyiga qancha to'lay olamiz va yillik stavka (bp).
    Money? debtMonthly,
    int? debtAnnualRateBp,
  }) = _CeremonyPlan;
}

/// Stsenariy: «3 kunlik, 200 kishi», «1 kunlik, 100 kishi, ixcham».
@freezed
abstract class CeremonyScenario with _$CeremonyScenario implements Synced {
  const factory CeremonyScenario({
    required SyncMeta meta,
    required String planId,
    required String name,
    @Default(0) int guests,
    @Default(0) int sortOrder,
  }) = _CeremonyScenario;
}

/// Byudjet qatori: bir martalik summa yoki kishi boshiga narx.
@freezed
abstract class CeremonyBudgetLine with _$CeremonyBudgetLine implements Synced {
  const factory CeremonyBudgetLine({
    required SyncMeta meta,
    required String scenarioId,
    required String title,
    required CeremonyLineKind kind,
    required Money amount,
    required FundingSource source,
    @Default(0) int sortOrder,
  }) = _CeremonyBudgetLine;

  const CeremonyBudgetLine._();

  /// Qatorning jami narxi [guests] mehmon uchun.
  Money totalFor(int guests) =>
      kind == CeremonyLineKind.perGuest ? amount.times(guests) : amount;
}

/// Muhokamada katta a'zoning belgisi.
@freezed
abstract class CeremonyDiscussionMark
    with _$CeremonyDiscussionMark
    implements Synced {
  const factory CeremonyDiscussionMark({
    required SyncMeta meta,
    required String planId,
    required String memberId,
  }) = _CeremonyDiscussionMark;
}

/// Maqsadga hissa (to'yona o'rniga jamg'arma).
@freezed
abstract class GoalContribution with _$GoalContribution implements Synced {
  const factory GoalContribution({
    required SyncMeta meta,
    required String goalId,
    required String contributorName,
    required Money amount,
    required LocalDate receivedOn,
  }) = _GoalContribution;
}

abstract interface class CeremonyPlanRepository
    implements SyncedRepository<CeremonyPlan> {}

abstract interface class CeremonyScenarioRepository
    implements SyncedRepository<CeremonyScenario> {
  Future<List<CeremonyScenario>> forPlan(String planId);
}

abstract interface class CeremonyBudgetLineRepository
    implements SyncedRepository<CeremonyBudgetLine> {
  Future<List<CeremonyBudgetLine>> forScenario(String scenarioId);
}

abstract interface class CeremonyDiscussionMarkRepository
    implements SyncedRepository<CeremonyDiscussionMark> {
  Future<List<CeremonyDiscussionMark>> forPlan(String planId);
}

abstract interface class GoalContributionRepository
    implements SyncedRepository<GoalContribution> {
  Future<List<GoalContribution>> forGoal(String goalId);
}
