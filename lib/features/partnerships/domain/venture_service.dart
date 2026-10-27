import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/partnerships/domain/distribution.dart';
import 'package:baraka_daftari/features/partnerships/domain/idea_math.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_service.dart';
import 'package:baraka_daftari/features/partnerships/domain/profit_spike.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture.dart';
import 'package:meta/meta.dart';

/// Yopilgan davr va uning taqsimoti.
@immutable
final class ClosedPeriod {
  const ClosedPeriod(this.period, this.shares);

  final VenturePeriod period;
  final List<DistributionShare> shares;
}

/// «Katta foyda» tekshiruvi (SPEC 2F.7): davr foydasi ogohlantirishga
/// loyiqmi va ikkala tomon 4–5-bandni qayta o'qiganini belgilaganmi.
@immutable
final class ProfitSpikeCheck {
  const ProfitSpikeCheck({
    required this.alert,
    required this.actual,
    required this.key,
    required this.parties,
    required this.acked,
  });

  final bool alert;

  /// Davr foydasi (sof).
  final Money actual;

  /// Tasdiq kaliti (davr tugashi va foyda).
  final String key;

  /// Kelishuv tomonlari. Bo'sh — kelishuv bog'lanmagan, gate qo'llanmaydi.
  final List<AgreementParty> parties;
  final Set<String> acked;

  bool get allAcked => parties.every((p) => acked.contains(p.id));

  /// Taqsimot shu tasdiqsiz o'tmaydi.
  bool get blocks => alert && parties.isNotEmpty && !allAcked;
}

/// Sheriklik kassa daftari holati.
@immutable
final class LedgerView {
  const LedgerView({
    required this.partnership,
    required this.entries,
    required this.closed,
    required this.openStart,
    required this.today,
  });

  final PartnershipView partnership;

  /// Hamma yozuvlar (yangisi birinchi).
  final List<VentureEntry> entries;
  final List<ClosedPeriod> closed;

  /// Ochiq davr boshi.
  final LocalDate openStart;
  final LocalDate today;

  CurrencyCode get currency => partnership.currency;

  LocalDate? get lastClosedEnd =>
      closed.isEmpty ? null : closed.last.period.endDate;

  /// Yopilgan davrga tegishli yozuv o'zgarmaydi.
  bool isLocked(VentureEntry e) {
    final end = lastClosedEnd;
    return end != null && !e.occurredOn.isAfter(end);
  }

  List<VentureEntry> get openEntries => [
    for (final e in entries)
      if (!isLocked(e)) e,
  ];

  Money get openIncome => Money.sum([
    for (final e in openEntries)
      if (e.effect.isPositive) e.effect,
  ], currency);

  Money get openExpense => Money.sum([
    for (final e in openEntries)
      if (e.effect.isNegative) -e.effect,
  ], currency);

  Money get openNet => openIncome - openExpense;

  /// Mudarabada sof kapital egasi daftarni faqat ko'radi (SPEC 2E.3) —
  /// yozuvlarni mehnat egasi yuritadi.
  bool get readOnly =>
      partnership.partnership.type == PartnershipType.mudaraba &&
      partnership.me?.role == PartnerRole.capitalProvider;
}

/// Sheriklik kassa daftari va davr taqsimoti (SPEC 2E.3). Biznes puli uy
/// pulidan alohida: xonadon byudjetiga faqat mening taqsimlangan ulushim
/// `Income` (`TAVAKKAL`) sifatida tushadi.
class VentureLedgerService {
  VentureLedgerService({
    required PartnershipService partnerships,
    required PartnershipRepository partnershipRepo,
    required VentureEntryRepository entries,
    required VenturePeriodRepository periods,
    required DistributionShareRepository shares,
    required BuyoutPaymentRepository buyouts,
    required IncomeRepository incomes,
    required SyncMetaFactory metaFactory,
    required Clock clock,
    AgreementLink? agreements,
  }) : _agreements = agreements,
       _partnerships = partnerships,
       _partnershipRepo = partnershipRepo,
       _entries = entries,
       _periods = periods,
       _shares = shares,
       _buyouts = buyouts,
       _incomes = incomes,
       _meta = metaFactory,
       _clock = clock;

  /// Kassa daftari yozuvlari kelishuv jurnaliga ham yoziladi (SPEC 2F.6).
  final AgreementLink? _agreements;

  Future<void> _journal(Partnership p, JournalDraft d) async =>
      _agreements?.record(AgreementSource.partnership, p.meta.id, d);

