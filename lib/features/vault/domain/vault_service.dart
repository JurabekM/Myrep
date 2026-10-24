import 'dart:math' as math;

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/vault/domain/habit.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:meta/meta.dart';

/// «Kelajagim» ekrani uchun to'liq holat.
@immutable
final class VaultOverview {
  const VaultOverview({
    required this.household,
    required this.vault,
    required this.growth,
    required this.rule,
    required this.balance,
    required this.reserveBalance,
    required this.growthBalance,
    required this.reserve,
    required this.gate,
    required this.habit,
    required this.history,
    required this.hasInitialBalance,
    required this.progressionOffer,
  });

  final Household household;

  /// Qorovul pul (favqulodda zaxira) aktivi; ulush qoidasi shunga bog'liq.
  final Asset vault;

  /// O'sadigan pul aktivi (SPEC 2C.3).
  final Asset growth;
  final AllocationRule rule;

  /// «Kelajagim» jami = qorovul + o'sadigan.
  final Money balance;
  final Money reserveBalance;
  final Money growthBalance;
  final ReserveStatus reserve;
  final GateState gate;
  final HabitStats habit;

  /// Eng yangisi birinchi.
  final List<VaultTransaction> history;
  final bool hasInitialBalance;

  /// Progressiv rejimda taklif qilinadigan yangi ulush (bp); yo'q — `null`.
  final int? progressionOffer;
}

/// Oylik zarur + kerak xarajatlar o'rtachasi (yoki taxminiy summa) manbai.
typedef EssentialSource =
    Future<({EssentialBasis? basis, bool fromEstimate})> Function();

/// Qarz sharti (4-qonun): faol foizli qarz yo'q yoki chiqish rejasi bor.
/// Interfeys — Vazifa 10–11 da haqiqiy qarz ma'lumoti bilan almashtiriladi.
// ignore: one_member_abstracts
abstract interface class DebtReadiness {
  Future<bool> isReady();
}

/// Vazifa 10–11 gacha: qarz ma'lumoti yo'q — «qarz yo'q» (MVP_PLAN stub).
class NoDebtDataReadiness implements DebtReadiness {
  const NoDebtDataReadiness();

  @override
  Future<bool> isReady() async => true;
}

/// 1-qonun: «Avval o'zingga to'la» (SPEC 2.1, 2.2) va 3-qonun: jamg'arma
/// qorovul / o'sadiganga bo'linadi (SPEC 2C.3–2C.4).
class VaultService {
  VaultService({
    required HouseholdRepository households,
    required AssetRepository assets,
    required VaultTransactionRepository transactions,
    required AllocationRuleRepository rules,
    required SyncMetaFactory metaFactory,
    required Clock clock,
    EssentialSource? essentials,
    DebtReadiness debtReadiness = const NoDebtDataReadiness(),
  }) : _households = households,
       _assets = assets,
       _txs = transactions,
       _rules = rules,
       _meta = metaFactory,
       _clock = clock,
       _essentials = essentials,
       _debt = debtReadiness;

  /// Boshlang'ich ulush — 5 %.
  static const defaultBasisPoints = 500;

  /// Maqsad — 10 % (har daromadning 1/10 qismi).
  static const targetBasisPoints = 1000;
  static const progressionStepBasisPoints = 100;
  static const weeksForProgression = 4;

  // Domen xato kodlari (UI ARB matniga aylantiradi).
  static const errReasonRequired = 'vault_withdraw_reason_required';
  static const errPinRequired = 'vault_withdraw_pin_required';
  static const errInsufficient = 'vault_insufficient_balance';
  static const errInitialExists = 'vault_initial_already_set';
  static const errNotPositive = 'vault_amount_must_be_positive';
  static const errInvalidRule = 'vault_invalid_rule';
  static const errEmergencyRequired = 'vault_reserve_emergency_required';
  static const errGateClosed = 'vault_growth_gate_closed';

  final HouseholdRepository _households;
  final AssetRepository _assets;
  final VaultTransactionRepository _txs;
  final AllocationRuleRepository _rules;
  final SyncMetaFactory _meta;
  final Clock _clock;
  final EssentialSource? _essentials;
  final DebtReadiness _debt;

  Future<Asset> _vaultOf(Household household, VaultType type) async {
    final hh = household.meta.id;
    return await _assets.findVault(hh, type) ??
        await _assets.add(
          Asset(
            meta: _meta.create(hh),
            type: AssetType.vault,
            unit: QuantityUnit.minor,
            currency: household.baseCurrency,
            acquiredAt: _clock.nowUtc(),
            vaultType: type,
          ),
        );
  }

