import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'income.freezed.dart';

/// Daromad (SPEC 2.1): manba, kanal, sana va oila a'zosi.
@freezed
abstract class Income with _$Income implements Synced {
  const factory Income({
    required SyncMeta meta,
    required Money amount,
    required IncomeSource source,
    required PaymentChannel channel,

    /// UTC.
    required DateTime receivedAt,
    String? memberId,

    /// «Ter / mol / tavakkal» (ixtiyoriy).
    IncomeSourceType? sourceType,
    String? note,
  }) = _Income;
}

abstract interface class IncomeRepository implements SyncedRepository<Income> {
  Future<List<Income>> listInRange(String householdId, DateRange range);

  /// Oxirgi kiritilgan daromad — tez kiritishda manba va kanalni oldindan
  /// tanlash uchun.
  Future<Income?> latest(String householdId);

  /// Oxirgi turli summalar (eng yangisi birinchi) — tez kiritish chip'lari.
  Future<List<Money>> recentAmounts(String householdId, {int limit = 3});
}