  static const errNotActive = 'ledger_partnership_not_active';
  static const errReadOnly = 'ledger_read_only';
  static const errPeriodClosed = 'ledger_period_closed';
  static const errNotPositive = 'ledger_amount_invalid';
  static const errNameRequired = 'ledger_title_required';
  static const errNothingToClose = 'ledger_nothing_to_close';
  static const errFuture = 'ledger_date_in_future';

  final PartnershipService _partnerships;
  final PartnershipRepository _partnershipRepo;
  final VentureEntryRepository _entries;
  final VenturePeriodRepository _periods;
  final DistributionShareRepository _shares;
  final BuyoutPaymentRepository _buyouts;
  final IncomeRepository _incomes;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  Future<LedgerView> view(Partnership p) async {
    final pv = await _partnerships.view(p);
    final periods = await _periods.forPartnership(p.meta.id);
    final entries = await _entries.forPartnership(p.meta.id);
    final last = periods.isEmpty ? null : periods.last.endDate;
    final first = entries.isEmpty ? null : entries.last.occurredOn;
    return LedgerView(
      partnership: pv,
      entries: entries,
      closed: [
        for (final x in periods)
          ClosedPeriod(x, await _shares.forPeriod(x.meta.id)),
      ],
      openStart:
          last?.plusDays(1) ?? pv.partnership.startDate ?? first ?? today,
      today: today,
    );
  }

