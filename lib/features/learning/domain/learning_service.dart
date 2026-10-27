import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/learning/domain/course_check.dart';
import 'package:baraka_daftari/features/learning/domain/learning.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';

/// 8-qonun (SPEC 2H): soat qiymati, o'qish maqsadi va yo'llari, kurs
/// tekshiruvi, «o'rgatganlarim».
class LearningService {
  LearningService({
    required HouseholdRepository households,
    required IncomeRepository incomes,
    required HourlySnapshotRepository snapshots,
    required LearningGoalRepository goals,
    required LearningItemRepository items,
    required TeachingEntryRepository teachings,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _incomes = incomes,
       _snapshots = snapshots,
       _goals = goals,
       _items = items,
       _teachings = teachings,
       _meta = metaFactory,
       _clock = clock;

  /// Maqsad uchun avval soat qiymati hisoblanadi (SPEC 2H.2).
  static const errNoHourly = 'learning_no_hourly';
  static const errTitleRequired = 'learning_title_required';

  /// «Buni o'rgangach nimani qila olaman?» bo'sh (SPEC 2H.3).
  static const errPurposeRequired = 'learning_purpose_required';

  /// `DONE` uchun erishilgan natija yoziladi.
  static const errOutcomeRequired = 'learning_outcome_required';

  /// Kurs tekshiruvi faqat `COURSE` yo'lida.
  static const errNotCourse = 'learning_not_course';

  /// Qizil bahoni olgan kurs uchun «o'qiyapman» — alohida tasdiq bilan.
  static const errRedCourse = 'learning_red_course';

  /// Kimga va nimani o'rgatgani bo'sh (SPEC 2H.6).
  static const errTeachingRequired = 'learning_teaching_required';

  final HouseholdRepository _households;
  final IncomeRepository _incomes;
  final HourlySnapshotRepository _snapshots;
  final LearningGoalRepository _goals;
  final LearningItemRepository _items;
  final TeachingEntryRepository _teachings;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get _today => Tashkent.dateOf(_clock.nowUtc());

  Future<String> get _householdId async =>
      (await _households.current()).meta.id;

  /// O'tgan to'liq oyning daromadi (asosiy valyutada) — kalkulyatorga
  /// taklif. Daromad yozilmagan bo'lsa `null`.
  Future<Money?> lastMonthIncome() async {
    final h = await _households.current();
    final period = h.calendar.previousMonthOf(_today);
    final list = await _incomes.listInRange(h.meta.id, period);
    var total = Money.zero(h.baseCurrency);
    var any = false;
    for (final i in list) {
      if (i.amount.currency != h.baseCurrency) continue;
      total += i.amount;
      any = true;
    }
    return any ? total : null;
  }

  /// Hisoblaydi va tarixga yozadi (SPEC 2H.1).
  Future<(HourlySnapshot, HourlyValue)> calculate({
    required Money income,
    required int minutesPerDay,
    required int daysPerMonth,
    int maxMinutesPerDay = LearningMath.defaultMaxMinutesPerDay,
  }) async {
    final v = hourlyValue(
      income: income,
      minutesPerDay: minutesPerDay,
      daysPerMonth: daysPerMonth,
      maxMinutesPerDay: maxMinutesPerDay,
    );
    final s = await _snapshots.add(
      HourlySnapshot(
        meta: _meta.create(await _householdId),
        income: income,
        minutesPerDay: minutesPerDay,
        daysPerMonth: daysPerMonth,
        maxMinutesPerDay: maxMinutesPerDay,
        hourly: v.hourly,
      ),
    );
    return (s, v);
  }

  /// Eng yangisi birinchi.
  Future<List<HourlySnapshot>> snapshots() async =>
      _snapshots.listActive(await _householdId);

  Future<HourlySnapshot?> latestSnapshot() async =>
      (await snapshots()).firstOrNull;

  Future<List<LearningGoal>> goals() async =>
      _goals.listActive(await _householdId);

  /// Maqsad: boshlang'ich soat qiymati — oxirgi hisob; maqsad standarti —
  /// ikki barobar (SPEC 2H.2).
  Future<LearningGoal> createGoal({
    required String title,
    String? why,
    Money? targetHourly,
  }) async {
    final name = title.trim();
    if (name.isEmpty) throw const DomainRuleException(errTitleRequired);
    final latest = await latestSnapshot();
    if (latest == null) throw const DomainRuleException(errNoHourly);
    final base = latest.hourly;
    final target = targetHourly ?? base.times(2);
    if (target.currency != base.currency) {
      throw CurrencyMismatchException(base.currency, target.currency);
    }
    if (target.isNegative) {
      throw const DomainRuleException(LearningMath.errInvalidAmount);
    }
    final reason = why?.trim();
    return _goals.add(
      LearningGoal(
        meta: _meta.create(await _householdId),
        title: name,
        why: reason == null || reason.isEmpty ? null : reason,
        baseHourly: base,
        targetHourly: target,
        status: LearningGoalStatus.active,
      ),
    );
  }

  Future<LearningGoal> setGoalStatus(
    LearningGoal goal,
    LearningGoalStatus status,
  ) async {
    final fresh = await _goals.findById(goal.meta.id) ?? goal;
    return _goals.update(
      fresh.copyWith(
        status: status,
        closedAt: status == LearningGoalStatus.active ? null : _clock.nowUtc(),
      ),
    );
  }

  Future<List<LearningItem>> items(String goalId) => _items.forGoal(goalId);

  /// Yangi yo'l (SPEC 2H.3): natija maqsadi majburiy.
  Future<LearningItem> addItem({
    required String goalId,
    required LearningItemKind kind,
    required String title,
    required String purpose,
    Money? cost,
    int? studyMinutes,
  }) async {
    final name = title.trim();
    final aim = purpose.trim();
    if (name.isEmpty) throw const DomainRuleException(errTitleRequired);
    if (aim.isEmpty) throw const DomainRuleException(errPurposeRequired);
    if ((cost?.isNegative ?? false) || (studyMinutes ?? 0) < 0) {
      throw const DomainRuleException(LearningMath.errInvalidAmount);
    }
    return _items.add(
      LearningItem(
        meta: _meta.create(await _householdId),
        goalId: goalId,
        kind: kind,
        title: name,
        purpose: aim,
        status: LearningItemStatus.planned,
        cost: cost == null || cost.isZero ? null : cost,
        studyMinutes: studyMinutes == null || studyMinutes == 0
            ? null
            : studyMinutes,
      ),
    );
  }

  /// Kurs tekshiruvi natijasini yo'lga yozadi (SPEC 2H.5).
  Future<(LearningItem, CourseEvaluation)> saveCourseCheck(
    LearningItem item,
    Map<CourseQuestion, OfferAnswer> answers,
  ) async {
    if (item.kind != LearningItemKind.course) {
      throw const DomainRuleException(errNotCourse);
    }
    final e = evaluateCourse(answers);
    final fresh = await _items.findById(item.meta.id) ?? item;
    final saved = await _items.update(
      fresh.copyWith(
        courseAnswersJson: courseAnswersToJson(answers),
        courseVerdict: e.verdict,
      ),
    );
    return (saved, e);
  }

  /// Holat: `DONE` — natija bilan; qizil kursni boshlash — [confirmRedCourse]
  /// bilan.
  Future<LearningItem> setItemStatus(
    LearningItem item,
    LearningItemStatus status, {
    String? outcome,
    bool confirmRedCourse = false,
  }) async {
    final fresh = await _items.findById(item.meta.id) ?? item;
    final result = (outcome ?? fresh.outcome ?? '').trim();
    if (status == LearningItemStatus.done && result.isEmpty) {
      throw const DomainRuleException(errOutcomeRequired);
    }
    if (status == LearningItemStatus.inProgress &&
        fresh.kind == LearningItemKind.course &&
        fresh.courseVerdict == OfferVerdict.red &&
        !confirmRedCourse) {
      throw const DomainRuleException(errRedCourse);
    }
    return _items.update(
      fresh.copyWith(
        status: status,
        outcome: result.isEmpty ? null : result,
        completedAt: status == LearningItemStatus.done ? _clock.nowUtc() : null,
      ),
    );
  }

  /// Maqsad bo'yicha qoplanish (SPEC 2H.4): tashlab ketilmagan yo'llarning
  /// narxi (maqsad valyutasida) va vaqti; oylik daqiqa — oxirgi hisobdan.
  /// Hisob bo'lmasa `null`.
  Future<SkillPayback?> payback(LearningGoal goal) async {
    final latest = await latestSnapshot();
    if (latest == null) return null;
    final currency = goal.baseHourly.currency;
    var cost = Money.zero(currency);
    var minutes = 0;
    for (final i in await _items.forGoal(goal.meta.id)) {
      if (!i.counts) continue;
      if (i.cost case final c? when c.currency == currency) cost += c;
      minutes += i.studyMinutes ?? 0;
    }
    return skillPayback(
      cost: cost,
      studyMinutes: minutes,
      currentHourly: goal.baseHourly,
      targetHourly: goal.targetHourly,
      monthlyMinutes: latest.value.monthlyMinutes,
    );
  }

  /// Eng yangi sana birinchi.
  Future<List<TeachingEntry>> teachings() async =>
      _teachings.listActive(await _householdId);

  Future<TeachingEntry> logTeaching({
    required String learner,
    required String topic,
    LocalDate? on,
    int? minutes,
    String? note,
  }) async {
    final who = learner.trim();
    final what = topic.trim();
    if (who.isEmpty || what.isEmpty) {
      throw const DomainRuleException(errTeachingRequired);
    }
    if ((minutes ?? 0) < 0) {
      throw const DomainRuleException(LearningMath.errInvalidAmount);
    }
    final text = note?.trim();
    return _teachings.add(
      TeachingEntry(
        meta: _meta.create(await _householdId),
        learner: who,
        topic: what,
        taughtOn: on ?? _today,
        minutes: minutes == null || minutes == 0 ? null : minutes,
        note: text == null || text.isEmpty ? null : text,
      ),
    );
  }
}