  /// Uy xo'jaligi, qorovul jamg'arma aktivi va qoida (yo'q bo'lsa
  /// yaratiladi).
  Future<(Household, Asset, AllocationRule)> _context() async {
    final household = await _households.current();
    final hh = household.meta.id;
    final vault = await _vaultOf(household, VaultType.qorovul);
    final rule =
        await _rules.activeFor(vault.meta.id) ??
        await _rules.add(
          AllocationRule(
            meta: _meta.create(hh),
            vaultAssetId: vault.meta.id,
            mode: AllocationMode.fixed,
            currency: household.baseCurrency,
            basisPoints: defaultBasisPoints,
          ),
        );
    return (household, vault, rule);
  }

  Future<List<VaultTransaction>> _history(Asset reserve, Asset growth) async =>
      [
        ...await _txs.listForVault(reserve.meta.id),
        ...await _txs.listForVault(growth.meta.id),
      ]..sort((a, b) => b.occurredAt.compareTo(a.occurredAt));

  Future<ReserveStatus> _reserve(Money balance) async {
    final src = await _essentials?.call();
    return ReserveStatus(
      balance: balance,
      essential: src?.basis,
      fromEstimate: src?.fromEstimate ?? false,
    );
  }

  Future<GateState> _gate(Household household, ReserveStatus reserve) async =>
      GateState(
        reserve: reserve,
        debtReady: await _debt.isReady(),
        bypassed: household.gateBypassedAt != null,
      );

  Future<VaultOverview> overview() async {
    final (household, vault, rule) = await _context();
    final growth = await _vaultOf(household, VaultType.osadigan);
    final currency = household.baseCurrency;
    final history = await _history(vault, growth);
    final reserveBalance = await _txs.balance(vault.meta.id, currency);
    final growthBalance = await _txs.balance(growth.meta.id, currency);
    final reserve = await _reserve(reserveBalance);
    final today = Tashkent.dateOf(_clock.nowUtc());
    final savings = [
      for (final t in history)
        if (_countsAsHabit(t)) t.occurredAt,
    ];
    final habit = computeHabit(
      savingInstants: savings,
      calendar: household.calendar,
      today: today,
    );
    return VaultOverview(
      household: household,
      vault: vault,
      growth: growth,
      rule: rule,
      balance: reserveBalance + growthBalance,
      reserveBalance: reserveBalance,
      growthBalance: growthBalance,
      reserve: reserve,
      gate: await _gate(household, reserve),
      habit: habit,
      history: history,
      hasInitialBalance: history.any(
        (t) => t.reason == VaultTransactionReason.initial,
      ),
      progressionOffer: _progressionOffer(rule, savings, household, today),
    );
  }

  /// Odatga faqat daromad ulushi va qo'lda qo'shilgan summa kiradi
  /// («avval yigʻilgan pul» — bir martalik, pul olish — odat emas).
  static bool _countsAsHabit(VaultTransaction t) =>
      t.type == VaultTransactionType.deposit &&
      t.reason != VaultTransactionReason.initial;

  int? _progressionOffer(
    AllocationRule rule,
    List<DateTime> savings,
    Household household,
    LocalDate today,
  ) {
    final bp = rule.basisPoints;
    if (rule.mode != AllocationMode.progressive || bp == null) return null;
    if (bp >= targetBasisPoints) return null;
    final weeks = streakWeeksSince(
      savingInstants: savings,
      calendar: household.calendar,
      today: today,
      since: rule.progressionOfferedAt,
    );
    if (weeks < weeksForProgression) return null;
    return math.min(bp + progressionStepBasisPoints, targetBasisPoints);
  }

