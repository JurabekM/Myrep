import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/domain/rescue.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription.dart';

/// Obunalar auditi (SPEC 2B.5): yillik narx, «ishlatdim», unutilgan obuna,
/// bekor qilish → «Qutqarilgan pul».
class SubscriptionService {
  SubscriptionService({
    required HouseholdRepository households,
    required SubscriptionRepository subscriptions,
    required SavingsRescueRepository rescues,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _subscriptions = subscriptions,
       _rescues = rescues,
       _meta = metaFactory,
       _clock = clock;

  /// Shuncha kun «ishlatdim» belgilanmasa — unutilgan obuna.
  static const forgottenAfterDays = 30;
  static const errTitleRequired = 'subscription_title_required';
  static const errNotPositive = 'subscription_price_must_be_positive';
  static const errAlreadyCancelled = 'subscription_already_cancelled';

  final HouseholdRepository _households;
  final SubscriptionRepository _subscriptions;
  final SavingsRescueRepository _rescues;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  Future<List<Subscription>> list() async =>
      _subscriptions.listActive((await _households.current()).meta.id);

  Future<Subscription> add({
    required String title,
    required Money price,
    SubscriptionCycle cycle = SubscriptionCycle.monthly,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errTitleRequired);
    if (!price.isPositive) throw const DomainRuleException(errNotPositive);
    final hh = (await _households.current()).meta.id;
    return _subscriptions.add(
      Subscription(
        meta: _meta.create(hh),
        title: title.trim(),
        price: price,
        cycle: cycle,
        startedOn: today,
      ),
    );
  }

  /// «Ishlatdim» — unutilgan obuna ogohlantirishi tozalanadi.
  Future<Subscription> markUsed(Subscription s) =>
      _subscriptions.update(s.copyWith(lastUsedOn: today));

  /// Bekor qilish: oylik ekvivalenti «Qutqarilgan pul»ga yoziladi; yiliga
  /// [Subscription.yearly] tejaladi.
  Future<Subscription> cancel(Subscription s) async {
    if (!s.isActive) throw const DomainRuleException(errAlreadyCancelled);
    final cancelled = await _subscriptions.update(
      s.copyWith(cancelledOn: today),
    );
    await _rescues.add(
      SavingsRescue(
        meta: _meta.create(s.meta.householdId),
        kind: RescueKind.subscription,
        amount: s.monthly,
        occurredOn: today,
        sourceId: s.meta.id,
      ),
    );
    return cancelled;
  }

  bool isForgotten(Subscription s) =>
      s.isActive && s.daysSinceUse(today) >= forgottenAfterDays;

  /// Faol obunalarning yillik jami.
  static Money annualTotal(Iterable<Subscription> list, CurrencyCode c) =>
      Money.sum([
        for (final s in list)
          if (s.isActive && s.price.currency == c) s.yearly,
      ], c);
}
