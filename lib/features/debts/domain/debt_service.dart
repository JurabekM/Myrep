import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/builders.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:meta/meta.dart';

/// Bitta qarz: reja, to'lovlar, haqiqiy narx.
///
/// Rejadagi to'lovlar qatorlarni tartib bilan yopadi; qo'shimcha
/// (muddatidan oldin) to'lovlar qatorlarni qayta quradi (`applyPrepayment`) —
/// shuning uchun «qoplangan» qatorlar faqat rejadagi to'lovlar bilan
/// sanaladi.
@immutable
final class DebtView {
  const DebtView({
    required this.debt,
    required this.plan,
    required this.payments,
    this.contributors = const [],
  });

  final Debt debt;
  final List<DebtInstallment> plan;
  final List<DebtPayment> payments;
  final List<DebtContributor> contributors;

  CurrencyCode get currency => debt.principal.currency;

  /// Haqiqiy narx: to'langan (jarimalar bilan) + qolgan reja.
  DebtCost get cost =>
      DebtCost(principal: debt.principal, totalPaid: paid + remainingPlanned);

  bool get isInterestBearing => isInterestBearingDebt(debt);

  bool get isOpen => debt.remaining.isPositive;

  /// Hamma to'lovlar (jarimalar bilan).
  Money get paid => Money.sum(payments.map((p) => p.amount), currency);

  /// Rejadagi to'lovlar (qatorlarni tartib bilan yopadi).
  Money get regularPaid => Money.sum([
    for (final p in payments)
      if (!p.isPrepayment) p.amount,
  ], currency);

  /// Birinchi to'lanmagan qator indeksi va unga to'langan qism.
  (int, Money) get _coverage {
    var covered = regularPaid;
    for (final (k, i) in plan.indexed) {
      if (covered >= i.amount) {
        covered -= i.amount;
        continue;
      }
      return (k, covered);
    }
    return (plan.length, Money.zero(currency));
  }

  /// Qolgan reja qatorlari: birinchisi qisman to'langan bo'lsa — qolgani
  /// (foiz avval yopiladi).
  List<Installment> get remainingRows {
    final (k, part) = _coverage;
    return [
      for (final (j, i) in plan.indexed.skip(k))
        if (j == k && part.isPositive)
          Installment(
            dueOn: i.dueOn,
            amount: i.amount - part,
            interest: part >= i.interest
                ? Money.zero(currency)
                : i.interest - part,
          )
        else
          Installment(dueOn: i.dueOn, amount: i.amount, interest: i.interest),
    ];
  }

  /// To'liq yopilgan reja qatorlari soni (rejaning boshidan).
  int get paidRows => _coverage.$1;

  Money get remainingPlanned =>
      Money.sum(remainingRows.map((r) => r.amount), currency);

  /// Navbatdagi to'lanmagan reja qatori.
  DebtInstallment? get next {
    if (!isOpen) return null;
    final (k, _) = _coverage;
    return k < plan.length ? plan[k] : null;
  }

  /// Navbatdagi qatorni to'liq yopish uchun qolgan summa.
  Money? get nextDue {
    final rows = remainingRows;
    return !isOpen || rows.isEmpty ? null : rows.first.amount;
  }

  /// «Qarzsiz kun» — rejaning oxirgi to'lovi.
  LocalDate? get debtFreeOn {
    final rows = remainingRows;
    return !isOpen || rows.isEmpty ? null : rows.last.dueOn;
  }

  /// Qo'shimcha to'lov qoidasi (SPEC 2D.2).
  PayoffTerms get terms {
    final fee = debt.prepayFeeBp ?? 0;
    final rate = debt.annualRateBp ?? 0;
    if (rate > 0 && plan.isNotEmpty) {
      switch (debt.scheduleType) {
        case DebtScheduleType.annuity:
          return PayoffTerms.annuity(
            annualRateBp: rate,
            annuityPayment: debt.monthlyPayment ?? plan.first.amount,
            prepayFeeBp: fee,
          );
        case DebtScheduleType.differentiated:
          return PayoffTerms.differentiated(
            annualRateBp: rate,
            principalPart: plan.first.amount - plan.first.interest,
            prepayFeeBp: fee,
          );
        case DebtScheduleType.fixedMarkup || DebtScheduleType.manual || null:
          break;
      }
    }
    return PayoffTerms.flat(prepayFeeBp: fee);
  }

  PayoffDebt get payoff =>
      PayoffDebt(id: debt.meta.id, rows: remainingRows, terms: terms);

