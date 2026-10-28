import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/learning/data/drift_learning_repositories.dart';
import 'package:baraka_daftari/features/learning/domain/course_check.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:baraka_daftari/features/learning/domain/learning_service.dart';
import 'package:baraka_daftari/features/learning/presentation/learning_widgets.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

const Map<CourseQuestion, OfferAnswer> cleanCourse = {
  CourseQuestion.incomePromise: OfferAnswer.no,
  CourseQuestion.pressure: OfferAnswer.no,
  CourseQuestion.referralIncome: OfferAnswer.no,
  CourseQuestion.secretMethod: OfferAnswer.no,
  CourseQuestion.curriculumShown: OfferAnswer.yes,
  CourseQuestion.teacherPractices: OfferAnswer.yes,
  CourseQuestion.refundTerms: OfferAnswer.yes,
};

void main() {
  late TestDb t;
  late LearningService s;
  late DriftIncomeRepository incomes;

  setUp(() {
    t = TestDb.open();
    incomes = DriftIncomeRepository(t.db, t.clock);
    s = LearningService(
      households: DriftHouseholdRepository(t.db, t.clock),
      incomes: incomes,
      snapshots: DriftHourlySnapshotRepository(t.db, t.clock),
      goals: DriftLearningGoalRepository(t.db, t.clock),
      items: DriftLearningItemRepository(t.db, t.clock),
      teachings: DriftTeachingEntryRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
  });

  /// Kuniga 9 soat, 26 kun, oyiga 6 mln.
  Future<void> calc() => s.calculate(
    income: som(6000000),
    minutesPerDay: 540,
    daysPerMonth: 26,
  );

  group('soat qiymati va maqsad (SPEC 2H.1–2H.2)', () {
    test('soat qiymatisiz maqsad ochilmaydi', () async {
      expect(
        () => s.createGoal(title: 'Buxgalteriya'),
        rule(LearningService.errNoHourly),
      );
    });

    test('hisob tarixga yoziladi; maqsad standarti — ikki barobar', () async {
      final (snap, v) = await s.calculate(
        income: som(6000000),
        minutesPerDay: 540,
        daysPerMonth: 26,
      );
      expect(v.hourly.minorUnits, 2564103);
      expect(v.loadBp, 7500);
      expect(v.doubleByHoursFeasible, isFalse);
      expect((await s.latestSnapshot())!.meta.id, snap.meta.id);
      expect((await s.latestSnapshot())!.value.ceilingIncome, som(8000000));

      final g = await s.createGoal(title: '  Buxgalteriya  ', why: ' ');
      expect(g.title, 'Buxgalteriya');
      expect(g.why, isNull);
      expect(g.baseHourly.minorUnits, 2564103);
      expect(g.targetHourly.minorUnits, 5128206);
      expect(g.status, LearningGoalStatus.active);
    });

    test('notoʻgʻri soat — INVALID_HOURS, nom boʻsh — xato', () async {
      expect(
        () => s.calculate(
          income: som(1000),
          minutesPerDay: 0,
          daysPerMonth: 26,
        ),
        rule(LearningMath.errInvalidHours),
      );
      await calc();
      expect(
        () => s.createGoal(title: ' '),
        rule(LearningService.errTitleRequired),
      );
    });

    test('oʻtgan oy daromadi taklif qilinadi (asosiy valyutada)', () async {
      expect(await s.lastMonthIncome(), isNull);
      final hid = await t.householdId();
      // FakeClock: 2026-10-09 → oʻtgan oy — sentabr.
      for (final (major, day) in [(3000000, 5), (2500000, 20)]) {
        await incomes.add(
          Income(
            meta: t.meta.create(hid),
            amount: som(major),
            source: IncomeSource.salary,
            channel: PaymentChannel.card,
            receivedAt: Tashkent.startOfDay(LocalDate(2026, 9, day)),
          ),
        );
      }
      await incomes.add(
        Income(
          meta: t.meta.create(hid),
          amount: som(999),
          source: IncomeSource.other,
          channel: PaymentChannel.cash,
          receivedAt: Tashkent.startOfDay(LocalDate(2026, 10, 2)),
        ),
      );
      expect(await s.lastMonthIncome(), som(5500000));
    });

    test('maqsad holati: erishildi va qayta ochish', () async {
      await calc();
      final g = await s.createGoal(title: 'Ingliz tili');
      final done = await s.setGoalStatus(g, LearningGoalStatus.done);
      expect(done.closedAt, isNotNull);
      final again = await s.setGoalStatus(done, LearningGoalStatus.active);
      expect(again.closedAt, isNull);
    });
  });

  group('oʻqish yoʻllari (SPEC 2H.3)', () {
    test('natija maqsadisiz yoʻl saqlanmaydi', () async {
      await calc();
      final g = await s.createGoal(title: 'Excel');
      expect(
        () => s.addItem(
          goalId: g.meta.id,
          kind: LearningItemKind.book,
          title: 'Kitob',
          purpose: '  ',
        ),
        rule(LearningService.errPurposeRequired),
      );
      final item = await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.book,
        title: 'Kitob',
        purpose: 'Oylik hisobotni oʻzim tuzaman',
        cost: const Money.zero(CurrencyCode.uzs),
        studyMinutes: 0,
      );
      expect(item.cost, isNull);
      expect(item.studyMinutes, isNull);
      expect(item.status, LearningItemStatus.planned);
    });

    test('«tugatdim» natijasiz boʻlmaydi', () async {
      await calc();
      final g = await s.createGoal(title: 'Excel');
      final item = await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.practice,
        title: 'Oʻz ishimda',
        purpose: 'Jadvalni tez toʻldiraman',
      );
      expect(
        () => s.setItemStatus(item, LearningItemStatus.done),
        rule(LearningService.errOutcomeRequired),
      );
      final done = await s.setItemStatus(
        item,
        LearningItemStatus.done,
        outcome: 'Hisobot 2 soatda emas, 20 daqiqada',
      );
      expect(done.completedAt, isNotNull);
      expect(done.outcome, 'Hisobot 2 soatda emas, 20 daqiqada');
    });
  });

  group('kurs tekshiruvi (SPEC 2H.5)', () {
    test('ikki belgi bahoni qizilga koʻtaradi', () {
      final one = evaluateCourse({
        ...cleanCourse,
        CourseQuestion.pressure: OfferAnswer.yes,
      });
      expect(one.verdict, OfferVerdict.yellow);
      final two = evaluateCourse({
        ...cleanCourse,
        CourseQuestion.pressure: OfferAnswer.yes,
        CourseQuestion.refundTerms: OfferAnswer.no,
      });
      expect(two.verdict, OfferVerdict.red);
      expect(two.signs, [ScamSign.urgency, ScamSign.hardExit]);
      expect(evaluateCourse(cleanCourse).verdict, OfferVerdict.green);
    });

    test('javoblar JSON orqali qaytadi', () {
      final a = {
        CourseQuestion.pressure: OfferAnswer.yes,
        CourseQuestion.refundTerms: OfferAnswer.unknown,
      };
      expect(courseAnswersFromJson(courseAnswersToJson(a)), a);
      expect(courseAnswersFromJson('{"x":"yes","pressure":"maybe"}'), isEmpty);
      expect(courseAnswersFromJson(null), isEmpty);
    });

    test('qizil kursni boshlash — faqat alohida tasdiq bilan', () async {
      await calc();
      final g = await s.createGoal(title: 'Dasturlash');
      final book = await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.book,
        title: 'Kitob',
        purpose: 'Sayt yasayman',
      );
      expect(
        () => s.saveCourseCheck(book, cleanCourse),
        rule(LearningService.errNotCourse),
      );
      final course = await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.course,
        title: 'Tezkor kurs',
        purpose: 'Sayt yasayman',
      );
      final (saved, e) = await s.saveCourseCheck(course, {
        ...cleanCourse,
        CourseQuestion.incomePromise: OfferAnswer.yes,
        CourseQuestion.referralIncome: OfferAnswer.yes,
      });
      expect(e.level, ScamLevel.flee);
      expect(saved.courseVerdict, OfferVerdict.red);
      expect(
        () => s.setItemStatus(saved, LearningItemStatus.inProgress),
        rule(LearningService.errRedCourse),
      );
      final started = await s.setItemStatus(
        saved,
        LearningItemStatus.inProgress,
        confirmRedCourse: true,
      );
      expect(started.status, LearningItemStatus.inProgress);
    });
  });

  group('qoplanish (SPEC 2H.4)', () {
    test('qoʻshimcha daromad yoʻq — «qoplanmaydi»', () async {
      await calc();
      final base = (await s.latestSnapshot())!.hourly;
      final g = await s.createGoal(title: 'Kurs', targetHourly: base);
      await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.course,
        title: 'Kurs',
        purpose: 'Mijoz bilan ishlash',
        cost: som(500000),
      );
      final p = (await s.payback(g))!;
      expect(p.monthlyGain.isZero, isTrue);
      expect(p.paybackMonths, isNull);
    });

    test('yoʻllar narxi va vaqti yigʻiladi, tashlanganlari kirmaydi', () async {
      await calc();
      final g = await s.createGoal(title: 'Kurs');
      await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.course,
        title: 'Kurs',
        purpose: 'Hisobot',
        cost: som(3000000),
        studyMinutes: 6000,
      );
      final dropped = await s.addItem(
        goalId: g.meta.id,
        kind: LearningItemKind.book,
        title: 'Kitob',
        purpose: 'Hisobot',
        cost: som(9000000),
      );
      await s.setItemStatus(dropped, LearningItemStatus.dropped);
      final p = (await s.payback(g))!;
      // skill_payback.json sp-001 bilan bir xil.
      expect(p.timeCost.minorUnits, 256410300);
      expect(p.totalInvest.minorUnits, 556410300);
      expect(p.monthlyGain.minorUnits, 600000102);
      expect(p.paybackMonths, 1);
    });
  });

  group('«oʻrgatganlarim» (SPEC 2H.6)', () {
    test('kimga va nima majburiy; bugungi sana', () async {
      expect(
        () => s.logTeaching(learner: 'Ukam', topic: ' '),
        rule(LearningService.errTeachingRequired),
      );
      final e = await s.logTeaching(
        learner: ' Ukam ',
        topic: 'Jadvalda formula',
        minutes: 30,
      );
      expect(e.learner, 'Ukam');
      expect(e.taughtOn, LocalDate(2026, 10, 9));
      expect((await s.teachings()).single.minutes, 30);
    });
  });

  group('soat kiritish yordamchilari', () {
    test('soat → daqiqa va qaytish', () {
      expect(parseHoursToMinutes('9'), 540);
      expect(parseHoursToMinutes('7,5'), 450);
      expect(parseHoursToMinutes('7.25'), 435);
      expect(parseHoursToMinutes('abc'), isNull);
      expect(hoursLabel(450), '7,5');
      expect(hoursLabel(540), '9');
    });

    test('davomiylik: bir soatdan kami daqiqada', () {
      final l10n = lookupAppLocalizations(const Locale('uz'));
      expect(durationLabel(l10n, 45), '45 daqiqa');
      expect(durationLabel(l10n, 59), '59 daqiqa');
      expect(durationLabel(l10n, 60), '1 soat');
      expect(durationLabel(l10n, 90), '1,5 soat');
      expect(
        durationLabel(lookupAppLocalizations(const Locale('ru')), 45),
        '45 мин',
      );
    });

    test('taxminiy summa ekranda yaxlitlanadi', () {
      Money tiyin(int minor) => Money(minor, CurrencyCode.uzs);
      // 6 000 000 soʻm, 8 soat × 26 kun, ikki barobar maqsad: oylik
      // qoʻshimcha 5 999 999,20 soʻm (vektorlar) → ekranda 6 000 000.
      expect(estimateDisplay(tiyin(599999920)), som(6000000));
      expect(estimateDisplay(tiyin(149950)), som(1000));
      expect(estimateDisplay(tiyin(150000)), som(2000));
      expect(estimateDisplay(tiyin(49950)), som(500));
      expect(estimateDisplay(tiyin(49949)), som(499));
      expect(estimateDisplay(tiyin(0)), som(0));
    });
  });
}
