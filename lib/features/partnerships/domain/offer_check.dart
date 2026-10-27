import 'dart:convert';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:meta/meta.dart';

/// «Kafolatlangan foyda» detektori savollari (SPEC 2E.5, 7-qonunda 2G.1).
enum OfferQuestion {
  /// Foyda kafolatlanganmi?
  guaranteed,

  /// Zarar bo'lishiladimi?
  lossShared,

  /// Real mol yoki ish bormi?
  realGoods,

  /// Yangi a'zo jalb qilish talab qilinadimi?
  recruitment,

  /// Shoshiltirish bormi?
  pressure,

  /// Yozma shartnoma bormi?
  writtenContract,

  /// Pulni istagan vaqtda qaytarib olsa bo'ladimi? (2G.1, «chiqish qiyin»)
  exitEasy,

  /// Odamlardan pul yig'ishga davlat ruxsati bormi? (2G.1)
  license,

  /// Ishni o'z ko'zingiz bilan ko'rdingizmi yoki ko'rsatishdimi? (2G.2)
  verifiedInPerson,
}

enum OfferAnswer { yes, no, unknown }

/// Besh xavf belgisi (SPEC 2G.1): bittasini ko'rsangiz hushyor torting,
/// ikkitasini ko'rsangiz qoching.
enum ScamSign {
  /// Katta foyda kafolatlab va'da qilinadi.
  guaranteedHighReturn,

  /// «Faqat bugun», «joy kam» — shoshiriladi.
  urgency,

  /// Daromad moldan emas, yangi odam olib kelishdan.
  recruitmentIncome,

  /// Ishning o'zi ko'rinmaydi: mol, ruxsat yo'q yoki tekshirishga yo'l
  /// berilmaydi.
  noRealBusiness,

  /// Kirish oson, chiqish qiyin.
  hardExit;

  /// Umumiy vektordagi kod (`GUARANTEED_HIGH_RETURN`).
  String get code =>
      name.replaceAllMapped(RegExp('[A-Z]'), (m) => '_${m[0]}').toUpperCase();
}

/// Belgilar soni bo'yicha daraja: 0 — yo'q, 1 — hushyor, 2+ — qoch.
enum ScamLevel { none, caution, flee }

/// Taklif toifasi (SPEC 2G.7): ribo, g'arar (noaniq bitim), qimor (yutuq
/// boshqaning yutqazishidan).
enum OfferCategory { ribo, gharar, qimor }

/// Bitta bayroq: qaysi savol va qanchalik xavfli.
@immutable
final class OfferFlag {
  const OfferFlag(this.question, this.level);

  final OfferQuestion question;
  final OfferVerdict level;

  @override
  bool operator ==(Object other) =>
      other is OfferFlag && other.question == question && other.level == level;

  @override
  int get hashCode => Object.hash(question, level);

  @override
  String toString() => 'OfferFlag(${question.name}, ${level.name})';
}

/// Qaror jadvali: har savol uchun qaysi javob qaysi bayroqni beradi.
///
/// | Savol | qizil | sariq |
/// |---|---|---|
/// | kafolatlangan foyda | ha | bilmayman |
/// | zarar bo'lishiladi | yo'q | bilmayman |
/// | real mol / ish | yo'q | bilmayman |
/// | yangi a'zo jalb qilish | ha | bilmayman |
/// | shoshiltirish | — | ha, bilmayman |
/// | yozma shartnoma | — | yo'q, bilmayman |
/// | pulni istagan vaqtda qaytarish | — | yo'q, bilmayman |
/// | davlat ruxsati | — | yo'q, bilmayman |
/// | o'z ko'zi bilan tekshirish | — | yo'q, bilmayman |
///
/// Tavakkalsiz, kafolatlangan foyda va'da qilinsa — yo ribo, yo firibgarlik.
/// Sariq bayroqlar besh belgi qoidasi (2G.1) bilan qizilga ko'tarilishi mumkin.
OfferVerdict? _flagFor(OfferQuestion q, OfferAnswer a) {
  if (a == OfferAnswer.unknown) return OfferVerdict.yellow;
  return switch (q) {
    OfferQuestion.guaranteed => a == OfferAnswer.yes ? OfferVerdict.red : null,
    OfferQuestion.lossShared => a == OfferAnswer.no ? OfferVerdict.red : null,
    OfferQuestion.realGoods => a == OfferAnswer.no ? OfferVerdict.red : null,
    OfferQuestion.recruitment => a == OfferAnswer.yes ? OfferVerdict.red : null,
    OfferQuestion.pressure => a == OfferAnswer.yes ? OfferVerdict.yellow : null,
    OfferQuestion.writtenContract ||
    OfferQuestion.exitEasy ||
    OfferQuestion.license ||
    OfferQuestion.verifiedInPerson =>
      a == OfferAnswer.no ? OfferVerdict.yellow : null,
  };
}

