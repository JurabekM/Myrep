import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:meta/meta.dart';

/// Tez kiritish ekrani uchun oldindan tanlangan qiymatlar.
@immutable
final class IncomeDefaults {
  const IncomeDefaults({
    required this.currency,
    required this.source,
    required this.channel,
    required this.recentAmounts,
  });

  final CurrencyCode currency;
  final IncomeSource source;
  final PaymentChannel channel;
  final List<Money> recentAmounts;
}

/// Daromadni tez kiritish (SPEC 2.1).
class IncomeService {
  IncomeService({
    required HouseholdRepository households,
    required IncomeRepository incomes,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _incomes = incomes,
       _meta = metaFactory,
       _clock = clock;

  static const errNotPositive = 'income_amount_must_be_positive';

  final HouseholdRepository _households;
  final IncomeRepository _incomes;
  final SyncMetaFactory _meta;
  final Clock _clock;

  /// Oxirgi manba va kanal oldindan tanlanadi; birinchi marta — kunlik ish,
  /// naqd.
  Future<IncomeDefaults> defaults() async {
    final household = await _households.current();
    final hh = household.meta.id;
    final last = await _incomes.latest(hh);
    return IncomeDefaults(
      currency: household.baseCurrency,
      // Birinchi daromad — onboarding'dagi daromad turiga ko'ra.
      source:
          last?.source ??
          switch (household.incomeKind) {
            IncomeKind.orders => IncomeSource.order,
            IncomeKind.salary => IncomeSource.salary,
            IncomeKind.dailyCash || null => IncomeSource.dailyWork,
          },
      channel:
          last?.channel ??
          (household.incomeKind == IncomeKind.salary
              ? PaymentChannel.card
              : PaymentChannel.cash),
      recentAmounts: await _incomes.recentAmounts(hh),
    );
  }

  Future<Income> add({
    required Money amount,
    required IncomeSource source,
    required PaymentChannel channel,
    String? memberId,

    /// Audit uchun o'tgan sana; standart — hozir.
    DateTime? receivedAt,

    /// «Ter / mol / tavakkal» testi (SPEC 2C.5), ixtiyoriy.
    IncomeSourceType? sourceType,
  }) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final household = await _households.current();
    return _incomes.add(
      Income(
        meta: _meta.create(household.meta.id),
        amount: amount,
        source: source,
        channel: channel,
        memberId: memberId,
        receivedAt: receivedAt ?? _clock.nowUtc(),
        sourceType: sourceType,
      ),
    );
  }
}
