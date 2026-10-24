import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'venture.freezed.dart';

/// Sheriklik kassa daftari yozuvi (`VentureEntry`, SPEC 2E.3).
@freezed
abstract class VentureEntry with _$VentureEntry implements Synced {
  const factory VentureEntry({
    required SyncMeta meta,
    required String partnershipId,
    required VentureEntryKind kind,
    required String title,

    /// Musbat; tuzatish — ishorali (manfiy — kamaytiradi).
    required Money amount,
    required LocalDate occurredOn,
    String? note,

    /// Chek yoki dalil rasmi (shifrlangan bazada).
    List<int>? receiptImage,
  }) = _VentureEntry;

  const VentureEntry._();

  /// Sof foydaga ta'siri: kirim +, xarajat va fors-major −, tuzatish ishorasi.
  Money get effect => switch (kind) {
    VentureEntryKind.income || VentureEntryKind.correction => amount,
    VentureEntryKind.expense || VentureEntryKind.forceMajeure => -amount,
  };
}

/// Yopilgan davr (`ProfitDistribution`).
@freezed
abstract class VenturePeriod with _$VenturePeriod implements Synced {
  const factory VenturePeriod({
    required SyncMeta meta,
    required String partnershipId,
    required LocalDate startDate,
    required LocalDate endDate,
    required Money income,
    required Money expense,
    required Money net,
    required Money buyout,
    @Default(false) bool negligence,
    String? negligenceNote,
    String? incomeId,
  }) = _VenturePeriod;
}

/// Davr taqsimotidagi sherik ulushi.
@freezed
abstract class DistributionShare with _$DistributionShare implements Synced {
  const factory DistributionShare({
    required SyncMeta meta,
    required String periodId,
    required String partnerId,
    required Money amount,
    required Money buyout,
  }) = _DistributionShare;
}

/// Oiladagi hunar (`Skill`).
@freezed
abstract class Skill with _$Skill implements Synced {
  const factory Skill({
    required SyncMeta meta,
    required String name,
    String? memberId,
  }) = _Skill;
}

/// Hunardan ish g'oyasi (`VentureIdea`).
@freezed
abstract class VentureIdea with _$VentureIdea implements Synced {
  const factory VentureIdea({
    required SyncMeta meta,
    required String title,
    required Money pessimisticIncome,
    required Money baseIncome,
    required Money optimisticIncome,
    required Money monthlyExpense,
    @Default(10000) int myShareBp,
    String? skillId,
  }) = _VentureIdea;
}

/// G'oyaning CAPEX bandi.
@freezed
abstract class IdeaCapexItem with _$IdeaCapexItem implements Synced {
  const factory IdeaCapexItem({
    required SyncMeta meta,
    required String ideaId,
    required String title,
    required Money amount,
  }) = _IdeaCapexItem;
}

/// Saqlangan taklif tekshiruvi (`OfferCheck`).
@freezed
abstract class OfferCheckRecord with _$OfferCheckRecord implements Synced {
  const factory OfferCheckRecord({
    required SyncMeta meta,
    required String title,
    required String answersJson,
    required OfferVerdict verdict,

    /// v16 (SPEC 2G.6): summa, va'da qilingan oylik stavka, maslahatchi va
    /// qaror.
    Money? amount,
    int? promisedMonthlyBp,
    String? advisor,
    OfferDecision? decision,
    DateTime? decidedAt,
  }) = _OfferCheckRecord;
}

abstract interface class VentureEntryRepository
    implements SyncedRepository<VentureEntry> {
  Future<List<VentureEntry>> forPartnership(String partnershipId);
}

abstract interface class VenturePeriodRepository
    implements SyncedRepository<VenturePeriod> {
  /// Davr oxiri bo'yicha o'sib boruvchi.
  Future<List<VenturePeriod>> forPartnership(String partnershipId);
}

abstract interface class DistributionShareRepository
    implements SyncedRepository<DistributionShare> {
  Future<List<DistributionShare>> forPeriod(String periodId);
}

abstract interface class SkillRepository implements SyncedRepository<Skill> {}

abstract interface class VentureIdeaRepository
    implements SyncedRepository<VentureIdea> {}

abstract interface class IdeaCapexItemRepository
    implements SyncedRepository<IdeaCapexItem> {
  Future<List<IdeaCapexItem>> forIdea(String ideaId);
}

abstract interface class OfferCheckRepository
    implements SyncedRepository<OfferCheckRecord> {}
