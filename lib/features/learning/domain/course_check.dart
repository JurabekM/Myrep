import 'dart:convert';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:meta/meta.dart';

/// Kurs tekshiruvi savollari (SPEC 2H.5): 2G.1 besh belgisi o'qish
/// takliflariga moslab.
enum CourseQuestion {
  /// Qisqa vaqtda ma'lum daromad kafolatlanadimi?
  incomePromise,

  /// «Faqat bugun», «joy kam» deb shoshirishadimi?
  pressure,

  /// Daromad yangi o'quvchi olib kelishdanmi?
  referralIncome,

  /// «Faqat shu yerda o'rgatiladigan maxfiy usul» deb sotiladimi?
  secretMethod,

  /// Dastur, amaliy topshiriqlar va natija oldindan ko'rsatildimi?
  curriculumShown,

  /// O'qituvchi shu ish bilan amalda shug'ullanadimi?
  teacherPractices,

  /// To'lovni qaytarish shartlari yozma bormi?
  refundTerms,
}

/// Kurs tekshiruvi natijasi: belgilar, daraja va baho.
@immutable
final class CourseEvaluation {
  const CourseEvaluation(this.signs, this.level, this.verdict);

  final List<ScamSign> signs;
  final ScamLevel level;
  final OfferVerdict verdict;
}

/// Umumiy vektor `spec/test-vectors/course_check.json`. Javob berilmagan
/// savol — «bilmayman»: belgi emas, lekin baho kamida sariq.
CourseEvaluation evaluateCourse(Map<CourseQuestion, OfferAnswer> answers) {
  OfferAnswer of(CourseQuestion q) => answers[q] ?? OfferAnswer.unknown;
  final signs = [
    if (of(CourseQuestion.incomePromise) == OfferAnswer.yes)
      ScamSign.guaranteedHighReturn,
    if (of(CourseQuestion.pressure) == OfferAnswer.yes) ScamSign.urgency,
    if (of(CourseQuestion.referralIncome) == OfferAnswer.yes)
      ScamSign.recruitmentIncome,
    if (of(CourseQuestion.secretMethod) == OfferAnswer.yes ||
        of(CourseQuestion.curriculumShown) == OfferAnswer.no ||
        of(CourseQuestion.teacherPractices) == OfferAnswer.no)
      ScamSign.noRealBusiness,
    if (of(CourseQuestion.refundTerms) == OfferAnswer.no) ScamSign.hardExit,
  ];
  final level = scamLevel(signs.length);
  final unknown = CourseQuestion.values.any(
    (q) => of(q) == OfferAnswer.unknown,
  );
  final verdict = switch (level) {
    ScamLevel.flee => OfferVerdict.red,
    ScamLevel.caution => OfferVerdict.yellow,
    ScamLevel.none => unknown ? OfferVerdict.yellow : OfferVerdict.green,
  };
  return CourseEvaluation(signs, level, verdict);
}

/// Javoblar → saqlanadigan JSON (`{"pressure": "yes", ...}`).
String courseAnswersToJson(Map<CourseQuestion, OfferAnswer> answers) =>
    jsonEncode({
      for (final q in CourseQuestion.values)
        if (answers[q] case final a?) q.name: a.name,
    });

/// Saqlangan JSON → javoblar; noma'lum kalitlar tashlanadi.
Map<CourseQuestion, OfferAnswer> courseAnswersFromJson(String? json) {
  if (json == null || json.isEmpty) return {};
  final raw = jsonDecode(json) as Map<String, dynamic>;
  return {
    for (final q in CourseQuestion.values)
      if (raw[q.name] case final String a)
        if (OfferAnswer.values.asNameMap()[a] case final answer?) q: answer,
  };
}