  /// Daromaddan ajratish taklifi: «Shundan X so'm — kelajagingiz uchun».
  ///
  /// * Foiz qoidasi: `percentOf` → 1 000 so'mgacha (kichik summada — butun
  ///   so'mgacha) **yuqoriga** yaxlitlanadi (jamg'arma foydasiga), lekin
  ///   daromaddan oshmaydi.
  /// * Qat'iy summa (oyiga): oy maqsadidan qolgan qism, daromaddan oshmaydi.
  /// * Taklif yo'q bo'lsa (maqsad bajarilgan, valyuta boshqa) — `null`.
  Future<Money?> suggestShare(Income income) async {
    final (household, vault, rule) = await _context();
    final amount = income.amount;
    if (amount.currency != rule.currency || !amount.isPositive) return null;

    final fixed = rule.fixedAmount;
    final Money raw;
    if (fixed != null && rule.basisPoints == null) {
      final month = household.calendar.monthOf(
        Tashkent.dateOf(income.receivedAt),
      );
      final saved = await _savedInRange(household, month, rule.currency);
      final left = fixed - saved;
      if (!left.isPositive) return null;
      return left < amount ? left : amount;
    } else {
      raw = percentOf(amount, rule.basisPoints ?? defaultBasisPoints);
    }
    if (!raw.isPositive) return null;
    final step = raw.minorUnits >= _thousand(raw.currency)
        ? _thousand(raw.currency)
        : raw.currency.minorPerMajor;
    final rounded = raw.roundTo(step, RoundingMode.ceiling);
    return rounded > amount ? amount : rounded;
  }

  static int _thousand(CurrencyCode c) => 1000 * c.minorPerMajor;

  Future<Money> _savedInRange(
    Household household,
    DateRange range,
    CurrencyCode currency,
  ) async {
    final all = await _history(
      await _vaultOf(household, VaultType.qorovul),
      await _vaultOf(household, VaultType.osadigan),
    );
    return Money.sum([
      for (final t in all)
        if (_countsAsHabit(t) &&
            t.amount.currency == currency &&
            !t.occurredAt.isBefore(range.startInstant) &&
            t.occurredAt.isBefore(range.endInstantExclusive))
          t.amount,
    ], currency);
  }

  /// Daromaddan ulush ajratish (DEPOSIT, `incomeShare`).
  Future<VaultTransaction> allocateFromIncome(Income income, Money amount) =>
      _deposit(
        amount,
        VaultTransactionReason.incomeShare,
        incomeId: income.meta.id,
      );

  /// Qo'lda qo'shish (masalan, «qutqarilgan pul»).
  Future<VaultTransaction> depositManual(Money amount) =>
      _deposit(amount, VaultTransactionReason.manual);

  /// «Qutqarilgan pul»ni o'tkazish (SPEC 2B.7: 1- va 2-qonun ulanishi).
  Future<VaultTransaction> depositRescue(Money amount) =>
      _deposit(amount, VaultTransactionReason.rescue);

  /// «Avval yig'ilgan pul»: ilovadan oldingi naqd jamg'arma — bir martalik.
  Future<VaultTransaction> setInitialBalance(Money amount) async {
    final (_, vault, _) = await _context();
    final history = await _txs.listForVault(vault.meta.id);
    if (history.any((t) => t.reason == VaultTransactionReason.initial)) {
      throw const DomainRuleException(errInitialExists);
    }
    return _deposit(amount, VaultTransactionReason.initial);
  }

