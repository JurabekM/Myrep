import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'vault.freezed.dart';

/// Qiymat saqlovchi (SPEC 4.3). «Kelajagim» — `type == vault`.
@freezed
abstract class Asset with _$Asset implements Synced {
  const factory Asset({
    required SyncMeta meta,
    required AssetType type,
    required QuantityUnit unit,

    /// UTC.
    required DateTime acquiredAt,

    /// Pul — minor birlik, oltin — milligramm.
    @Default(0) int quantity,
    CurrencyCode? currency,
    String? name,
    VaultType? vaultType,
  }) = _Asset;
}

/// Balans tarixidagi nuqta (zakot hawl'i uchun).
@freezed
abstract class AssetSnapshot with _$AssetSnapshot implements Synced {
  const factory AssetSnapshot({
    required SyncMeta meta,
    required String assetId,
    required int quantity,

    /// UTC.
    required DateTime takenAt,
  }) = _AssetSnapshot;
}

/// «Kelajagim» harakati: kirim yoki chiqim.
@freezed
abstract class VaultTransaction with _$VaultTransaction implements Synced {
  const factory VaultTransaction({
    required SyncMeta meta,
    required String vaultAssetId,
    required VaultTransactionType type,

    /// Doim musbat; yo'nalish [type] da.
    required Money amount,
    required VaultTransactionReason reason,

    /// UTC.
    required DateTime occurredAt,

    /// Pul olishda majburiy.
    String? reasonNote,
    String? incomeId,
    String? memberId,
  }) = _VaultTransaction;
}

/// Avto-ulush qoidasi: 5 % / 10 % (basis point) yoki qat'iy summa.
@freezed
abstract class AllocationRule with _$AllocationRule implements Synced {
  const factory AllocationRule({
    required SyncMeta meta,
    required String vaultAssetId,
    required AllocationMode mode,
    required CurrencyCode currency,
    int? basisPoints,

    /// Qat'iy summa — oyiga (masalan, 300 000 so'm).
    Money? fixedAmount,
    @Default(true) bool isActive,

    /// Progressiv rejimda oxirgi «+1 %» taklifi (UTC).
    DateTime? progressionOfferedAt,
  }) = _AllocationRule;
}

abstract interface class AssetRepository implements SyncedRepository<Asset> {
  Future<Asset?> findFirstOfType(String householdId, AssetType type);

  /// Barcha jamg'arma aktivlari (qorovul + o'sadigan).
  Future<List<Asset>> listVaults(String householdId);

  /// Jamg'arma aktivi turiga ko'ra; qorovul — eski (turi yo'q) aktiv ham.
  Future<Asset?> findVault(String householdId, VaultType type);

  Future<AssetSnapshot> addSnapshot(AssetSnapshot snapshot);

  Future<List<AssetSnapshot>> listSnapshots(String assetId);
}

abstract interface class VaultTransactionRepository
    implements SyncedRepository<VaultTransaction> {
  /// Kirimlar − chiqimlar (faqat faol yozuvlar).
  Future<Money> balance(String vaultAssetId, CurrencyCode currency);

  Future<List<VaultTransaction>> listForVault(String vaultAssetId);
}

abstract interface class AllocationRuleRepository
    implements SyncedRepository<AllocationRule> {
  Future<AllocationRule?> activeFor(String vaultAssetId);
}