  Future<VentureEntry> addEntry(
    Partnership p, {
    required VentureEntryKind kind,
    required String title,
    required Money amount,
    LocalDate? date,
    String? note,
    List<int>? receiptImage,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    final ok = kind == VentureEntryKind.correction
        ? !amount.isZero
        : amount.isPositive;
    if (!ok) throw const DomainRuleException(errNotPositive);
    final v = await view(p);
    if (v.partnership.partnership.status != PartnershipStatus.active) {
      throw const DomainRuleException(errNotActive);
    }
    if (v.readOnly) throw const DomainRuleException(errReadOnly);
    final on = date ?? today;
    if (on.isAfter(today)) throw const DomainRuleException(errFuture);
    final end = v.lastClosedEnd;
    if (end != null && !on.isAfter(end)) {
      // Yopilgan davr o'zgarmaydi — tuzatish ochiq davrda yangi yozuv bilan.
      throw const DomainRuleException(errPeriodClosed);
    }
    final jk = _journalKind(kind);
    await _agreements?.ensureWritable(
      AgreementSource.partnership,
      p.meta.id,
      jk,
      on,
    );
    final entry = await _entries.add(
      VentureEntry(
        meta: _meta.create(p.meta.householdId),
        partnershipId: p.meta.id,
        kind: kind,
        title: title.trim(),
        amount: amount,
        occurredOn: on,
        note: note?.trim().isEmpty ?? true ? null : note!.trim(),
        receiptImage: receiptImage,
      ),
    );
    await _journal(
      p,
      JournalDraft(
        kind: jk,
        date: on,
        amount: amount,
        note: entry.title,
        refId: entry.meta.id,
      ),
    );
    return entry;
  }

  static JournalKind _journalKind(VentureEntryKind kind) => switch (kind) {
    VentureEntryKind.income => JournalKind.ventureIncome,
    VentureEntryKind.expense => JournalKind.ventureExpense,
    VentureEntryKind.forceMajeure => JournalKind.forceMajeure,
    VentureEntryKind.correction => JournalKind.correction,
  };

  /// «Katta foyda» holati (davr [endDate] gacha). Kelishuv bog'lanmagan
  /// bo'lsa — tomonlar bo'sh va gate qo'llanmaydi.
  Future<ProfitSpikeCheck> spikeCheck(
    Partnership p, {
    LocalDate? endDate,
  }) async {
    final v = await view(p);
    final end = endDate ?? today;
    final net = _netOf(_inPeriod(v, end), v.currency);
    final linked = await _agreements?.viewBySource(
      AgreementSource.partnership,
      p.meta.id,
    );
    return _spike(v, net, end, linked);
  }

  ProfitSpikeCheck _spike(
    LedgerView v,
    Money net,
    LocalDate end,
    AgreementView? linked,
  ) {
    final closed = v.closed;
    final last3 = closed.length < ProfitSpike.window
        ? null
        : [
            for (final c in closed.skip(closed.length - ProfitSpike.window))
              c.period.net,
          ];
    final key = profitSpikeKey(end, net.minorUnits);
    return ProfitSpikeCheck(
      alert: ProfitSpike.evaluate(actual: net, last3: last3),
      actual: net,
      key: key,
      parties: linked?.answers.parties ?? const [],
      acked: linked == null ? const {} : profitSpikeAcks(linked.journal, key),
    );
  }

  static List<VentureEntry> _inPeriod(LedgerView v, LocalDate end) => [
    for (final e in v.openEntries)
      if (!e.occurredOn.isAfter(end)) e,
  ];

  static Money _netOf(List<VentureEntry> entries, CurrencyCode c) => Money.sum([
    for (final e in entries) e.effect,
  ], c);

  /// Faqat ochiq davr yozuvini o'chirish mumkin.
  Future<void> removeEntry(Partnership p, VentureEntry e) async {
    final v = await view(p);
    if (v.isLocked(e)) throw const DomainRuleException(errPeriodClosed);
    if (v.readOnly) throw const DomainRuleException(errReadOnly);
    await _entries.softDelete(e.meta.id);
    // Jurnaldan o'chirilmaydi — teskari tuzatuvchi yozuv.
    await _journal(
      p,
      JournalDraft(
        kind: JournalKind.correction,
        date: today,
        amount: -e.effect,
        note: e.title,
        refId: e.meta.id,
      ),
    );
  }

  /// Davrni yopish: sof foyda yoki zarar Vazifa 13 qoidalari bilan
  /// taqsimlanadi, buyout ulushdan avtomatik ayiriladi, mening musbat
  /// ulushim uy byudjetiga daromad bo'lib tushadi. Yopilgan davr
  /// o'zgarmaydi.
  Future<ClosedPeriod> closePeriod(
    Partnership p, {
    LocalDate? endDate,
    bool negligence = false,
    String? negligenceNote,
  }) async {
    final v = await view(p);
    final pv = v.partnership;
    if (pv.partnership.status != PartnershipStatus.active) {
      throw const DomainRuleException(errNotActive);
    }
    if (v.readOnly) throw const DomainRuleException(errReadOnly);
    final end = endDate ?? today;
    final inPeriod = _inPeriod(v, end);
    if (inPeriod.isEmpty) throw const DomainRuleException(errNothingToClose);
    final c = v.currency;
    final income = Money.sum([
      for (final e in inPeriod)
        if (e.effect.isPositive) e.effect,
    ], c);
    final expense = Money.sum([
      for (final e in inPeriod)
        if (e.effect.isNegative) -e.effect,
    ], c);
    final net = income - expense;
    // Nizo ochiq bo'lsa taqsimot to'xtaydi (SPEC 2F.8). Ochiq ko'rik
    // tugamaguncha davr yopilmaydi (SPEC 2F.5). «Katta foyda» tasdig'i (2F.7)
    // — taqsimotdan oldin. Yakunlangan ko'rikdan keyin davrni yopish odatiy
    // oqim.
    final linked = await _agreements?.viewBySource(
      AgreementSource.partnership,
      p.meta.id,
    );
    if (linked?.agreement.status == AgreementStatus.inDispute) {
      throw const DomainRuleException(AccountabilityErrors.inDispute);
    }
    if (linked != null &&
        reviewStateOf(
          linked.journal,
          start: linked.agreement.effectiveFrom,
          everyDays: linked.answers.custody.reviewEveryDays,
        ).isOpen) {
      throw const DomainRuleException(AccountabilityErrors.reviewOpen);
    }
    if (_spike(v, net, end, linked).blocks) {
      throw const DomainRuleException(AccountabilityErrors.spikeAckRequired);
    }
    final months = switch (pv.partnership.reportPeriod) {
      ReportPeriod.monthly => 1,
      ReportPeriod.quarterly => 3,
      ReportPeriod.yearly => 12,
    };
    final monthly = pv.partnership.buyoutMonthly;
    final result = distribute(
      type: pv.partnership.type,
      parties: [
        for (final x in pv.partners)
          DistributionParty(
            role: x.role,
            shareBp: x.profitShareBp,
            capital: pv.capitalOf(x),
          ),
      ],
      net: net,
      buyoutDue: monthly?.times(months),
      buyoutRemaining: pv.buyoutRemaining,
      negligence: negligence,
      note: negligenceNote,
    );
    final hh = p.meta.householdId;
    var period = await _periods.add(
      VenturePeriod(
        meta: _meta.create(hh),
        partnershipId: p.meta.id,
        startDate: v.openStart.isAfter(end) ? end : v.openStart,
        endDate: end,
        income: income,
        expense: expense,
        net: net,
        buyout: result.buyoutPaid,
        negligence: negligence,
        negligenceNote: negligence ? negligenceNote?.trim() : null,
      ),
    );
    final shares = <DistributionShare>[
      for (final (i, x) in pv.partners.indexed)
        await _shares.add(
          DistributionShare(
            meta: _meta.create(hh),
            periodId: period.meta.id,
            partnerId: x.meta.id,
            amount: result.shares[i],
            buyout: result.buyout[i],
          ),
        ),
    ];
    for (final sh in shares) {
      if (sh.amount.isZero) continue;
      await _journal(
        p,
        JournalDraft(
          kind: sh.amount.isNegative
              ? JournalKind.lossDistribution
              : JournalKind.profitDistribution,
          date: end,
          partyId: sh.partnerId,
          amount: sh.amount,
          refId: sh.meta.id,
        ),
      );
    }
    if (result.buyoutPaid.isPositive) {
      await _journal(
        p,
        JournalDraft(
          kind: JournalKind.buyout,
          date: end,
          amount: result.buyoutPaid,
          refId: period.meta.id,
        ),
      );
      await _buyouts.add(
        BuyoutPayment(
          meta: _meta.create(hh),
          partnershipId: p.meta.id,
          amount: result.buyoutPaid,
          paidOn: end,
        ),
      );
    }
    final me = pv.me;
    if (me != null) {
      final mine = result.shares[pv.partners.indexOf(me)];
      if (mine.isPositive) {
        final inc = await _incomes.add(
          Income(
            meta: _meta.create(hh),
            amount: mine,
            source: IncomeSource.other,
            channel: PaymentChannel.cash,
            receivedAt: _clock.nowUtc(),
            sourceType: IncomeSourceType.tavakkal,
            note: pv.partnership.title,
          ),
        );
        period = await _periods.update(period.copyWith(incomeId: inc.meta.id));
      }
    }
    return ClosedPeriod(period, shares);
  }

  Future<Partnership?> find(String id) => _partnershipRepo.findById(id);
}

/// «Hunardan ishga» (SPEC 2E.4): hunarlar va g'oyalar.
@immutable
final class IdeaView {
  const IdeaView(this.idea, this.capex);

