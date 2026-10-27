import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:meta/meta.dart';

/// Xarajatning amaldagi toifasi (SPEC 2B.2, 2B.8).
///
/// * Sadaqa — toifadan tashqari (`null`): havas ham, «oqib ketish» ham emas,
///   foydalanuvchi qo'lda «havas» deb belgilasa ham.
/// * Aks holda xarajatning o'z toifasi, bo'lmasa kategoriyaning standarti.
Necessity? effectiveNecessity(Expense e, Category? category) {
  if (category?.systemKey == CategoryKey.sadaqa) return null;
  return e.necessity ?? category?.defaultNecessity;
}

/// Havas chegarasiga kiradimi: amaldagi toifa havas va sovg'a emas
/// («siz olib kelsangiz hisobga kirmaydi»).
bool countsAsHavas(Expense e, Category? category) =>
    !e.isGift && effectiveNecessity(e, category) == Necessity.havas;

/// Qarz bilan qilingan havas — qizil bayroq (SPEC 2B.8).
bool isDebtFundedHavas(Expense e, Category? category) =>
    e.fundedByDebt && effectiveNecessity(e, category) == Necessity.havas;

/// Ogohlantirish darajasi (bloklash yo'q).
enum LimitLevel { ok, near, over }

/// 80 % — yaqinlashdi, 100 % — oshdi.
const int nearLimitBasisPoints = 8000;

@immutable
final class LimitUsage {
  const LimitUsage({required this.spent, required this.limit});

  final Money spent;
  final Money limit;

  /// Sarflangan ulush, bazis punktda (pastga yaxlitlangan).
  int get basisPoints => ratioBasisPoints(spent, limit, RoundingMode.down) ?? 0;

  LimitLevel get level => basisPoints >= basisPointsWhole
      ? LimitLevel.over
      : basisPoints >= nearLimitBasisPoints
      ? LimitLevel.near
      : LimitLevel.ok;

  Money get remaining => limit - spent;
}

/// Jamlash effekti (SPEC 2B.1): [windowDays] kunlik jamidan hafta / oy /
/// yil bo'yicha prognoz (butun birlikgacha). «Kuniga 2 ta ichimlik = oyiga
/// X, yiliga Y».
@immutable
final class Rollup {
  const Rollup(this.total, this.windowDays)
    : assert(windowDays > 0, 'windowDays > 0');

  final Money total;
  final int windowDays;

  Money get perWeek => _project(7);
  Money get perMonth => _project(30);
  Money get perYear => _project(365);

  /// Prognoz — butun so'mgacha (tiyin aniqligi ortiqcha).
  Money _project(int days) =>
      total.scaled(days, windowDays).roundTo(total.currency.minorPerMajor);
}