  /// Kiritish: «avval yig'ilgan pul» — doim qorovulga; qolganlari avval
  /// qorovulni maqsadgacha to'ldiradi, ortgani darvoza ochiq bo'lsa o'sadiganga
  /// (SPEC 2C.3). Birinchi yozilgan tranzaksiya qaytariladi.
  Future<VaultTransaction> _deposit(
    Money amount,
    VaultTransactionReason reason, {
    String? incomeId,
  }) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final (household, vault, _) = await _context();
    var toReserve = amount;
    var toGrowth = Money.zero(amount.currency);
    if (reason != VaultTransactionReason.initial) {
      final reserve = await _reserve(
        await _txs.balance(vault.meta.id, amount.currency),
      );
      final gate = await _gate(household, reserve);
      // Zaxira to'lishini splitShare o'zi hal qiladi; ortiqcha faqat qarz
      // sharti bajarilganda o'sadiganga o'tadi (`gate.ready` emas — u
      // qorovul allaqachon to'la bo'lishini talab qiladi).
      final split = splitShare(
        amount: amount,
        reserve: reserve,
        growthOpen: gate.debtReady,
      );
      toReserve = split.qorovul;
      toGrowth = split.osadigan;
    }
    VaultTransaction? first;
    for (final (asset, part) in [
      (vault, toReserve),
      if (toGrowth.isPositive)
        (await _vaultOf(household, VaultType.osadigan), toGrowth),
    ]) {
      if (!part.isPositive) continue;
      final tx = await _txs.add(
        VaultTransaction(
          meta: _meta.create(household.meta.id),
          vaultAssetId: asset.meta.id,
          type: VaultTransactionType.deposit,
          amount: part,
          reason: reason,
          incomeId: incomeId,
          occurredAt: _clock.nowUtc(),
        ),
      );
      first ??= tx;
    }
    return first!;
  }

  /// O'sadigan pulga kapital kiritish — tayyorgarlik darvozasi orqali
  /// (SPEC 2C.4). Yopiq bo'lsa faqat ongli chetlab o'tish bilan
  /// ([bypassConfirmed]); bu holat qayd etiladi.
  Future<VaultTransaction> depositGrowth(
    Money amount, {
    bool bypassConfirmed = false,
  }) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final o = await overview();
    if (!o.gate.isOpen) {
      if (!bypassConfirmed) throw const DomainRuleException(errGateClosed);
      await _households.update(
        o.household.copyWith(gateBypassedAt: _clock.nowUtc()),
      );
    }
    return _txs.add(
      VaultTransaction(
        meta: _meta.create(o.household.meta.id),
        vaultAssetId: o.growth.meta.id,
        type: VaultTransactionType.deposit,
        amount: amount,
        reason: VaultTransactionReason.manual,
        occurredAt: _clock.nowUtc(),
      ),
    );
  }

  /// Pul olish (SPEC 2.2 friction): sabab majburiy, PIN qayta kiritilgan
  /// bo'lishi shart ([approval]), balansdan oshmaydi.
  ///
  /// Qorovul puldan olishda «bu haqiqatan favqulodda holatmi?» tasdig'i
  /// majburiy ([emergencyConfirmed], SPEC 2C.3).
  Future<VaultTransaction> withdraw({
    required Money amount,
    required String reason,
    required PinApproval? approval,
    VaultType from = VaultType.qorovul,
    bool emergencyConfirmed = false,
  }) async {
    final note = reason.trim();
    if (note.isEmpty) throw const DomainRuleException(errReasonRequired);
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    if (from == VaultType.qorovul && !emergencyConfirmed) {
      throw const DomainRuleException(errEmergencyRequired);
    }
    if (approval == null || !approval.consume(_clock.nowUtc())) {
      throw const DomainRuleException(errPinRequired);
    }
    final household = await _households.current();
    final vault = await _vaultOf(household, from);
    final balance = await _txs.balance(vault.meta.id, amount.currency);
    if (amount > balance) throw const DomainRuleException(errInsufficient);
    return _txs.add(
      VaultTransaction(
        meta: _meta.create(household.meta.id),
        vaultAssetId: vault.meta.id,
        type: VaultTransactionType.withdraw,
        amount: amount,
        reason: VaultTransactionReason.withdrawal,
        reasonNote: note,
        occurredAt: _clock.nowUtc(),
      ),
    );
  }

  /// Ulush qoidasini o'zgartirish: foiz (5 % / 10 % …) yoki oylik qat'iy
  /// summa; progressiv rejim faqat foiz bilan.
  Future<AllocationRule> updateRule({
    required AllocationMode mode,
    int? basisPoints,
    Money? fixedAmount,
  }) async {
    final valid =
        (basisPoints != null &&
            fixedAmount == null &&
            basisPoints > 0 &&
            basisPoints <= basisPointsWhole) ||
        (basisPoints == null &&
            fixedAmount != null &&
            fixedAmount.isPositive &&
            mode == AllocationMode.fixed);
    if (!valid) throw const DomainRuleException(errInvalidRule);
    final (_, _, rule) = await _context();
    return _rules.update(
      rule.copyWith(
        mode: mode,
        basisPoints: basisPoints,
        fixedAmount: fixedAmount,
        currency: fixedAmount?.currency ?? rule.currency,
        // Rejim almashsa ketma-ketlik yangidan sanaladi.
        progressionOfferedAt: mode == AllocationMode.progressive
            ? (rule.mode == mode ? rule.progressionOfferedAt : _clock.nowUtc())
            : null,
      ),
    );
  }

  /// Progressiv taklifga javob: qabul qilinsa ulush oshadi; har ikki holatda
  /// keyingi taklif yana 4 haftadan keyin.
  Future<AllocationRule> answerProgression({required bool accept}) async {
    final overview = await this.overview();
    final offer = overview.progressionOffer;
    final rule = overview.rule;
    return _rules.update(
      rule.copyWith(
        basisPoints: accept && offer != null ? offer : rule.basisPoints,
        progressionOfferedAt: _clock.nowUtc(),
      ),
    );
  }
}