  final VentureIdea idea;
  final List<IdeaCapexItem> capex;

  Money get capexTotal =>
      Money.sum(capex.map((x) => x.amount), idea.baseIncome.currency);

  List<IdeaScenarioResult> get scenarios => [
    for (final (s, income) in [
      (IdeaScenario.pessimistic, idea.pessimisticIncome),
      (IdeaScenario.base, idea.baseIncome),
      (IdeaScenario.optimistic, idea.optimisticIncome),
    ])
      evaluateScenario(
        scenario: s,
        capex: capexTotal,
        income: income,
        expense: idea.monthlyExpense,
        myShareBp: idea.myShareBp,
      ),
  ];
}

class IdeaService {
  IdeaService({
    required HouseholdRepository households,
    required SkillRepository skills,
    required VentureIdeaRepository ideas,
    required IdeaCapexItemRepository capex,
    required SyncMetaFactory metaFactory,
  }) : _households = households,
       _skills = skills,
       _ideas = ideas,
       _capex = capex,
       _meta = metaFactory;

  static const errNameRequired = 'idea_title_required';
  static const errNotPositive = 'idea_amount_invalid';

  final HouseholdRepository _households;
  final SkillRepository _skills;
  final VentureIdeaRepository _ideas;
  final IdeaCapexItemRepository _capex;
  final SyncMetaFactory _meta;

  Future<String> _hh() async => (await _households.current()).meta.id;

  Future<List<Skill>> skills() async => _skills.listActive(await _hh());

  Future<Skill> addSkill(String name, {String? memberId}) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    return _skills.add(
      Skill(
        meta: _meta.create(await _hh()),
        name: name.trim(),
        memberId: memberId,
      ),
    );
  }

  Future<void> removeSkill(Skill s) => _skills.softDelete(s.meta.id);

  Future<List<IdeaView>> ideas() async => [
    for (final i in await _ideas.listActive(await _hh()))
      IdeaView(i, await _capex.forIdea(i.meta.id)),
  ];

