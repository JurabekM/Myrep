import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/learning/data/drift_learning_repositories.dart';
import 'package:baraka_daftari/features/learning/domain/learning.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:baraka_daftari/features/learning/domain/learning_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:meta/meta.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'learning_providers.g.dart';

@Riverpod(keepAlive: true)
Future<LearningService> learningService(Ref ref) async => LearningService(
  households: await ref.watch(householdRepositoryProvider.future),
  incomes: await ref.watch(incomeRepositoryProvider.future),
  snapshots: await ref.watch(hourlySnapshotRepositoryProvider.future),
  goals: await ref.watch(learningGoalRepositoryProvider.future),
  items: await ref.watch(learningItemRepositoryProvider.future),
  teachings: await ref.watch(teachingEntryRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

/// Maqsad, uning yo'llari va qoplanish taxmini.
@immutable
final class GoalView {
  const GoalView(this.goal, this.items, this.payback);

  final LearningGoal goal;
  final List<LearningItem> items;
  final SkillPayback? payback;
}

/// «Bilimga sarmoya» ekrani ma'lumoti (SPEC 2H).
@immutable
final class LearningOverview {
  const LearningOverview({
    required this.snapshots,
    required this.goals,
    required this.teachings,
  });

  /// Eng yangisi birinchi.
  final List<HourlySnapshot> snapshots;
  final List<GoalView> goals;
  final List<TeachingEntry> teachings;

  HourlySnapshot? get latest => snapshots.firstOrNull;
}

@riverpod
Future<LearningOverview> learningOverview(Ref ref) async {
  final s = await ref.watch(learningServiceProvider.future);
  return LearningOverview(
    snapshots: await s.snapshots(),
    goals: [
      for (final g in await s.goals())
        GoalView(g, await s.items(g.meta.id), await s.payback(g)),
    ],
    teachings: await s.teachings(),
  );
}
