import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';

/// Majburiyat turi → standart kategoriya (to'lov shu kategoriyada yozilsa,
/// majburiyat «yozilgan» hisoblanadi — ikki marta sanalmaydi).
CategoryKey categoryForKind(ObligationKind kind) => switch (kind) {
  ObligationKind.rent => CategoryKey.rent,
  ObligationKind.credit => CategoryKey.credit,
  ObligationKind.utility => CategoryKey.utilities,
  ObligationKind.phone => CategoryKey.phone,
  ObligationKind.fuel => CategoryKey.fuel,
  ObligationKind.other => CategoryKey.other,
};

/// Doimiy to'lovlar (SPEC 2.5) va nasiya daftari (`Debt`, `SHOP`).
class ObligationService {
  ObligationService({
    required HouseholdRepository households,
    required ObligationRepository obligations,
    required DebtRepository debts,
    required CategoryRepository categories,
    required DebtInstallmentRepository installments,
    required DebtPaymentRepository payments,
    required SyncMetaFactory metaFactory,
    Clock clock = const SystemClock(),
  }) : _clock = clock,
       _households = households,
       _obligations = obligations,
       _debts = debts,
       _categories = categories,
       _installments = installments,
       _payments = payments,
       _meta = metaFactory;

  static const errInvalid = 'obligation_invalid';
  static const errPaymentTooBig = 'nasiya_payment_too_big';

  final HouseholdRepository _households;
  final ObligationRepository _obligations;
  final DebtRepository _debts;
  final CategoryRepository _categories;
  final DebtInstallmentRepository _installments;
  final DebtPaymentRepository _payments;
  final Clock _clock;
  final SyncMetaFactory _meta;

  Future<Household> _household() => _households.current();

  Future<List<Obligation>> obligations() async =>
      _obligations.listActive((await _household()).meta.id);

  Future<Obligation> addObligation({
    required String title,
    required ObligationKind kind,
    required Money amount,
    required int dayOfMonth,
  }) async {
    _validate(title, amount, dayOfMonth);
    final hh = (await _household()).meta.id;
    final category = await _categories.findBySystemKey(
      hh,
      categoryForKind(kind),
    );
    return _obligations.add(
      Obligation(
        meta: _meta.create(hh),
        title: title.trim(),
        kind: kind,
        amount: amount,
        dayOfMonth: dayOfMonth,
        categoryId: category?.meta.id,
      ),
    );
  }

  Future<Obligation> updateObligation(Obligation o) async {
    _validate(o.title, o.amount, o.dayOfMonth);
    final hh = o.meta.householdId;
    final category = await _categories.findBySystemKey(
      hh,
      categoryForKind(o.kind),
    );
    return _obligations.update(
      o.copyWith(title: o.title.trim(), categoryId: category?.meta.id),
    );
  }

  Future<void> deleteObligation(String id) => _obligations.softDelete(id);

  void _validate(String title, Money amount, int day) {
    if (title.trim().isEmpty || !amount.isPositive || day < 1 || day > 31) {
      throw const DomainRuleException(errInvalid);
    }
  }

  // --- Nasiya daftari ---

  Future<List<Debt>> nasiya() async => _debts.listByCreditorType(
    (await _household()).meta.id,
    CreditorType.shop,
  );

  /// Nasiya = do'kon qarzi (SPEC 2C.7). To'lash niyati (SPEC 2D.5): muddat
  /// majburiy — bitta qatorli to'lov rejasi yoziladi.
  Future<Debt> addNasiya({
    required String shopName,
    required Money amount,
    required LocalDate dueDate,
    String? note,
  }) async {
    if (shopName.trim().isEmpty || !amount.isPositive) {
      throw const DomainRuleException(errInvalid);
    }
    final hh = (await _household()).meta.id;
    final debt = await _debts.add(
      Debt(
        meta: _meta.create(hh),
        creditorType: CreditorType.shop,
        creditorName: shopName.trim(),
        principal: amount,
        remaining: amount,
        totalPaid: Money.zero(amount.currency),
        dueDate: dueDate,
        note: note,
        scheduleType: DebtScheduleType.manual,
      ),
    );
    await _installments.add(
      DebtInstallment(
        meta: _meta.create(hh),
        debtId: debt.meta.id,
        dueOn: dueDate,
        amount: amount,
        interest: Money.zero(amount.currency),
      ),
    );
    return debt;
  }

  /// Nasiyaga to'lov: qoldiq kamayadi, to'langan jami oshadi.
  Future<Debt> payNasiya(Debt debt, Money payment) async {
    if (!payment.isPositive) throw const DomainRuleException(errInvalid);
    if (payment > debt.remaining) {
      throw const DomainRuleException(errPaymentTooBig);
    }
    await _payments.add(
      DebtPayment(
        meta: _meta.create(debt.meta.householdId),
        debtId: debt.meta.id,
        amount: payment,
        paidOn: Tashkent.dateOf(_clock.nowUtc()),
      ),
    );
    return _debts.update(
      debt.copyWith(
        remaining: debt.remaining - payment,
        totalPaid: (debt.totalPaid ?? Money.zero(payment.currency)) + payment,
      ),
    );
  }

  Future<void> deleteNasiya(String id) => _debts.softDelete(id);
}
