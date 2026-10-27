import 'package:baraka_daftari/core/money/money.dart';
import 'package:meta/meta.dart';

/// Katta summa taqsimoti (SPEC 2G.5): katta summa kelganda avval
/// oilaning 6 oylik zaxira kamomadi to'ldiriladi, qolgani sarmoya uchun.
@immutable
final class LumpSumPlan {
  const LumpSumPlan({required this.toReserve, required this.toInvest});

  /// Qorovul jamg'armaga (devor) — savdoga ham, sheriklikka ham qo'shilmaydi.
  final Money toReserve;

  /// Zaxira to'lgandan keyin qolgani — «Hunardan ishga» (2E.4, 2G.8).
  final Money toInvest;
}

/// Umumiy vektor `spec/test-vectors/lump_sum_split.json`:
/// `toReserve = min(amount, reserveMissing)`, `toInvest = amount − toReserve`.
/// Valyutalar bir xil bo'lishi shart (`CurrencyMismatchException`).
LumpSumPlan splitLumpSum(Money amount, Money reserveMissing) {
  final zero = Money.zero(amount.currency);
  // Manfiy kamomad — zaxira allaqachon to'la.
  final missing = reserveMissing.isNegative ? zero : reserveMissing;
  if (!amount.isPositive) return LumpSumPlan(toReserve: zero, toInvest: zero);
  final toReserve = amount < missing ? amount : missing;
  return LumpSumPlan(toReserve: toReserve, toInvest: amount - toReserve);
}
