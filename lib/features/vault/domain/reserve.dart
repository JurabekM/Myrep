import 'package:baraka_daftari/core/money/money.dart';
import 'package:meta/meta.dart';

/// Zaxira maqsadi asosi: oxirgi [months] oydagi (`ZARUR` + `KERAK`) jami
/// [total]. Taxminiy summa — `months = 1`.
///
/// Maqsad spec bo'yicha (`spec/test-vectors/emergency_target.json`):
/// `round_half_up(Σ × N / k)` — avval o'rtacha yaxlitlanib, keyin
/// ko'paytirilmaydi (aks holda 31 000 000 o'rniga 31 000 002 so'm chiqadi).
@immutable
final class EssentialBasis {
  const EssentialBasis({required this.total, required this.months})
    : assert(months > 0, 'oylar soni musbat');

  final Money total;
  final int months;

  /// Oylik o'rtacha (ko'rsatish uchun, butun so'mgacha).
  Money get monthly => Money(
    MoneyRounding.divide(total.minorUnits, months),
    total.currency,
  ).roundTo(total.currency.minorPerMajor);

  /// [n] oylik zaxira: `round_half_up(Σ × n / k)`.
  Money targetFor(int n) => Money(
    MoneyRounding.mulDiv(total.minorUnits, n, months),
    total.currency,
  );
}

/// Zaxira maqsadi (spec `emergency_target`): ma'lumotli (musbat) oylar
/// [minMonths] tadan kam bo'lsa — `null`.
Money? emergencyTarget({
  required List<Money> monthTotals,
  int months = ReserveStatus.fullMonths,
  int minMonths = 3,
}) => essentialBasis(
  monthTotals: monthTotals,
  minMonths: minMonths,
)?.targetFor(months);

/// Qorovul pul (favqulodda zaxira) holati (SPEC 2C.3).
@immutable
final class ReserveStatus {
  const ReserveStatus({
    required this.balance,
    EssentialBasis? essential,
    Money? monthlyEssential,
    this.fromEstimate = false,
  }) : _essential = essential,
       _monthly = monthlyEssential;

  /// To'liq maqsad — 6 oy, birinchi milestone — 3 oy.
  static const fullMonths = 6;
  static const firstMilestoneMonths = 3;

  /// Qorovul pul balansi.
  final Money balance;

  final EssentialBasis? _essential;
  final Money? _monthly;

  /// O'rtacha foydalanuvchi kiritgan taxminiy summadan olinganmi.
  final bool fromEstimate;

  /// Maqsad asosi; `null` — noma'lum (ma'lumot 3 oydan kam va taxminiy
  /// summa kiritilmagan).
  EssentialBasis? get essential =>
      _essential ??
      (_monthly == null ? null : EssentialBasis(total: _monthly, months: 1));

  /// Oylik zarur + kerak xarajatlar o'rtachasi (ko'rsatish uchun).
  Money? get monthlyEssential => essential?.monthly;

  bool get needsEstimate => essential == null;

  Money? get target => essential?.targetFor(fullMonths);
  Money? get firstMilestone => essential?.targetFor(firstMilestoneMonths);

  /// Necha oylik zaxira bor, o'ndan birlarda (14 → «1,4 oy»), pastga
  /// yaxlitlangan: `⌊balans × 10 × k / Σ⌋`. Noma'lum bo'lsa 0.
  int get monthsTenths {
    final e = essential;
    if (e == null || !e.total.isPositive || balance.isNegative) return 0;
    return MoneyRounding.divideBig(
      BigInt.from(balance.minorUnits) * BigInt.from(10 * e.months),
      BigInt.from(e.total.minorUnits),
      RoundingMode.down,
    );
  }

  bool get firstMilestoneReached {
    final m = firstMilestone;
    return m != null && balance >= m;
  }

  bool get isFull {
    final t = target;
    return t != null && balance >= t;
  }

  /// Maqsadgacha yetishmayotgani (to'la bo'lsa 0; noma'lum — `null`).
  Money? get missing {
    final t = target;
    if (t == null) return null;
    final d = t - balance;
    return d.isNegative ? Money.zero(t.currency) : d;
  }
}