  /// Hozir to'liq yopish uchun kerak summa: navbatdagi qator + qolganini
  /// qo'shimcha to'lov bilan (jarimasi bilan).
  Money get payoffAmount {
    final rows = remainingRows;
    if (!isOpen || rows.isEmpty) return Money.zero(currency);
    final rest = rows.sublist(1);
    final t = terms;
    final net = Money.sum(
      rest.map((r) => t.kind == PayoffKind.balance ? r.principal : r.amount),
      currency,
    );
    return rows.first.amount + net + t.feeFor(net);
  }

  /// Qo'shimcha to'lov qayta quradigan qatorlar: [plan] dagi boshlanish
  /// indeksi va qolgan qatorlar (qisman to'langan birinchi qator — o'z
  /// holicha qoladi).
  (int, List<Installment>) get rebuildable {
    final (k, part) = _coverage;
    final rows = remainingRows;
    return part.isPositive && rows.isNotEmpty
        ? (k + 1, rows.sublist(1))
        : (k, rows);
  }

  /// Faqat qo'shimcha to'lov sifatida eng ko'pi (jarimasi bilan).
  Money get maxExtra {
    if (!isOpen) return Money.zero(currency);
    final t = terms;
    final net = Money.sum(
      rebuildable.$2.map(
        (r) => t.kind == PayoffKind.balance ? r.principal : r.amount,
      ),
      currency,
    );
    return net + t.feeFor(net);
  }

  /// Yelkadosh to'lagan jami.
  Money paidBy(String contributorId) => Money.sum([
    for (final p in payments)
      if (p.contributorId == contributorId) p.amount,
  ], currency);
}

/// To'lov natijasi: qarz yopildimi va rejim odatiyga qaytdimi
/// (nishonlash ekrani uchun).
@immutable
final class DebtPaymentResult {
  const DebtPaymentResult({
    required this.debt,
    required this.payments,
    required this.closed,
    this.freedMonthly,
    this.modeReturned = false,
  });

  final Debt debt;
  final List<DebtPayment> payments;
  final bool closed;

  /// Yopilgan qarzdan bo'shagan oylik to'lov.
  final Money? freedMonthly;
  final bool modeReturned;
}

bool isInterestBearingDebt(Debt d) => isInterestBearing(
  hasMarkup: d.hasMarkup,
  annualRateBp: d.annualRateBp,
  markup: d.markupAmount,
);

extension on Debt {
  CurrencyCode get currency => principal.currency;
}

/// Standart yopish tartibi (SPEC 2D.2): avval foizli qarzlar — eng yuqori
/// ustamalisidan (stavka yoki ortiqcha to'lov ulushi), keyin foizsizlar —
/// muddati yaqinidan. Qo'lda tartib ([Debt.payoffOrder]) bo'lsa — u.
List<DebtView> orderForPayoff(List<DebtView> views) {
  int weight(DebtView v) => v.debt.annualRateBp ?? v.cost.overpaymentBp;
  final manual = views.any((v) => v.debt.payoffOrder != null);
  return [...views]..sort((a, b) {
    if (manual) {
      final x = a.debt.payoffOrder ?? 1 << 30;
      final y = b.debt.payoffOrder ?? 1 << 30;
      if (x != y) return x.compareTo(y);
    }
    if (a.isInterestBearing != b.isInterestBearing) {
      return a.isInterestBearing ? -1 : 1;
    }
    if (a.isInterestBearing) {
      final w = weight(b).compareTo(weight(a));
      if (w != 0) return w;
    } else {
      final x = a.next?.dueOn;
      final y = b.next?.dueOn;
      if (x != null && y != null && x != y) return x.compareTo(y);
    }
    return a.debt.meta.createdAt.compareTo(b.debt.meta.createdAt);
  });
}

/// Qarzlar va bergan qarzlar holati (SPEC 2C.7).
@immutable
final class DebtOverview {
  const DebtOverview({
    required this.debts,
    required this.receivables,
    required this.goals,
    required this.totalDebt,
    required this.monthlyPayments,
    required this.totalReceivable,
    this.monthlyIncome,
  });

  /// Ochiq qarzlar (foizlilari birinchi).
  final List<DebtView> debts;
  final List<Receivable> receivables;
  final List<Goal> goals;
  final Money totalDebt;

  /// Ochiq qarzlarning navbatdagi oylik to'lovlari jami.
  final Money monthlyPayments;
  final Money totalReceivable;

