import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony.dart';
import 'package:baraka_daftari/features/ceremonies/domain/ceremony_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:meta/meta.dart';

/// Bitta marosim rejasi: stsenariylar taqqoslashi, muhokama holati,
/// to'yona o'rniga jamg'arma.
@immutable
final class CeremonyView {
  const CeremonyView({
    required this.plan,
    required this.scenarios,
    required this.adults,
    required this.markedBy,
    required this.goals,
    this.giftGoal,
    this.giftContributions = const [],
  });

  final CeremonyPlan plan;

  /// Tartib bo'yicha stsenariy xulosalari.
  final List<ScenarioSummary> scenarios;
  final List<Member> adults;

  /// Muhokamaga belgi qo'ygan katta a'zolar.
  final Set<String> markedBy;
  final List<Goal> goals;
  final Goal? giftGoal;
  final List<GoalContribution> giftContributions;

  ScenarioSummary? get selected {
    for (final s in scenarios) {
      if (s.scenario.meta.id == plan.selectedScenarioId) return s;
    }
    return scenarios.isEmpty ? null : scenarios.first;
  }

  /// SPEC 2D.8: tanlangan stsenariyda qarz bilan moliyalangan qator bor —
  /// tasdiqlashdan oldin oilaviy muhokama majburiy.
  bool get needsDiscussion => selected?.hasDebt ?? false;

  bool get discussionComplete =>
      adults.isNotEmpty && adults.every((m) => markedBy.contains(m.meta.id));

  bool get isConfirmed => plan.status == CeremonyStatus.confirmed;

  bool get canConfirm =>
      !isConfirmed &&
      selected != null &&
      selected!.total.isPositive &&
      (!needsDiscussion || plan.status == CeremonyStatus.discussed);

  Money get giftCollected =>
      Money.sum(giftContributions.map((c) => c.amount), plan.currency);
}

