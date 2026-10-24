import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'partnership.freezed.dart';

/// Sheriklik (`Partnership`, SPEC 2E.1). Shartnomasiz yaratilmaydi.
@freezed
abstract class Partnership with _$Partnership implements Synced {
  const factory Partnership({
    required SyncMeta meta,
    required String title,
    required PartnershipType type,
    required CurrencyCode currency,
    required int termMonths,
    required ReportPeriod reportPeriod,
    required String endTerms,
    required String disputeTerms,
    @Default(PartnershipStatus.draft) PartnershipStatus status,
    LocalDate? startDate,
    @Default(1) int contractVersion,

    /// Kapital qabul qiluvchi: «bu qarz emas» tushuntirishi o'qildi.
    @Default(false) bool notDebtAcknowledged,

    /// Kamayib boruvchi musharaka: oyiga ulush sotib olish to'lovi.
    Money? buyoutMonthly,
  }) = _Partnership;
}

/// Sherik va uning roli.
@freezed
abstract class Partner with _$Partner implements Synced {
  const factory Partner({
    required SyncMeta meta,
    required String partnershipId,
    required String name,
    required PartnerRole role,
    required int profitShareBp,
    @Default(false) bool isMe,
    @Default(0) int sortOrder,
  }) = _Partner;

  const Partner._();

  bool get providesCapital =>
      role == PartnerRole.capitalProvider || role == PartnerRole.both;
}

/// Kiritilgan kapital: pul yoki narxlangan uskuna.
@freezed
abstract class CapitalContribution
    with _$CapitalContribution
    implements Synced {
  const factory CapitalContribution({
    required SyncMeta meta,
    required String partnershipId,
    required String partnerId,
    required CapitalKind kind,
    required String title,
    required Money amount,
  }) = _CapitalContribution;
}

/// Shartnoma versiyasi: shartlar surati (JSON). Imzolar `LoanSigner`
/// jadvalida (`documentId` = shu yozuv ID si) — har versiya qayta imzo.
@freezed
abstract class PartnershipContract
    with _$PartnershipContract
    implements Synced {
  const factory PartnershipContract({
    required SyncMeta meta,
    required String partnershipId,
    required int version,
    required String templateId,
    required String termsJson,
  }) = _PartnershipContract;
}

/// Ulush sotib olish to'lovi (kamayib boruvchi musharaka).
@freezed
abstract class BuyoutPayment with _$BuyoutPayment implements Synced {
  const factory BuyoutPayment({
    required SyncMeta meta,
    required String partnershipId,
    required Money amount,
    required LocalDate paidOn,
  }) = _BuyoutPayment;
}

/// Kapital qabul qilishga katta a'zoning roziligi.
@freezed
abstract class PartnershipConsent with _$PartnershipConsent implements Synced {
  const factory PartnershipConsent({
    required SyncMeta meta,
    required String partnershipId,
    required String memberId,
  }) = _PartnershipConsent;
}

abstract interface class PartnershipRepository
    implements SyncedRepository<Partnership> {}

abstract interface class PartnerRepository
    implements SyncedRepository<Partner> {
  Future<List<Partner>> forPartnership(String partnershipId);
}

abstract interface class CapitalContributionRepository
    implements SyncedRepository<CapitalContribution> {
  Future<List<CapitalContribution>> forPartnership(String partnershipId);
}

abstract interface class PartnershipContractRepository
    implements SyncedRepository<PartnershipContract> {
  /// Versiya bo'yicha o'sib boruvchi.
  Future<List<PartnershipContract>> forPartnership(String partnershipId);
}

abstract interface class BuyoutPaymentRepository
    implements SyncedRepository<BuyoutPayment> {
  Future<List<BuyoutPayment>> forPartnership(String partnershipId);
}

abstract interface class PartnershipConsentRepository
    implements SyncedRepository<PartnershipConsent> {
  Future<List<PartnershipConsent>> forPartnership(String partnershipId);
}