  /// Oxirgi 3 to'liq oyning o'rtacha daromadi; noma'lum — `null`.
  final Money? monthlyIncome;

  /// Oylik qarz yuki (daromadga nisbatan, bp).
  int? get loadBp => monthlyIncome == null
      ? null
      : debtLoadBp(monthlyPayments, monthlyIncome!);
}

/// 4-qonun: qarz inventari, haqiqiy narx, «to'lash niyati» (SPEC 2C.7,
/// 2D.3, 2D.5, 2D.6).
class DebtService {
  DebtService({
    required HouseholdRepository households,
    required DebtRepository debts,
    required DebtInstallmentRepository installments,
    required DebtPaymentRepository payments,
    required ReceivableRepository receivables,
    required GoalRepository goals,
    required DebtContributorRepository contributors,
    required SellableItemRepository sellables,
    required IncomeRepository incomes,
    required SyncMetaFactory metaFactory,
    required Clock clock,
    AgreementLink? agreements,
  }) : _households = households,
       _agreements = agreements,
       _debts = debts,
       _installments = installments,
       _payments = payments,
       _receivables = receivables,
       _goals = goals,
       _contributors = contributors,
       _sellables = sellables,
       _incomes = incomes,
       _meta = metaFactory,
       _clock = clock;

  /// Tilxat (`Agreement(LOAN)`) jurnali — to'lovlar shu orqali (SPEC 2F.6).
  final AgreementLink? _agreements;

  static const errNameRequired = 'debt_name_required';
  static const errNotPositive = 'debt_amount_must_be_positive';

  /// SPEC 2D.5: to'lash niyati — rejasiz qarzni saqlab bo'lmaydi.
  static const errScheduleRequired = 'debt_schedule_required';
  static const errPlanMismatch = 'debt_plan_must_cover_principal';
  static const errPaymentTooBig = 'debt_payment_exceeds_remaining';
  static const errNothingToApply = 'debt_nothing_to_apply';

  final HouseholdRepository _households;
  final DebtRepository _debts;
  final DebtInstallmentRepository _installments;
  final DebtPaymentRepository _payments;
  final ReceivableRepository _receivables;
  final GoalRepository _goals;
  final DebtContributorRepository _contributors;
  final SellableItemRepository _sellables;
  final IncomeRepository _incomes;
  final SyncMetaFactory _meta;
  final Clock _clock;

  LocalDate get today => Tashkent.dateOf(_clock.nowUtc());

  /// Yangi qarz. Reja [scheduleType] bo'yicha quriladi (qo'lda — [manual]);
  /// bo'sh bo'lsa yoki asosiy summani qoplamasa — saqlanmaydi.
  Future<DebtView> add({
    required CreditorType creditorType,
    required String creditorName,
    required Money principal,
    required DebtScheduleType scheduleType,
    int termMonths = 0,
    int annualRateBp = 0,
    Money? markup,
    LocalDate? start,
    List<Installment> manual = const [],
    String? reason,
    String? earlyRepaymentTerms,
    BorrowCheck? check,
  }) async {
    if (creditorName.trim().isEmpty) {
      throw const DomainRuleException(errNameRequired);
    }
    if (!principal.isPositive) throw const DomainRuleException(errNotPositive);
    final from = start ?? today;
    if (scheduleType != DebtScheduleType.manual &&
        (termMonths <= 0 || annualRateBp < 0)) {
      throw const DomainRuleException(errScheduleRequired);
    }
    final schedule = buildSchedule(
      type: scheduleType,
      principal: principal,
      start: from,
      termMonths: termMonths,
      annualRateBp: annualRateBp,
      markup: markup,
      manual: manual,
    );
    if (schedule.isEmpty || schedule.any((i) => !i.amount.isPositive)) {
      throw const DomainRuleException(errScheduleRequired);
    }
    if (Money.sum(schedule.map((i) => i.principal), principal.currency) !=
        principal) {
      throw const DomainRuleException(errPlanMismatch);
    }
    final hh = (await _households.current()).meta.id;
    final debt = await _debts.add(
      Debt(
        meta: _meta.create(hh),
        creditorType: creditorType,
        creditorName: creditorName.trim(),
        principal: principal,
        remaining: Money.sum(schedule.map((i) => i.amount), principal.currency),
        monthlyPayment: schedule.first.amount,
        dueDate: schedule.last.dueOn,
        reason: reason?.trim().isEmpty ?? true ? null : reason!.trim(),
        hasMarkup: isInterestBearing(
          hasMarkup: false,
          annualRateBp: annualRateBp,
          markup: markup,
        ),
        totalPaid: Money.zero(principal.currency),
        markupAmount: markup,
        earlyRepaymentTerms: earlyRepaymentTerms,
        scheduleType: scheduleType,
        termMonths: termMonths == 0 ? null : termMonths,
        annualRateBp: annualRateBp == 0 ? null : annualRateBp,
        startDate: from,
        borrowCheckJson: check?.toJson(),
      ),
    );
    final plan = <DebtInstallment>[
      for (final i in schedule)
        await _installments.add(
          DebtInstallment(
            meta: _meta.create(hh),
            debtId: debt.meta.id,
            dueOn: i.dueOn,
            amount: i.amount,
            interest: i.interest,
          ),
        ),
    ];
    return DebtView(debt: debt, plan: plan, payments: const []);
  }

