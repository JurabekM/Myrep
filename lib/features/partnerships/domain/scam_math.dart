import 'package:baraka_daftari/core/money/money_rounding.dart';
import 'package:meta/meta.dart';

/// Va'da qilingan oylik foydani yillikka aylantirish (SPEC 2G.3). Natija bp:
/// 10000 = 1 barobar. **Faqat ogohlantirish uchun** — muqobil daromad
/// sifatida ko'rsatilmaydi (SPEC 3-bo'lim).
///
/// Umumiy vektor `spec/test-vectors/promised_return.json`:
/// - oddiy: `10000 + months · monthlyBp`;
/// - murakkab: `x = 10000`, har oy `x = half_up(x · (10000 + monthlyBp) / 10000)`.
@immutable
final class PromisedMultiple {
  const PromisedMultiple({required this.simpleBp, required this.compoundBp});

  final int simpleBp;
  final int compoundBp;
}

PromisedMultiple promisedMultiple(int monthlyBp, {int months = 12}) {
  if (monthlyBp < 0 || months < 0) {
    throw ArgumentError("monthlyBp va months manfiy bo'lmaydi");
  }
  var x = 10000;
  for (var i = 0; i < months; i++) {
    // core/money standart rejimi — yarmidan yuqoriga (half-up).
    x = MoneyRounding.divide(x * (10000 + monthlyBp), 10000);
  }
  return PromisedMultiple(simpleBp: 10000 + months * monthlyBp, compoundBp: x);
}

/// Piramida ta'limiy modeli (SPEC 2G.4): har ishtirokchi `k` ta yangi odam
/// olib keladi; aholi `N` tugaganda yangi qavat to'lmaydi va piramida cho'kadi.
@immutable
final class PyramidModel {
  const PyramidModel({
    required this.levels,
    required this.participants,
    required this.lastLevel,
    required this.lastLevelShareBp,
    required this.lastLevelFull,
  });

  /// Qavatlar soni (to'lmagan oxirgi qavat ham).
  final int levels;
  final int participants;

  /// Eng pastki qavatdagi odamlar — cho'kkan kuni pulini yo'qotadiganlar.
  final int lastLevel;
  final int lastLevelShareBp;
  final bool lastLevelFull;
}

/// Umumiy vektor `spec/test-vectors/pyramid_levels.json`.
PyramidModel pyramidLevels({
  required int recruitsPerPerson,
  required int population,
}) {
  if (recruitsPerPerson < 2 || population < 1) {
    throw ArgumentError('recruitsPerPerson >= 2, population >= 1');
  }
  var levels = 0;
  var total = 0;
  var size = 1;
  var last = 0;
  var full = true;
  while (true) {
    if (total + size <= population) {
      total += size;
      last = size;
      levels++;
      if (total == population) break;
      size *= recruitsPerPerson;
    } else {
      final rest = population - total;
      if (rest > 0) {
        total += rest;
        last = rest;
        levels++;
        full = false;
      }
      break;
    }
  }
  return PyramidModel(
    levels: levels,
    participants: total,
    lastLevel: last,
    lastLevelShareBp: MoneyRounding.divide(last * 10000, total),
    lastLevelFull: full,
  );
}
