import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:meta/meta.dart';

/// Oylik daromadning 70 / 20 / 10 taqsimoti (SPEC 2D.1).
@immutable
final class RecoveryBudget {
  const RecoveryBudget({
    required this.income,
    required this.needs,
    required this.debtExtra,
    required this.savings,
    required this.mandatoryDebt,
  });

  factory RecoveryBudget.of(
    Money income,
    RecoverySplit split,
    Money mandatoryDebt,
  ) {
    final parts = allocate(income, [
      split.needsBp,
      split.debtBp,
      split.savingsBp,
    ]);
    return RecoveryBudget(
      income: income,
      needs: parts[0],
      debtExtra: parts[1],
      savings: parts[2],
      mandatoryDebt: mandatoryDebt,
    );
  }

  final Money income;

  /// Ro'zg'or — majburiy oylik qarz to'lovlari shu ichida (`ZARUR`).
  final Money needs;

  /// Odatiy to'lovdan tashqari qo'shimcha qarz to'lovi.
  final Money debtExtra;

  /// «Kelajagim» — 0 bo'lmaydi.
  final Money savings;
  final Money mandatoryDebt;

  /// Majburiy to'lovlardan keyin ro'zg'orga qolgani (manfiy — sig'maydi).
  Money get household => needs - mandatoryDebt;

  bool get mandatoryExceedsNeeds => mandatoryDebt > needs;
}

/// «Qarzdan chiqish» rejimi holati.
@immutable
final class RecoveryState {
  const RecoveryState({
    required this.mode,
    required this.split,
    required this.hasOpenDebts,
    required this.freedOffer,
    required this.monthlyExtra,
    this.budget,
  });

  final BudgetMode mode;
  final RecoverySplit split;
  final bool hasOpenDebts;

  /// Hamma qarz yopilib rejim odatiyga qaytgan — bo'shagan 20 % taklifi.
  final bool freedOffer;

  /// Planner uchun standart oylik qo'shimcha to'lov (rejimda — 20 % ulush).
  final Money monthlyExtra;

  /// Daromad ma'lum bo'lsa — oylik taqsimot.
  final RecoveryBudget? budget;

  bool get isActive => mode == BudgetMode.debtRecovery;

  /// SPEC 2D.1: faol qarz bo'lsa ilova rejimni taklif qiladi.
  bool get offerRecovery => !isActive && hasOpenDebts;
}

/// 4-qonun: `DEBT_RECOVERY` rejimi 70 / 20 / 10 (SPEC 2D.1).
class RecoveryService {
  RecoveryService({
    required HouseholdRepository households,
    required DebtService debts,
    required VaultService vault,
  }) : _households = households,
       _debts = debts,
       _vault = vault;

  /// Jamg'arma ulushi 0 ga (1 % dan pastga) tushirilmaydi.
  static const errSavingsRequired = 'recovery_savings_required';
  static const errSplitInvalid = 'recovery_split_must_total_100';
  static const errNoDebts = 'recovery_no_open_debts';

  final HouseholdRepository _households;
  final DebtService _debts;
  final VaultService _vault;

  Future<RecoveryState> state() async {
    final h = await _households.current();
    final o = await _debts.overview();
    final split = h.recoverySplit;
    final income = o.monthlyIncome;
    final active = h.budgetMode == BudgetMode.debtRecovery;
    return RecoveryState(
      mode: h.budgetMode,
      split: split,
      hasOpenDebts: o.debts.isNotEmpty,
      freedOffer: h.freedShareOfferPending,
      monthlyExtra: active && income != null
          ? percentOf(income, split.debtBp)
          : Money.zero(h.baseCurrency),
      budget: income == null
          ? null
          : RecoveryBudget.of(income, split, o.monthlyPayments),
    );
  }

  static void validate(RecoverySplit split) {
    if (split.savingsBp < RecoverySplit.minSavingsBp) {
      throw const DomainRuleException(errSavingsRequired);
    }
    if (!split.isValid) throw const DomainRuleException(errSplitInvalid);
  }

  /// Rejimni yoqish (yoki ulushlarni o'zgartirish). «Kelajagim» ulushi foiz
  /// qoidasida [RecoverySplit.savingsBp] dan kam bo'lsa — ko'tariladi.
  Future<void> enable([RecoverySplit split = RecoverySplit.standard]) async {
    validate(split);
    final h = await _households.current();
    if (h.budgetMode != BudgetMode.debtRecovery &&
        (await _debts.overview()).debts.isEmpty) {
      throw const DomainRuleException(errNoDebts);
    }
    await _households.update(
      h.copyWith(
        budgetMode: BudgetMode.debtRecovery,
        recoverySplit: split,
        freedShareOfferPending: false,
      ),
    );
    final rule = (await _vault.overview()).rule;
    final bp = rule.basisPoints;
    if (bp != null && bp < split.savingsBp) {
      await _vault.updateRule(mode: rule.mode, basisPoints: split.savingsBp);
    }
  }

  /// Rejimdan qo'lda chiqish.
  Future<void> disable() async {
    final h = await _households.current();
    await _households.update(h.copyWith(budgetMode: BudgetMode.standard));
  }

  /// Bo'shagan 20 % ni «Kelajagim»ga yo'naltirish (SPEC 2D.1): foiz
  /// qoidasiga qo'shiladi; qat'iy summada — daromadning shu ulushi.
  Future<AllocationRule?> acceptFreedShare() async {
    final h = await _households.current();
    await _households.update(h.copyWith(freedShareOfferPending: false));
    final rule = (await _vault.overview()).rule;
    final bp = rule.basisPoints;
    if (bp != null) {
      final next = bp + h.recoverySplit.debtBp;
      return _vault.updateRule(
        mode: rule.mode,
        basisPoints: next > basisPointsWhole ? basisPointsWhole : next,
      );
    }
    final income = (await _debts.overview()).monthlyIncome;
    if (income == null || rule.fixedAmount == null) return null;
    return _vault.updateRule(
      mode: AllocationMode.fixed,
      fixedAmount:
          rule.fixedAmount! + percentOf(income, h.recoverySplit.debtBp),
    );
  }

  Future<void> dismissFreedShare() async {
    final h = await _households.current();
    await _households.update(h.copyWith(freedShareOfferPending: false));
  }

  /// Yopilgan qarzdan bo'shagan oylik to'lovni «Kelajagim»ga (SPEC 2D.9):
  /// qat'iy summaga qo'shiladi; foiz qoidasida — daromadga nisbatan butun
  /// foizgacha yuqoriga. Daromad noma'lum bo'lsa — `null`.
  Future<AllocationRule?> redirectFreed(Money freed) async {
    final rule = (await _vault.overview()).rule;
    if (rule.fixedAmount != null && rule.basisPoints == null) {
      return _vault.updateRule(
        mode: AllocationMode.fixed,
        fixedAmount: rule.fixedAmount! + freed,
      );
    }
    final income = (await _debts.overview()).monthlyIncome;
    final ratio = income == null ? null : ratioBasisPoints(freed, income);
    if (ratio == null || rule.basisPoints == null) return null;
    final add = (ratio + 99) ~/ 100 * 100;
    final next = rule.basisPoints! + add;
    return _vault.updateRule(
      mode: rule.mode,
      basisPoints: next > basisPointsWhole ? basisPointsWhole : next,
    );
  }
}
