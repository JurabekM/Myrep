import 'dart:convert';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'debts.freezed.dart';

/// Rejadagi to'lov (saqlangan).
@freezed
abstract class DebtInstallment with _$DebtInstallment implements Synced {
  const factory DebtInstallment({
    required SyncMeta meta,
    required String debtId,
    required LocalDate dueOn,
    required Money amount,
    required Money interest,
  }) = _DebtInstallment;

  const DebtInstallment._();

  /// Asosiy qarz qismi.
  Money get principal => amount - interest;
}

/// Qarzga to'lov (`DebtPayment`).
@freezed
abstract class DebtPayment with _$DebtPayment implements Synced {
  const factory DebtPayment({
    required SyncMeta meta,
    required String debtId,
    required Money amount,
    required LocalDate paidOn,
    @Default(false) bool isPrepayment,
    String? note,

    /// Qo'shimcha to'lovdan ushlangan jarima (v10, `amount` ichida).
    Money? fee,

    /// Kim to'ladi (`DebtContributor`); `null` — oilaning o'zi.
    String? contributorId,
  }) = _DebtPayment;

  const DebtPayment._();

  /// Qarzni kamaytirgan qism (jarimasiz).
  Money get net => fee == null ? amount : amount - fee!;
}

/// Foydalanuvchi bergan qarz (`Receivable`, SPEC 2D.5). **Foiz maydoni
/// yo'q** — foizli qarz berib bo'lmaydi («qarzi hasana»).
@freezed
abstract class Receivable with _$Receivable implements Synced {
  const factory Receivable({
    required SyncMeta meta,
    required String debtorName,
    required Money principal,
    required Money remaining,
    required LocalDate dueDate,
    String? reason,
    String? note,
  }) = _Receivable;

  const Receivable._();

  bool get isOpen => remaining.isPositive;
}

/// Oila maqsadi (imkoniyat narxi, SPEC 2D.3).
@freezed
abstract class Goal with _$Goal implements Synced {
  const factory Goal({
    required SyncMeta meta,
    required String title,
    required Money target,
    LocalDate? targetDate,
  }) = _Goal;
}

/// Qarz tilxati imzolovchisi.
@freezed
abstract class LoanSigner with _$LoanSigner implements Synced {
  const factory LoanSigner({
    required SyncMeta meta,
    required String documentId,
    required SignerRole role,
    required String name,
    List<int>? signaturePng,
    DateTime? signedAt,
  }) = _LoanSigner;

  const LoanSigner._();

  bool get isSigned => signaturePng != null;
}

/// Qarzni to'lashda yelkadosh (SPEC 2D.4). MVP'da oddiy yozuv — ilovaga
/// taklif qilish keyinroq.
@freezed
abstract class DebtContributor with _$DebtContributor implements Synced {
  const factory DebtContributor({
    required SyncMeta meta,
    required String debtId,
    required String name,
    String? memberId,
    Money? monthlyShare,
  }) = _DebtContributor;
}

/// Sotiladigan buyum (SPEC 2D.7).
@freezed
abstract class SellableItem with _$SellableItem implements Synced {
  const factory SellableItem({
    required SyncMeta meta,
    required String name,
    required Money estimated,
    @Default(SellableStatus.listed) SellableStatus status,
    Money? soldFor,
    LocalDate? soldOn,

    /// Puli yo'naltirilgan qarz; `null` — hali yo'naltirilmagan.
    String? debtId,
    String? paymentId,
  }) = _SellableItem;

  const SellableItem._();

  bool get isSold => status == SellableStatus.sold;

  /// Sotilgan, lekin puli hali qarzga yo'naltirilmagan.
  bool get awaitsApplying => isSold && debtId == null;
}

/// Foizsiz muqobil (SPEC 2D.6).
enum BorrowAlternative { reserve, relative, sellItem, none }

/// Qarz oldidan «to'xta va o'yla» javoblari (SPEC 2D.6).
@immutable
final class BorrowCheck {
  const BorrowCheck({
    required this.isNecessity,
    required this.alternative,
    this.loadBp,
  });

  factory BorrowCheck.fromJson(String json) {
    final m = jsonDecode(json) as Map<String, dynamic>;
    return BorrowCheck(
      isNecessity: m['necessity'] as bool,
      alternative: BorrowAlternative.values.byName(m['alternative'] as String),
      loadBp: m['loadBp'] as int?,
    );
  }

  /// Zaruratmi (aks holda — hashamat).
  final bool isNecessity;
  final BorrowAlternative alternative;

  /// Shu qarz bilan oylik qarz yuki — daromadning necha bp i.
  final int? loadBp;

  String toJson() => jsonEncode({
    'necessity': isNecessity,
    'alternative': alternative.name,
    'loadBp': loadBp,
  });
}

abstract interface class DebtInstallmentRepository
    implements SyncedRepository<DebtInstallment> {
  Future<List<DebtInstallment>> forDebt(String debtId);
}

abstract interface class DebtPaymentRepository
    implements SyncedRepository<DebtPayment> {
  Future<List<DebtPayment>> forDebt(String debtId);
}

abstract interface class DebtContributorRepository
    implements SyncedRepository<DebtContributor> {
  Future<List<DebtContributor>> forDebt(String debtId);
}

abstract interface class SellableItemRepository
    implements SyncedRepository<SellableItem> {}

abstract interface class ReceivableRepository
    implements SyncedRepository<Receivable> {}

abstract interface class GoalRepository implements SyncedRepository<Goal> {}

abstract interface class LoanSignerRepository
    implements SyncedRepository<LoanSigner> {
  Future<List<LoanSigner>> forDocument(String documentId);
}
