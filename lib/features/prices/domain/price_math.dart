import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:meta/meta.dart';

/// Narx nuqtasi (sof hisob uchun).
@immutable
final class Observation {
  const Observation(this.on, this.price);

  final LocalDate on;
  final Money price;
}

/// [date] da amal qilgan narx: shu sanagacha (shu sana ham) eng so'nggi
/// kuzatuv; yo'q bo'lsa `null`.
Money? priceAt(Iterable<Observation> points, LocalDate date) {
  Observation? best;
  for (final p in points) {
    if (p.on.isAfter(date)) continue;
    if (best == null || p.on.isAfter(best.on)) best = p;
  }
  return best?.price;
}

/// Narx o'zgarishi bazis punktda: 80 000 → 130 000 = +6250 (62,5 %).
int changeBasisPoints(Money from, Money to) =>
    ratioBasisPoints(to - from, from) ?? 0;

/// Savatdagi bitta mahsulot: oylik miqdori (mingdan birlarda) va narxlari.
@immutable
final class BasketLine {
  const BasketLine({required this.quantityMilli, required this.points});

  final int quantityMilli;
  final List<Observation> points;
}

/// Savat bandi: ikki sanadagi narx va og'irlik (spec `personal_inflation`).
@immutable
final class WeightedChange {
  const WeightedChange({
    required this.from,
    required this.to,
    required this.weight,
  });

  final Money from;
  final Money to;

  /// Og'irlik (bp yoki bazaviy xarajat — nisbat muhim).
  final int weight;
}

/// Og'irlikli indeks (spec `personal_inflation`):
/// `round_half_up(Σ(w_i × bp_i) / Σw_i)`, `bp_i` — [changeBasisPoints].
/// Og'irliklar yig'indisi nol bo'lsa `null`.
int? weightedInflationBp(Iterable<WeightedChange> items) {
  var weighted = BigInt.zero;
  var weights = BigInt.zero;
  for (final i in items) {
    weighted +=
        BigInt.from(i.weight) * BigInt.from(changeBasisPoints(i.from, i.to));
    weights += BigInt.from(i.weight);
  }
  if (weights == BigInt.zero) return null;
  return MoneyRounding.divideBig(weighted, weights);
}

/// Shaxsiy inflyatsiya indeksi (SPEC 2C.1) — [from] dan [to] gacha. Ikkala
/// sanada ham narxi ma'lum mahsulotlargina qatnashadi; og'irlik — bazaviy
/// xarajat ulushi (narx × oylik miqdor, [from] sanasida), so'ng
/// [weightedInflationBp] (desktop bilan bir xil formula). Hisoblab bo'lmasa
/// `null`.
int? personalInflationBp(
  Iterable<BasketLine> basket,
  LocalDate from,
  LocalDate to,
) {
  final items = <WeightedChange>[];
  CurrencyCode? currency;
  for (final line in basket) {
    final p0 = priceAt(line.points, from);
    final p1 = priceAt(line.points, to);
    if (p0 == null || p1 == null || p0.currency != p1.currency) continue;
    currency ??= p0.currency;
    if (p0.currency != currency || !p0.isPositive) continue;
    final weight = MoneyRounding.mulDiv(
      p0.minorUnits,
      line.quantityMilli,
      1000,
    );
    if (weight <= 0) continue;
    items.add(WeightedChange(from: p0, to: p1, weight: weight));
  }
  return weightedInflationBp(items);
}

/// Yillik [annualBp] inflyatsiya bilan [years] yildan keyingi narx.
Money projectPrice(Money price, int annualBp, int years) {
  var p = price;
  for (var i = 0; i < years; i++) {
    p = p.scaled(basisPointsWhole + annualBp, basisPointsWhole);
  }
  return p;
}

/// «Inflyatsiya taʼsiri» (SPEC 2C.2): [balance] ga [price] narxli
/// mahsulotdan necha birlik (mingdan birlarda) olish mumkin.
int purchasableMilli(Money balance, Money price) {
  if (!price.isPositive || balance.currency != price.currency) return 0;
  if (balance.isNegative) return 0;
  return MoneyRounding.mulDiv(
    balance.minorUnits,
    1000,
    price.minorUnits,
    RoundingMode.down,
  );
}