/// Marosim rejalovchisi (SPEC 2D.8).
class CeremonyService {
  CeremonyService({
    required HouseholdRepository households,
    required MemberRepository members,
    required MemberPinService memberPins,
    required CeremonyPlanRepository plans,
    required CeremonyScenarioRepository scenarios,
    required CeremonyBudgetLineRepository lines,
    required CeremonyDiscussionMarkRepository marks,
    required GoalRepository goals,
    required GoalContributionRepository contributions,
    required DebtService debts,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _members = members,
       _memberPins = memberPins,
       _plans = plans,
       _scenarios = scenarios,
       _lines = lines,
       _marks = marks,
       _goals = goals,
       _contributions = contributions,
       _debts = debts,
       _meta = metaFactory,
       _clock = clock;

  static const errNameRequired = 'ceremony_name_required';
  static const errNotPositive = 'ceremony_amount_must_be_positive';
  static const errConfirmedLocked = 'ceremony_confirmed_locked';

  /// SPEC 2D.8: qarz manbali qator bilan muhokamasiz tasdiqlab bo'lmaydi.
  static const errDiscussionRequired = 'ceremony_discussion_required';
  static const errAdultOnly = 'ceremony_adult_only';
  static const errScenarioLimit = 'ceremony_scenario_limit';
  static const errLastScenario = 'ceremony_last_scenario';
  static const errNothingToConfirm = 'ceremony_nothing_to_confirm';

  /// SPEC 2D.8: 2–3 stsenariy yonma-yon.
  static const maxScenarios = 3;

  final HouseholdRepository _households;
  final MemberRepository _members;
  final MemberPinService _memberPins;
  final CeremonyPlanRepository _plans;
  final CeremonyScenarioRepository _scenarios;
  final CeremonyBudgetLineRepository _lines;
  final CeremonyDiscussionMarkRepository _marks;
  final GoalRepository _goals;
  final GoalContributionRepository _contributions;
  final DebtService _debts;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  Future<List<CeremonyPlan>> list() async =>
      _plans.listActive((await _households.current()).meta.id);

  /// Yangi reja: qoralama va bitta «Asosiy» stsenariy.
  Future<CeremonyPlan> create({
    required String title,
    required CeremonyType type,
    required String firstScenarioName,
    LocalDate? eventDate,
    int guests = 0,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    final h = await _households.current();
    final plan = await _plans.add(
      CeremonyPlan(
        meta: _meta.create(h.meta.id),
        title: title.trim(),
        type: type,
        currency: h.baseCurrency,
        eventDate: eventDate,
      ),
    );
    final s = await _scenarios.add(
      CeremonyScenario(
        meta: _meta.create(h.meta.id),
        planId: plan.meta.id,
        name: firstScenarioName,
        guests: guests < 0 ? 0 : guests,
      ),
    );
    return _plans.update(plan.copyWith(selectedScenarioId: s.meta.id));
  }

  Future<CeremonyPlan> _fresh(CeremonyPlan p) async =>
      await _plans.findById(p.meta.id) ?? p;

  /// Tasdiqlangan reja o'zgarmaydi; muhokamadan keyin o'zgarsa — muhokama
  /// qaytadan (belgilar o'chiriladi).
  Future<CeremonyPlan> _beforeEdit(String planId) async {
    final plan = (await _plans.findById(planId))!;
    if (plan.status == CeremonyStatus.confirmed) {
      throw const DomainRuleException(errConfirmedLocked);
    }
    if (plan.status == CeremonyStatus.discussed) {
      for (final m in await _marks.forPlan(plan.meta.id)) {
        await _marks.softDelete(m.meta.id);
      }
      return _plans.update(plan.copyWith(status: CeremonyStatus.draft));
    }
    return plan;
  }

  Future<CeremonyScenario> _scenario(String id) async =>
      (await _scenarios.findById(id))!;

  /// Yangi stsenariy; [copyFrom] — qatorlari nusxalanadi (taqqoslash
  /// uchun qulay).
  Future<CeremonyScenario> addScenario(
    CeremonyPlan plan, {
    required String name,
    int guests = 0,
    CeremonyScenario? copyFrom,
  }) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    final p = await _beforeEdit(plan.meta.id);
    final existing = await _scenarios.forPlan(p.meta.id);
    if (existing.length >= maxScenarios) {
      throw const DomainRuleException(errScenarioLimit);
    }
    final hh = p.meta.householdId;
    final s = await _scenarios.add(
      CeremonyScenario(
        meta: _meta.create(hh),
        planId: p.meta.id,
        name: name.trim(),
        guests: guests < 0 ? 0 : guests,
        sortOrder: existing.length,
      ),
    );
    if (copyFrom != null) {
      for (final l in await _lines.forScenario(copyFrom.meta.id)) {
        await _lines.add(
          l.copyWith(meta: _meta.create(hh), scenarioId: s.meta.id),
        );
      }
    }
    return s;
  }

  Future<CeremonyScenario> updateScenario(
    CeremonyScenario s, {
    String? name,
    int? guests,
  }) async {
    await _beforeEdit(s.planId);
    final fresh = await _scenario(s.meta.id);
    return _scenarios.update(
      fresh.copyWith(
        name: name == null || name.trim().isEmpty ? fresh.name : name.trim(),
        guests: guests == null || guests < 0 ? fresh.guests : guests,
      ),
    );
  }

  Future<void> removeScenario(CeremonyScenario s) async {
    final p = await _beforeEdit(s.planId);
    final all = await _scenarios.forPlan(p.meta.id);
    if (all.length <= 1) throw const DomainRuleException(errLastScenario);
    for (final l in await _lines.forScenario(s.meta.id)) {
      await _lines.softDelete(l.meta.id);
    }
    await _scenarios.softDelete(s.meta.id);
    if (p.selectedScenarioId == s.meta.id) {
      final next = all.firstWhere((x) => x.meta.id != s.meta.id);
      await _plans.update(
        (await _fresh(p)).copyWith(selectedScenarioId: next.meta.id),
      );
    }
  }

  /// Tasdiqlanadigan stsenariyni tanlash (muhokama shu stsenariy uchun).
  Future<CeremonyPlan> select(CeremonyScenario s) async {
    final p = await _beforeEdit(s.planId);
    return _plans.update(p.copyWith(selectedScenarioId: s.meta.id));
  }

  Future<CeremonyBudgetLine> addLine(
    CeremonyScenario s, {
    required String title,
    required CeremonyLineKind kind,
    required Money amount,
    required FundingSource source,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    await _beforeEdit(s.planId);
    final existing = await _lines.forScenario(s.meta.id);
    return _lines.add(
      CeremonyBudgetLine(
        meta: _meta.create(s.meta.householdId),
        scenarioId: s.meta.id,
        title: title.trim(),
        kind: kind,
        amount: amount,
        source: source,
        sortOrder: existing.length,
      ),
    );
  }

  Future<CeremonyBudgetLine> updateLine(
    CeremonyBudgetLine l, {
    FundingSource? source,
    Money? amount,
  }) async {
    if (amount != null && !amount.isPositive) {
      throw const DomainRuleException(errNotPositive);
    }
    final s = await _scenario(l.scenarioId);
    await _beforeEdit(s.planId);
    final fresh = (await _lines.findById(l.meta.id))!;
    return _lines.update(
      fresh.copyWith(
        source: source ?? fresh.source,
        amount: amount ?? fresh.amount,
      ),
    );
  }

  Future<void> removeLine(CeremonyBudgetLine l) async {
    final s = await _scenario(l.scenarioId);
    await _beforeEdit(s.planId);
    await _lines.softDelete(l.meta.id);
  }

  /// Qarz qismini oyiga qancha to'lay olamiz (va stavka) — to'lash
  /// muddatini hisoblash uchun. Muhokamani bekor qilmaydi.
  Future<CeremonyPlan> setDebtTerms(
    CeremonyPlan plan, {
    required Money monthly,
    int annualRateBp = 0,
  }) async {
    if (!monthly.isPositive || annualRateBp < 0) {
      throw const DomainRuleException(errNotPositive);
    }
    final p = await _fresh(plan);
    return _plans.update(
      p.copyWith(
        debtMonthly: monthly,
        debtAnnualRateBp: annualRateBp == 0 ? null : annualRateBp,
      ),
    );
  }

  Future<List<Member>> _adults(String hh) async => [
    for (final m in await _members.listActive(hh))
      if (m.role == MemberRole.adult) m,
  ];

  /// «Buni qarzsiz qanday o'tkazamiz?» — katta a'zo o'z profilini tanlab
  /// belgi qo'yadi (shaxsiy PIN bo'lsa — PIN bilan). Hamma kattalar
  /// belgilagach reja `DISCUSSED` bo'ladi. Natija: PIN tekshiruvi va
  /// muhokama shu belgi bilan yakunlandimi.
  Future<(PinCheck, bool completed)> markDiscussed(
    CeremonyPlan plan,
    Member member,
    String pin,
  ) async {
    if (member.role != MemberRole.adult) {
      throw const DomainRuleException(errAdultOnly);
    }
    final p = await _fresh(plan);
    if (p.status == CeremonyStatus.confirmed) {
      throw const DomainRuleException(errConfirmedLocked);
    }
    final check = await _memberPins.verify(member, pin);
    if (check is! PinAccepted) return (check, false);
    final marks = await _marks.forPlan(p.meta.id);
    if (!marks.any((m) => m.memberId == member.meta.id)) {
      await _marks.add(
        CeremonyDiscussionMark(
          meta: _meta.create(p.meta.householdId),
          planId: p.meta.id,
          memberId: member.meta.id,
        ),
      );
    }
    final marked = {
      for (final m in await _marks.forPlan(p.meta.id)) m.memberId,
    };
    final adults = await _adults(p.meta.householdId);
    final done = adults.every((a) => marked.contains(a.meta.id));
    if (done && p.status == CeremonyStatus.draft) {
      await _plans.update(p.copyWith(status: CeremonyStatus.discussed));
      return (check, true);
    }
    return (check, false);
  }

  /// Tasdiqlash. Tanlangan stsenariyda qarz bo'lsa — faqat oilaviy
  /// muhokamadan keyin (SPEC 2D.8).
  Future<CeremonyPlan> confirm(CeremonyPlan plan) async {
    final v = await view(plan);
    if (v.isConfirmed) return v.plan;
    final s = v.selected;
    if (s == null || !s.total.isPositive) {
      throw const DomainRuleException(errNothingToConfirm);
    }
    if (v.needsDiscussion && v.plan.status != CeremonyStatus.discussed) {
      throw const DomainRuleException(errDiscussionRequired);
    }
    return _plans.update(
      v.plan.copyWith(
        status: CeremonyStatus.confirmed,
        selectedScenarioId: s.scenario.meta.id,
      ),
    );
  }

  /// Tasdiqni bekor qilish — qoralamaga, muhokama qaytadan.
  Future<CeremonyPlan> reopen(CeremonyPlan plan) async {
    final p = await _fresh(plan);
    for (final m in await _marks.forPlan(p.meta.id)) {
      await _marks.softDelete(m.meta.id);
    }
    return _plans.update(p.copyWith(status: CeremonyStatus.draft));
  }

  Future<void> remove(CeremonyPlan plan) => _plans.softDelete(plan.meta.id);

  // --- To'yona o'rniga jamg'arma ---

  /// Yosh oila uchun maqsad (`Goal`), rejaga bog'lanadi.
  Future<Goal> createGiftGoal(
    CeremonyPlan plan, {
    required String title,
    required Money target,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (!target.isPositive) throw const DomainRuleException(errNotPositive);
    final p = await _fresh(plan);
    final g = await _goals.add(
      Goal(
        meta: _meta.create(p.meta.householdId),
        title: title.trim(),
        target: target,
        targetDate: p.eventDate,
      ),
    );
    await _plans.update(p.copyWith(giftGoalId: g.meta.id));
    return g;
  }

  /// Mehmon hissasi (qo'lda; real o'tkazma keyinroq).
  Future<GoalContribution> addContribution(
    Goal goal, {
    required String name,
    required Money amount,
  }) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    return _contributions.add(
      GoalContribution(
        meta: _meta.create(goal.meta.householdId),
        goalId: goal.meta.id,
        contributorName: name.trim(),
        amount: amount,
        receivedOn: today,
      ),
    );
  }

  /// Qarzni oyiga standart to'lash summasi: kiritilgan bo'lsa — o'sha;
  /// aks holda daromadning «Qarzdan chiqish» ulushi (20 %).
  Future<Money?> _debtMonthly(CeremonyPlan p) async {
    if (p.debtMonthly != null) return p.debtMonthly;
    final h = await _households.current();
    final income = (await _debts.overview()).monthlyIncome;
    return income == null ? null : percentOf(income, h.recoverySplit.debtBp);
  }

  Future<CeremonyView> view(CeremonyPlan plan) async {
    final p = await _fresh(plan);
    final hh = p.meta.householdId;
    final goals = await _goals.listActive(hh);
    final monthly = await _debtMonthly(p);
    final start = p.eventDate ?? today;
    final gift = p.giftGoalId == null
        ? null
        : goals.where((g) => g.meta.id == p.giftGoalId).firstOrNull;
    return CeremonyView(
      plan: p,
      scenarios: [
        for (final s in await _scenarios.forPlan(p.meta.id))
          summarizeScenario(
            s,
            await _lines.forScenario(s.meta.id),
            currency: p.currency,
            debtStart: start,
            debtMonthly: monthly,
            debtAnnualRateBp: p.debtAnnualRateBp ?? 0,
            goals: [
              for (final g in goals)
                if (g.meta.id != p.giftGoalId) g,
            ],
          ),
      ],
      adults: await _adults(hh),
      markedBy: {
        for (final m in await _marks.forPlan(p.meta.id)) m.memberId,
      },
      goals: goals,
      giftGoal: gift,
      giftContributions: gift == null
          ? const []
          : await _contributions.forGoal(gift.meta.id),
    );
  }
}
