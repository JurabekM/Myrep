import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'expense.freezed.dart';

@freezed
abstract class Category with _$Category implements Synced {
  const factory Category({
    required SyncMeta meta,

    /// Standart kategoriya kaliti (nomi ARB'dan); foydalanuvchinikida `null`.
    CategoryKey? systemKey,

    /// Foydalanuvchi bergan nom.
    String? name,
    Necessity? defaultNecessity,
    @Default(0) int sortOrder,
    @Default(false) bool isArchived,
  }) = _Category;
}

@freezed
abstract class Expense with _$Expense implements Synced {
  const factory Expense({
    required SyncMeta meta,
    required Money amount,
    required String categoryId,
    required PaymentChannel channel,

    /// UTC.
    required DateTime spentAt,
    String? memberId,

    /// MVP-2; MVP-1 da so'ralmaydi.
    Necessity? necessity,
    String? envelopeId,
    @Default(false) bool isGift,
    @Default(false) bool isOstentation,
    @Default(false) bool fundedByDebt,
    String? note,

    /// Kuzatiladigan odat (SPEC 2B.9).
    String? habitId,
  }) = _Expense;
}

/// Xarajat shabloni: bir bosishda yozish (SPEC 2B.1).
@freezed
abstract class ExpenseTemplate with _$ExpenseTemplate implements Synced {
  const factory ExpenseTemplate({
    required SyncMeta meta,
    required String title,
    required Money amount,
    required String categoryId,
    @Default(PaymentChannel.cash) PaymentChannel channel,

    /// `null` — kategoriya toifasi olinadi.
    Necessity? necessity,
    String? habitId,
    @Default(0) int sortOrder,
  }) = _ExpenseTemplate;
}

/// Kategoriya toifasining o'zgarishi (kim — [memberId], qachon —
/// `meta.createdAt`).
@freezed
abstract class NecessityChange with _$NecessityChange implements Synced {
  const factory NecessityChange({
    required SyncMeta meta,
    required String categoryId,
    Necessity? from,
    Necessity? to,
    String? memberId,
  }) = _NecessityChange;
}

abstract interface class CategoryRepository
    implements SyncedRepository<Category> {
  Future<Category?> findBySystemKey(String householdId, CategoryKey key);
}

abstract interface class ExpenseRepository
    implements SyncedRepository<Expense> {
  /// [range] dagi (Toshkent sanalari) faol xarajatlar, vaqt bo'yicha.
  Future<List<Expense>> listInRange(String householdId, DateRange range);

  /// Eng so'nggi faol xarajat («oxirgisini takrorlash»).
  Future<Expense?> latest(String householdId);

  /// O'chirilgan xarajatni qaytaradi («Bekor qilish» — suring bilan o'chirish).
  Future<void> restore(String id);
}

abstract interface class ExpenseTemplateRepository
    implements SyncedRepository<ExpenseTemplate> {}

abstract interface class NecessityChangeRepository
    implements SyncedRepository<NecessityChange> {
  /// Kategoriya tarixi, yangisi birinchi.
  Future<List<NecessityChange>> forCategory(String categoryId);
}
