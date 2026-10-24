import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'subscription.freezed.dart';

/// Takroriy to'lov / obuna (SPEC 2B.5).
@freezed
abstract class Subscription with _$Subscription implements Synced {
  const factory Subscription({
    required SyncMeta meta,
    required String title,

    /// Bir davr narxi ([cycle] bo'yicha).
    required Money price,
    required SubscriptionCycle cycle,
    required LocalDate startedOn,
    LocalDate? lastUsedOn,
    LocalDate? cancelledOn,
  }) = _Subscription;

  const Subscription._();

  bool get isActive => cancelledOn == null;

  /// Oylik ekvivalent (yillik narx / 12).
  Money get monthly => monthlyEquivalent(price, cycle);

  /// Yillik narx — bekor qilinsa shuncha tejaladi.
  Money get yearly => yearlyCost(price, cycle);

  /// «Ishlatdim» belgisidan (yo'q bo'lsa — boshlangan kundan) beri kunlar.
  int daysSinceUse(LocalDate today) =>
      (lastUsedOn ?? startedOn).daysUntil(today);
}

Money monthlyEquivalent(Money price, SubscriptionCycle cycle) =>
    switch (cycle) {
      SubscriptionCycle.monthly => price,
      SubscriptionCycle.yearly => price.scaled(1, 12),
    };

Money yearlyCost(Money price, SubscriptionCycle cycle) => switch (cycle) {
  SubscriptionCycle.monthly => price.times(12),
  SubscriptionCycle.yearly => price,
};

abstract interface class SubscriptionRepository
    implements SyncedRepository<Subscription> {}
