import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:meta/meta.dart';

/// 8-qonun hisoblari (SPEC 2H.1, 2H.4). Pul — minor birlikda, yaxlitlash
/// `core/money` standarti (yarmidan yuqoriga).
abstract final class LearningMath {
  /// Kunlik daqiqa 1…1440 yoki oydagi kunlar 1…31 dan tashqarida.
  static const errInvalidHours = 'learning_invalid_hours';

  /// Manfiy summa yoki vaqt.
  static const errInvalidAmount = 'learning_invalid_amount';

  /// Kunlik jismoniy chegara standarti — 12 soat (foydalanuvchi o'zgartiradi).
  static const int defaultMaxMinutesPerDay = 12 * 60;
}

/// «Bir soatim qancha turadi?» natijasi (SPEC 2H.1).
@immutable
final class HourlyValue {
  const HourlyValue({
    required this.monthlyMinutes,
    required this.hourly,
    required this.ceilingIncome,
    required this.loadBp,
    required this.doubleByHoursFeasible,
  });

  final int monthlyMinutes;

  /// Bir soat mehnatning qiymati.
  final Money hourly;

  /// Faqat soat qo'shib erishiladigan eng katta oylik daromad.
  final Money ceilingIncome;

  /// Kunlik chegaraning band qismi (10 000 = to'liq; oshishi mumkin).
  final int loadBp;

  /// Daromadni faqat soatni ko'paytirib ikki barobar qilish mumkinmi.
  final bool doubleByHoursFeasible;

  /// «Ikki barobar» maqsadi (SPEC 2H.2).
  Money get doubledHourly => hourly.times(2);
}

/// Umumiy vektor `spec/test-vectors/hourly_value.json`.
HourlyValue hourlyValue({
  required Money income,
  required int minutesPerDay,
  required int daysPerMonth,
  int maxMinutesPerDay = LearningMath.defaultMaxMinutesPerDay,
}) {
  bool inDay(int m) => m >= 1 && m <= 24 * 60;
  if (!inDay(minutesPerDay) ||
      !inDay(maxMinutesPerDay) ||
      daysPerMonth < 1 ||
      daysPerMonth > 31) {
    throw const DomainRuleException(LearningMath.errInvalidHours);
  }
  if (income.isNegative) {
    throw const DomainRuleException(LearningMath.errInvalidAmount);
  }
  final monthly = minutesPerDay * daysPerMonth;
  return HourlyValue(
    monthlyMinutes: monthly,
    hourly: Money(
      MoneyRounding.mulDiv(income.minorUnits, 60, monthly),
      income.currency,
    ),
    ceilingIncome: Money(
      MoneyRounding.mulDiv(income.minorUnits, maxMinutesPerDay, minutesPerDay),
      income.currency,
    ),
    loadBp: MoneyRounding.mulDiv(minutesPerDay, 10000, maxMinutesPerDay),
    doubleByHoursFeasible: 2 * minutesPerDay <= maxMinutesPerDay,
  );
}

/// «O'qish qachon o'zini qoplaydi?» (SPEC 2H.4). **Taxmin**, va'da emas.
@immutable
final class SkillPayback {
  const SkillPayback({
    required this.timeCost,
    required this.totalInvest,
    required this.monthlyGain,
    required this.paybackMonths,
  });

  /// O'qishga ketgan soatlar qiymati (joriy soat qiymati bo'yicha).
  final Money timeCost;

  /// Narx + vaqt qiymati.
  final Money totalInvest;

  /// Maqsad soat qiymatiga yetilsa, oyiga qo'shimcha daromad.
  final Money monthlyGain;

  /// `null` — bu maqsad bilan qoplanmaydi (qo'shimcha daromad yo'q).
  final int? paybackMonths;
}

/// Umumiy vektor `spec/test-vectors/skill_payback.json`.
SkillPayback skillPayback({
  required Money cost,
  required int studyMinutes,
  required Money currentHourly,
  required Money targetHourly,
  required int monthlyMinutes,
}) {
  if (cost.currency != currentHourly.currency ||
      targetHourly.currency != currentHourly.currency) {
    throw CurrencyMismatchException(cost.currency, currentHourly.currency);
  }
  if (cost.isNegative ||
      currentHourly.isNegative ||
      targetHourly.isNegative ||
      studyMinutes < 0 ||
      monthlyMinutes < 0) {
    throw const DomainRuleException(LearningMath.errInvalidAmount);
  }
  final currency = currentHourly.currency;
  final timeCost = MoneyRounding.mulDiv(
    currentHourly.minorUnits,
    studyMinutes,
    60,
  );
  final total = cost.minorUnits + timeCost;
  final perHour = targetHourly.minorUnits - currentHourly.minorUnits;
  final gain = perHour <= 0
      ? 0
      : MoneyRounding.mulDiv(perHour, monthlyMinutes, 60);
  return SkillPayback(
    timeCost: Money(timeCost, currency),
    totalInvest: Money(total, currency),
    monthlyGain: Money(gain, currency),
    paybackMonths: total == 0
        ? 0
        : gain == 0
        ? null
        : (total + gain - 1) ~/ gain,
  );
}