  /// Yangi g'oya. Pessimistik / optimistik kirim berilmasa — o'rtachaning
  /// 70 % / 130 % i.
  Future<IdeaView> addIdea({
    required String title,
    required Money baseIncome,
    required Money monthlyExpense,
    List<(String, Money)> capex = const [],
    Money? pessimisticIncome,
    Money? optimisticIncome,
    int myShareBp = basisPointsWhole,
    String? skillId,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (baseIncome.isNegative ||
        monthlyExpense.isNegative ||
        myShareBp <= 0 ||
        myShareBp > basisPointsWhole ||
        capex.any((x) => !x.$2.isPositive)) {
      throw const DomainRuleException(errNotPositive);
    }
    final (pess, opt) = defaultScenarioIncomes(baseIncome);
    final hh = await _hh();
    final idea = await _ideas.add(
      VentureIdea(
        meta: _meta.create(hh),
        title: title.trim(),
        pessimisticIncome: pessimisticIncome ?? pess,
        baseIncome: baseIncome,
        optimisticIncome: optimisticIncome ?? opt,
        monthlyExpense: monthlyExpense,
        myShareBp: myShareBp,
        skillId: skillId,
      ),
    );
    final items = [
      for (final (t, a) in capex)
        await _capex.add(
          IdeaCapexItem(
            meta: _meta.create(hh),
            ideaId: idea.meta.id,
            title: t.trim(),
            amount: a,
          ),
        ),
    ];
    return IdeaView(idea, items);
  }

  Future<void> removeIdea(VentureIdea i) => _ideas.softDelete(i.meta.id);
}

/// «Kafolatlangan foyda» detektori tarixi (SPEC 2E.5).
class OfferCheckService {
  OfferCheckService({
    required HouseholdRepository households,
    required OfferCheckRepository checks,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _checks = checks,
       _meta = metaFactory,
       _clock = clock;

  /// «Pul qo'yaman» uchun maslahatlashilgan odam ismi shart (SPEC 2G.6).
  static const errAdvisorRequired = 'offer_advisor_required';

  /// «Pul qo'yaman» tekshiruvdan 24 soat o'tmaguncha ochilmaydi.
  static const errCoolingOff = 'offer_cooling_off';

  /// Rad etilgan yoki qabul qilingan qaror o'zgarmaydi.
  static const errDecided = 'offer_already_decided';
  static const errBadRate = 'offer_rate_invalid';

  final HouseholdRepository _households;
  final OfferCheckRepository _checks;
  final SyncMetaFactory _meta;
  final Clock _clock;

  Future<List<OfferCheckRecord>> history() async =>
      _checks.listActive((await _households.current()).meta.id);

  Future<(OfferCheckRecord, OfferEvaluation)> save(
    String title,
    Map<OfferQuestion, OfferAnswer> answers, {
    Money? amount,
    int? promisedMonthlyBp,
  }) async {
    if (promisedMonthlyBp != null && promisedMonthlyBp < 0) {
      throw const DomainRuleException(errBadRate);
    }
    final e = evaluateOffer(answers);
    final r = await _checks.add(
      OfferCheckRecord(
        meta: _meta.create((await _households.current()).meta.id),
        title: title.trim(),
        answersJson: offerAnswersToJson(answers),
        verdict: e.verdict,
        amount: amount != null && amount.isPositive ? amount : null,
        promisedMonthlyBp: promisedMonthlyBp,
      ),
    );
    return (r, e);
  }

  /// Qaror (SPEC 2G.6): «rad etdim» va «keyinga qoldiraman» darhol;
  /// «pul qo'yaman» — maslahatchi ismi yozilgach va 24 soatdan keyin.
  /// «Keyinga qoldiraman» dan keyin boshqa qaror qilish mumkin.
  Future<OfferCheckRecord> decide(
    OfferCheckRecord check,
    OfferDecision decision, {
    String? advisor,
  }) async {
    final fresh = await _checks.findById(check.meta.id) ?? check;
    if (fresh.decision == OfferDecision.declined ||
        fresh.decision == OfferDecision.accepted) {
      throw const DomainRuleException(errDecided);
    }
    final now = _clock.nowUtc();
    final name = (advisor ?? fresh.advisor ?? '').trim();
    if (decision == OfferDecision.accepted) {
      if (name.isEmpty) throw const DomainRuleException(errAdvisorRequired);
      if (now.isBefore(acceptOpensAt(fresh.meta.createdAt))) {
        throw const DomainRuleException(errCoolingOff);
      }
    }
    return _checks.update(
      fresh.copyWith(
        decision: decision,
        decidedAt: now,
        advisor: name.isEmpty ? null : name,
      ),
    );
  }
}