  /// To'lov (SPEC 2D.2). Avval navbatdagi reja qatori yopiladi, ortgani —
  /// qo'shimcha (muddatidan oldin) to'lov: jarimasi ushlanadi va qolgan reja
  /// qayta quriladi (foizli qarzda foiz qayta hisoblanadi, muddat
  /// qisqaradi). [extraOnly] — hammasi qo'shimcha to'lov (sotilgan buyum,
  /// qutqarilgan pul).
  ///
  /// Hamma qarz yopilsa, «Qarzdan chiqish» rejimi o'zi odatiyga qaytadi
  /// (SPEC 2D.1).
  Future<DebtPaymentResult> pay(
    Debt target,
    Money amount, {
    bool extraOnly = false,
    String? contributorId,
    String? note,
  }) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    // Ekrandagi nusxa eskirgan bo'lishi mumkin — bazadagi joriy versiya.
    final debt = await _debts.findById(target.meta.id) ?? target;
    final v = await view(debt);
    if (amount > (extraOnly ? v.maxExtra : v.payoffAmount)) {
      throw const DomainRuleException(errPaymentTooBig);
    }
    final c = amount.currency;
    final hh = debt.meta.householdId;
    final added = <DebtPayment>[];
    final due = extraOnly ? Money.zero(c) : (v.nextDue ?? Money.zero(c));
    final regular = amount > due ? due : amount;
    if (regular.isPositive) {
      added.add(
        await _payments.add(
          DebtPayment(
            meta: _meta.create(hh),
            debtId: debt.meta.id,
            amount: regular,
            paidOn: today,
            note: note,
            contributorId: contributorId,
          ),
        ),
      );
    }
    final extra = amount - regular;
    if (extra.isPositive) {
      final fresh = await view(debt);
      final terms = fresh.terms;
      final (from, rows) = fresh.rebuildable;
      var net = terms.netWithin(extra);
      final cap = Money.sum(
        rows.map(
          (r) => terms.kind == PayoffKind.balance ? r.principal : r.amount,
        ),
        c,
      );
      if (net > cap) net = cap;
      final fee = terms.feeFor(net);
      added.add(
        await _payments.add(
          DebtPayment(
            meta: _meta.create(hh),
            debtId: debt.meta.id,
            amount: net + fee,
            paidOn: today,
            isPrepayment: true,
            fee: fee.isPositive ? fee : null,
            note: note,
            contributorId: contributorId,
          ),
        ),
      );
      for (final old in fresh.plan.skip(from)) {
        await _installments.softDelete(old.meta.id);
      }
      for (final r in applyPrepayment(rows, net, terms)) {
        await _installments.add(
          DebtInstallment(
            meta: _meta.create(hh),
            debtId: debt.meta.id,
            dueOn: r.dueOn,
            amount: r.amount,
            interest: r.interest,
          ),
        );
      }
    }
    for (final p in added) {
      await _agreements?.record(
        AgreementSource.debt,
        debt.meta.id,
        JournalDraft(
          kind: JournalKind.loanPayment,
          date: p.paidOn,
          partyId: borrowerPartyId,
          amount: p.amount,
          note: p.note,
          refId: p.meta.id,
        ),
      );
    }
    final after = await view(debt);
    final paidNow = Money.sum(added.map((p) => p.amount), c);
    final updated = await _debts.update(
      debt.copyWith(
        remaining: after.remainingPlanned,
        totalPaid: (debt.totalPaid ?? Money.zero(c)) + paidNow,
        dueDate: after.plan.isEmpty ? debt.dueDate : after.plan.last.dueOn,
      ),
    );
    final closed = !updated.remaining.isPositive;
    return DebtPaymentResult(
      debt: updated,
      payments: added,
      closed: closed,
      freedMonthly: closed ? debt.monthlyPayment : null,
      modeReturned: closed && await _returnToStandardIfDebtFree(),
    );
  }

  /// SPEC 2D.1: barcha qarzlar yopilganda rejim odatiyga qaytadi va
  /// bo'shagan 20 % taklif qilinadi.
  Future<bool> _returnToStandardIfDebtFree() async {
    final h = await _households.current();
    if (h.budgetMode != BudgetMode.debtRecovery) return false;
    for (final d in await _debts.listActive(h.meta.id)) {
      if (d.remaining.isPositive) return false;
    }
    await _households.update(
      h.copyWith(budgetMode: BudgetMode.standard, freedShareOfferPending: true),
    );
    return true;
  }

  Future<DebtView> view(Debt d) async => DebtView(
    debt: d,
    plan: await _installments.forDebt(d.meta.id),
    payments: await _payments.forDebt(d.meta.id),
    contributors: await _contributors.forDebt(d.meta.id),
  );

  /// Qo'lda yopish tartibi: [ids] ketma-ketligi saqlanadi; bo'sh — standart.
  Future<void> setPayoffOrder(List<String> ids) async {
    final h = await _households.current();
    for (final d in await _debts.listActive(h.meta.id)) {
      final i = ids.indexOf(d.meta.id);
      final order = i < 0 ? null : i;
      if (d.payoffOrder != order) {
        await _debts.update(d.copyWith(payoffOrder: order));
      }
    }
  }

  /// Muddatidan oldin to'lash jarimasi (bp; 0 — yo'q).
  Future<Debt> setPrepayFee(Debt d, int bp) {
    if (bp < 0 || bp > basisPointsWhole) {
      throw const DomainRuleException(errNotPositive);
    }
    return _debts.update(d.copyWith(prepayFeeBp: bp == 0 ? null : bp));
  }

  // --- Oilaviy yelkadoshlik (SPEC 2D.4) ---

  Future<DebtContributor> addContributor(
    Debt d, {
    required String name,
    String? memberId,
    Money? monthlyShare,
  }) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    return _contributors.add(
      DebtContributor(
        meta: _meta.create(d.meta.householdId),
        debtId: d.meta.id,
        name: name.trim(),
        memberId: memberId,
        monthlyShare: monthlyShare != null && monthlyShare.isPositive
            ? monthlyShare
            : null,
      ),
    );
  }

  Future<void> removeContributor(DebtContributor c) =>
      _contributors.softDelete(c.meta.id);

  // --- Sotiladigan buyumlar (SPEC 2D.7) ---

  Future<List<SellableItem>> sellables() async =>
      _sellables.listActive((await _households.current()).meta.id);

  Future<SellableItem> addSellable(String name, Money estimated) async {
    if (name.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (estimated.isNegative) throw const DomainRuleException(errNotPositive);
    final hh = (await _households.current()).meta.id;
    return _sellables.add(
      SellableItem(
        meta: _meta.create(hh),
        name: name.trim(),
        estimated: estimated,
      ),
    );
  }

  Future<SellableItem> markSold(SellableItem item, Money price) {
    if (!price.isPositive) throw const DomainRuleException(errNotPositive);
    return _sellables.update(
      item.copyWith(status: SellableStatus.sold, soldFor: price, soldOn: today),
    );
  }

  Future<void> removeSellable(SellableItem item) =>
      _sellables.softDelete(item.meta.id);

  /// Sotilgan buyum pulini bir bosishda qarzga qo'shimcha to'lov qilish.
  /// Qarz qolganidan kam bo'lsa — qarzning qolgani to'lanadi.
  Future<DebtPaymentResult> applySale(SellableItem item, Debt debt) async {
    if (!item.awaitsApplying) {
      throw const DomainRuleException(errNothingToApply);
    }
    final max = (await view(
      await _debts.findById(debt.meta.id) ?? debt,
    )).maxExtra;
    final amount = item.soldFor! > max ? max : item.soldFor!;
    if (!amount.isPositive) throw const DomainRuleException(errNothingToApply);
    final r = await pay(debt, amount, extraOnly: true, note: item.name);
    await _sellables.update(
      item.copyWith(debtId: debt.meta.id, paymentId: r.payments.last.meta.id),
    );
    return r;
  }

  Future<Money?> _monthlyIncome(Household h) async {
    var month = h.calendar.monthOf(today);
    final totals = <Money>[];
    for (var i = 0; i < 3; i++) {
      month = h.calendar.monthOf(month.start.plusDays(-1));
      totals.add(
        Money.sum([
          for (final x in await _incomes.listInRange(h.meta.id, month))
            if (x.amount.currency == h.baseCurrency) x.amount,
        ], h.baseCurrency),
      );
    }
    final withData = [
      for (final t in totals)
        if (t.isPositive) t,
    ];
    if (withData.isEmpty) return null;
    return Money(
      MoneyRounding.divide(
        Money.sum(withData, h.baseCurrency).minorUnits,
        withData.length,
      ),
      h.baseCurrency,
    );
  }

  Future<DebtOverview> overview() async {
    final h = await _households.current();
    final c = h.baseCurrency;
    final views = orderForPayoff([
      for (final d in await _debts.listActive(h.meta.id))
        if (d.remaining.isPositive && d.currency == c) await view(d),
    ]);
    final receivables = [
      for (final r in await _receivables.listActive(h.meta.id))
        if (r.isOpen && r.remaining.currency == c) r,
    ];
    return DebtOverview(
      debts: views,
      receivables: receivables,
      goals: await _goals.listActive(h.meta.id),
      totalDebt: Money.sum(views.map((v) => v.debt.remaining), c),
      monthlyPayments: Money.sum([
        for (final v in views) ?v.next?.amount,
      ], c),
      totalReceivable: Money.sum(receivables.map((r) => r.remaining), c),
      monthlyIncome: await _monthlyIncome(h),
    );
  }

  // --- Bergan qarzlar (Receivable): foiz maydoni YO'Q ---

  Future<Receivable> lend({
    required String debtorName,
    required Money amount,
    required LocalDate dueDate,
    String? reason,
  }) async {
    if (debtorName.trim().isEmpty) {
      throw const DomainRuleException(errNameRequired);
    }
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final hh = (await _households.current()).meta.id;
    return _receivables.add(
      Receivable(
        meta: _meta.create(hh),
        debtorName: debtorName.trim(),
        principal: amount,
        remaining: amount,
        dueDate: dueDate,
        reason: reason,
      ),
    );
  }

  Future<Receivable> receive(Receivable r, Money amount) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    if (amount > r.remaining) {
      throw const DomainRuleException(errPaymentTooBig);
    }
    final updated = await _receivables.update(
      r.copyWith(remaining: r.remaining - amount),
    );
    await _agreements?.record(
      AgreementSource.receivable,
      r.meta.id,
      JournalDraft(
        kind: JournalKind.loanPayment,
        date: today,
        partyId: borrowerPartyId,
        amount: amount,
      ),
    );
    return updated;
  }

  /// Muddati [days] kun ichida keladigan yoki o'tgan bergan qarzlar —
  /// xushmuomala eslatma uchun.
  Future<List<Receivable>> dueReceivables({int days = 3}) async {
    final limit = today.plusDays(days);
    return [
      for (final r in (await overview()).receivables)
        if (!r.dueDate.isAfter(limit)) r,
    ];
  }

  // --- Maqsadlar (imkoniyat narxi) ---

  Future<Goal> addGoal(String title, Money target) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errNameRequired);
    if (!target.isPositive) throw const DomainRuleException(errNotPositive);
    final hh = (await _households.current()).meta.id;
    return _goals.add(
      Goal(meta: _meta.create(hh), title: title.trim(), target: target),
    );
  }
}

/// Tayyorgarlik darvozasidagi qarz sharti (SPEC 2C.4), haqiqiy ma'lumot:
/// ochiq foizli (ribo / ustamali) qarz yo'q **yoki** qarzdan chiqish rejasi
/// bor (`DEBT_RECOVERY` rejimi yoqilgan).
class DebtDataReadiness implements DebtReadiness {
  DebtDataReadiness(this._debts, this._households);

  final DebtRepository _debts;
  final HouseholdRepository _households;

  @override
  Future<bool> isReady() async {
    final h = await _households.current();
    if (h.budgetMode == BudgetMode.debtRecovery) return true;
    for (final d in await _debts.listActive(h.meta.id)) {
      if (d.remaining.isPositive && isInterestBearingDebt(d)) return false;
    }
    return true;
  }
}