/// Besh belgi javoblardan (SPEC 2G.1); tartib — `ScamSign` tartibida, har
/// belgi bir marta.
List<ScamSign> scamSigns(Map<OfferQuestion, OfferAnswer> answers) {
  OfferAnswer of(OfferQuestion q) => answers[q] ?? OfferAnswer.unknown;
  return [
    if (of(OfferQuestion.guaranteed) == OfferAnswer.yes)
      ScamSign.guaranteedHighReturn,
    if (of(OfferQuestion.pressure) == OfferAnswer.yes) ScamSign.urgency,
    if (of(OfferQuestion.recruitment) == OfferAnswer.yes)
      ScamSign.recruitmentIncome,
    if (const [
      OfferQuestion.realGoods,
      OfferQuestion.license,
      OfferQuestion.verifiedInPerson,
    ].any((q) => of(q) == OfferAnswer.no))
      ScamSign.noRealBusiness,
    if (of(OfferQuestion.exitEasy) == OfferAnswer.no) ScamSign.hardExit,
  ];
}

ScamLevel scamLevel(int signs) => switch (signs) {
  0 => ScamLevel.none,
  1 => ScamLevel.caution,
  _ => ScamLevel.flee,
};

/// Tekshiruv natijasi: umumiy baho, izohlanadigan bayroqlar, besh belgi va
/// toifalar.
@immutable
final class OfferEvaluation {
  const OfferEvaluation(
    this.verdict,
    this.flags, {
    this.signs = const [],
    this.level = ScamLevel.none,
    this.categories = const [],
  });

  final OfferVerdict verdict;
  final List<OfferFlag> flags;
  final List<ScamSign> signs;
  final ScamLevel level;
  final List<OfferCategory> categories;
}

OfferVerdict _worst(OfferVerdict a, OfferVerdict b) =>
    a.index >= b.index ? a : b;

/// Javoblarni baholash; javob berilmagan savol — «bilmayman». Umumiy baho —
/// 2E.5 bayroqlari va besh belgi darajasining eng og'iri (SPEC 2G.1).
OfferEvaluation evaluateOffer(Map<OfferQuestion, OfferAnswer> answers) {
  final flags = <OfferFlag>[
    for (final q in OfferQuestion.values)
      if (_flagFor(q, answers[q] ?? OfferAnswer.unknown) case final level?)
        OfferFlag(q, level),
  ];
  final base = flags.any((f) => f.level == OfferVerdict.red)
      ? OfferVerdict.red
      : flags.isNotEmpty
      ? OfferVerdict.yellow
      : OfferVerdict.green;
  final signs = scamSigns(answers);
  final level = scamLevel(signs.length);
  final byLevel = switch (level) {
    ScamLevel.none => OfferVerdict.green,
    ScamLevel.caution => OfferVerdict.yellow,
    ScamLevel.flee => OfferVerdict.red,
  };
  return OfferEvaluation(
    _worst(base, byLevel),
    flags,
    signs: signs,
    level: level,
    categories: [
      if (answers[OfferQuestion.guaranteed] == OfferAnswer.yes)
        OfferCategory.ribo,
      if (signs.contains(ScamSign.noRealBusiness)) OfferCategory.gharar,
      if (signs.contains(ScamSign.recruitmentIncome)) OfferCategory.qimor,
    ],
  );
}

/// «To'xta, maslahatlash» (SPEC 2G.6): tekshiruvdan keyin kamida shuncha
/// vaqt o'tmaguncha «pul qo'yaman» qarori ochilmaydi.
const offerCoolingOff = Duration(hours: 24);

/// «Pul qo'yaman» qachon ochiladi.
DateTime acceptOpensAt(DateTime checkedAt) => checkedAt.add(offerCoolingOff);

String offerAnswersToJson(Map<OfferQuestion, OfferAnswer> a) =>
    jsonEncode({for (final e in a.entries) e.key.name: e.value.name});

/// Saqlangan javoblar. Noma'lum savol kodi (boshqa versiya) e'tiborsiz
/// qoldiriladi.
Map<OfferQuestion, OfferAnswer> offerAnswersFromJson(String json) {
  final questions = OfferQuestion.values.asNameMap();
  final answers = OfferAnswer.values.asNameMap();
  return {
    for (final e in (jsonDecode(json) as Map<String, dynamic>).entries)
      if ((questions[e.key], answers[e.value]) case (
        final q?,
        final a?,
      ))
        q: a,
  };
}
