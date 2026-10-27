import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/fx_rate.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:meta/meta.dart';

/// Bazada saqlangan kurs snapshoti.
@immutable
final class StoredFxRate implements Synced {
  const StoredFxRate({required this.meta, required this.rate});

  @override
  final SyncMeta meta;
  final FxRate rate;

  StoredFxRate copyWith({SyncMeta? meta, FxRate? rate}) =>
      StoredFxRate(meta: meta ?? this.meta, rate: rate ?? this.rate);

  @override
  bool operator ==(Object other) =>
      other is StoredFxRate && other.meta == meta && other.rate == rate;

  @override
  int get hashCode => Object.hash(meta, rate);
}

abstract interface class FxRateRepository
    implements SyncedRepository<StoredFxRate> {
  /// Eng so'nggi sanadagi kurs; bir sanada bir nechta bo'lsa — oxirgi
  /// kiritilgani.
  Future<StoredFxRate?> latest(
    String householdId,
    CurrencyCode from,
    CurrencyCode to,
  );
}