/// Maqsad asosi: oxirgi to'liq oylardan kamida [minMonths] tasida ma'lumot
/// bo'lsa — ularning jami; aks holda [estimate] (bir oylik taxmin); u ham
/// yo'q — `null`.
EssentialBasis? essentialBasis({
  required List<Money> monthTotals,
  Money? estimate,
  int minMonths = 3,
}) {
  final withData = [
    for (final m in monthTotals)
      if (m.isPositive) m,
  ];
  if (withData.length < minMonths) {
    return estimate == null ? null : EssentialBasis(total: estimate, months: 1);
  }
  return EssentialBasis(
    total: Money.sum(withData, withData.first.currency),
    months: withData.length,
  );
}

/// Oylik zarur + kerak xarajatlar o'rtachasi (SPEC 2C.3, ko'rsatish uchun):
/// oxirgi to'liq oylardan kamida [minMonths] tasida ma'lumot bo'lsa —
/// o'rtacha (butun so'mgacha); aks holda [estimate]; u ham yo'q — `null`.
Money? averageMonthlyEssential({
  required List<Money> monthTotals,
  Money? estimate,
  int minMonths = 3,
}) => essentialBasis(
  monthTotals: monthTotals,
  estimate: estimate,
  minMonths: minMonths,
)?.monthly;

/// Daromad ulushini taqsimlash (SPEC 2C.3: avval qorovul): qorovul maqsadga
/// yetguncha unga, ortgani — darvoza ochiq bo'lsa o'sadiganga.
({Money qorovul, Money osadigan}) splitShare({
  required Money amount,
  required ReserveStatus reserve,
  required bool growthOpen,
}) {
  final zero = Money.zero(amount.currency);
  final missing = reserve.missing;
  if (missing == null || !growthOpen) return (qorovul: amount, osadigan: zero);
  final toReserve = missing < amount ? missing : amount;
  return (qorovul: toReserve, osadigan: amount - toReserve);
}

/// Qorovul puldan olinganni qayta to'ldirish rejasi: [months] oyga teng
/// bo'lib, yuqoriga yaxlitlanadi — 1 000 so'mdan katta bo'lsa 1 000 so'mgacha,
/// kichik bo'lsa butun so'mgacha (kasrli so'm ko'rsatilmaydi).
({Money monthly, int months}) refillPlan(Money used, {int months = 6}) {
  final c = used.currency;
  final raw = Money(
    MoneyRounding.divide(used.minorUnits, months, RoundingMode.ceiling),
    c,
  );
  final thousand = 1000 * c.minorPerMajor;
  final step = raw.minorUnits >= thousand ? thousand : c.minorPerMajor;
  return (monthly: raw.roundTo(step, RoundingMode.ceiling), months: months);
}

/// Tayyorgarlik darvozasi (SPEC 2C.4): «Avval tayyorgarlik, keyin sarmoya».
@immutable
final class GateState {
  const GateState({
    required this.reserve,
    required this.debtReady,
    required this.bypassed,
  });

  final ReserveStatus reserve;

  /// Faol foizli qarz yo'q yoki qarzdan chiqish rejasi bor (4-qonun).
  final bool debtReady;

  /// Foydalanuvchi ongli ravishda chetlab o'tgan.
  final bool bypassed;

  bool get reserveReady => reserve.isFull;

  /// Ikkala shart bajarilgan.
  bool get ready => reserveReady && debtReady;

  /// O'sadigan pul / sheriklikka kirish ochiqmi.
  bool get isOpen => ready || bypassed;

  /// Yopiq bo'lsa — sabablari (chetlab o'tish hisobga olinmaydi).
  List<GateLockReason> get reasons => gateLockReasons(
    reserveFull: reserveReady,
    debtReady: debtReady,
  );
}

/// Darvoza yopiqligi sabablari (spec `readiness_gate`).
enum GateLockReason {
  /// Qorovul pul 6 oylik maqsadga yetmagan.
  reserveBelowTarget,

  /// Faol foizli qarz bor, qarzdan chiqish rejasi yo'q.
  interestDebtWithoutPlan,
}

/// Darvoza qoidasi (SPEC 2C.4): qorovul ≥ 6 oy **va** (foizli qarz yo'q
/// **yoki** chiqish rejasi bor). [debtReady] — ikkinchi shart.
List<GateLockReason> gateLockReasons({
  required bool reserveFull,
  required bool debtReady,
}) => [
  if (!reserveFull) GateLockReason.reserveBelowTarget,
  if (!debtReady) GateLockReason.interestDebtWithoutPlan,
];
