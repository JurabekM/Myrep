import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:meta/meta.dart';

/// Majburiyatning shu oydagi holati.
///
/// Ikki marta hisoblamaslik qoidasi: majburiyat o'z kategoriyasidagi
/// yozilgan xarajatlar bilan qoplanadi ([recorded]); faqat yozilmagan
/// qismi ([remainder]) «to'langan deb faraz qilinadi» va alohida qo'shiladi.
@immutable
final class ObligationLine {
  const ObligationLine({
    required this.obligation,
    required this.recorded,
    required this.remainder,
  });

  final Obligation obligation;
  final Money recorded;
  final Money remainder;
}

/// Bir davr (oy) bo'yicha pul harakati — audit, «Kimning puli?» va bosh
/// ekran shu yerdan hisoblanadi (SPEC 2.3, 2.4).
@immutable
final class MonthLedger {
  const MonthLedger({
    required this.period,
    required this.currency,
    required this.income,
    required this.expensesByCategory,
    required this.expenses,
    required this.obligations,
    required this.savingsDeposited,
    required this.savingsWithdrawn,
    Money? riboIncome,
  }) : riboIncome = riboIncome ?? const Money.zero(CurrencyCode.uzs);

  final DateRange period;
  final CurrencyCode currency;
  final Money income;

  /// Shundan foizli (ribo) deb belgilangan daromad — alohida ko'rsatiladi
  /// (SPEC 2C.5).
  final Money riboIncome;

  /// Kategoriya ID → yozilgan xarajatlar yig'indisi.
  final Map<String, Money> expensesByCategory;

  /// Barcha yozilgan xarajatlar.
  final Money expenses;
  final List<ObligationLine> obligations;

  /// «Kelajagim»ga ajratilgan (avval yig'ilgan pul — boshlang'ich balans —
  /// kirmaydi).
  final Money savingsDeposited;
  final Money savingsWithdrawn;

  Money get netSavings => savingsDeposited - savingsWithdrawn;

  /// Majburiyatlarning yozilmagan (faraz qilingan) qismi.
  Money get obligationsUnrecorded =>
      Money.sum(obligations.map((o) => o.remainder), currency);

  /// Majburiyatlar jami (oylik summalar).
  Money get obligationsTotal =>
      Money.sum(obligations.map((o) => o.obligation.amount), currency);

  /// «Izohsiz qolgan summa» (kickoff Vazifa 5):
  /// `daromad − (majburiyatlar + kiritilgan xarajatlar + jamg'arma)`.
  ///
  /// Majburiyat o'z kategoriyasida xarajat sifatida yozilgan bo'lsa, u
  /// xarajatlar ichida bir marta hisoblanadi. Manfiy natija — chiqim
  /// kirimdan ko'p yozilgan (ehtimol daromadning bir qismi kiritilmagan).
  Money get unexplained => unexplainedGap(
    income: income,
    obligations: obligationsUnrecorded,
    expenses: expenses,
    savings: netSavings,
  );
}

/// «Izohsiz qolgan summa» (spec `unexplained_gap`):
/// `daromad − (majburiyatlar + xarajatlar + jamg'arma)`; manfiy bo'lishi
/// mumkin.
Money unexplainedGap({
  required Money income,
  required Money obligations,
  required Money expenses,
  required Money savings,
}) => income - (obligations + expenses + savings);

/// Yozuvlardan [period] uchun hisob tuzadi. Boshqa valyutadagi yozuvlar
/// (FxRate'siz) hisobga olinmaydi; o'chirilganlarni chaqiruvchi o'zi
/// chiqarib tashlaydi.
MonthLedger buildMonthLedger({
  required DateRange period,
  required CurrencyCode currency,
  required Iterable<Income> incomes,
  required Iterable<Expense> expenses,
  required Iterable<Obligation> obligations,
  required Iterable<VaultTransaction> vaultTransactions,
}) {
  bool inPeriod(DateTime t) =>
      !t.isBefore(period.startInstant) &&
      t.isBefore(period.endInstantExclusive);
  final zero = Money.zero(currency);

  final income = Money.sum([
    for (final i in incomes)
      if (i.amount.currency == currency && inPeriod(i.receivedAt)) i.amount,
  ], currency);

  final ribo = Money.sum([
    for (final i in incomes)
      if (i.amount.currency == currency &&
          inPeriod(i.receivedAt) &&
          i.sourceType == IncomeSourceType.ribo)
        i.amount,
  ], currency);

  final byCategory = <String, Money>{};
  for (final e in expenses) {
    if (e.amount.currency != currency || !inPeriod(e.spentAt)) continue;
    byCategory[e.categoryId] = (byCategory[e.categoryId] ?? zero) + e.amount;
  }
  final expenseTotal = Money.sum(byCategory.values, currency);

  // Kategoriya bo'yicha yozilgan summa majburiyatlarga navbat bilan
  // taqsimlanadi (bir kategoriyada ikki kredit bo'lishi mumkin).
  final pools = Map<String, Money>.of(byCategory);
  final active = [
    for (final o in obligations)
      if (o.isActive &&
          o.amount.currency == currency &&
          o.meta.createdAt.isBefore(period.endInstantExclusive))
        o,
  ]..sort((a, b) => a.dayOfMonth.compareTo(b.dayOfMonth));
  final lines = <ObligationLine>[];
  for (final o in active) {
    final category = o.categoryId;
    final pool = category == null ? zero : (pools[category] ?? zero);
    final covered = pool < o.amount ? pool : o.amount;
    if (category != null) pools[category] = pool - covered;
    lines.add(
      ObligationLine(
        obligation: o,
        recorded: covered,
        remainder: o.amount - covered,
      ),
    );
  }

  var deposited = zero;
  var withdrawn = zero;
  for (final t in vaultTransactions) {
    if (t.amount.currency != currency || !inPeriod(t.occurredAt)) continue;
    if (t.type == VaultTransactionType.withdraw) {
      withdrawn += t.amount;
    } else if (t.reason != VaultTransactionReason.initial) {
      deposited += t.amount;
    }
  }

  return MonthLedger(
    period: period,
    currency: currency,
    income: income,
    expensesByCategory: byCategory,
    expenses: expenseTotal,
    obligations: lines,
    savingsDeposited: deposited,
    savingsWithdrawn: withdrawn,
    riboIncome: ribo,
  );
}

/// «Kimning puli?» (SPEC 2.4) — daromad kimlarga ketadi.
enum MoneyOwner {
  /// Uy egasi (ijara).
  landlord,

  /// Bank (kredit).
  bank,

  /// Do'kondor (oziq-ovqat, mayda xarajatlar).
  shop,

  /// Davlat / kommunal (kommunal, telefon).
  utilities,

  /// Yoqilg'i va yo'lkira.
  fuel,

  /// O'zingiz («Kelajagim»).
  self,

  /// Sadaqa — isrof emas, alohida (SPEC 2B.8).
  sadaqa,
  other,

  /// Izohsiz qolgan summa.
  unexplained,
}

MoneyOwner ownerOfCategory(CategoryKey? key) => switch (key) {
  CategoryKey.rent => MoneyOwner.landlord,
  CategoryKey.credit => MoneyOwner.bank,
  CategoryKey.groceries ||
  CategoryKey.dailySmall ||
  CategoryKey.snacks => MoneyOwner.shop,
  CategoryKey.utilities || CategoryKey.phone => MoneyOwner.utilities,
  CategoryKey.fuel || CategoryKey.transport => MoneyOwner.fuel,
  CategoryKey.sadaqa => MoneyOwner.sadaqa,
  CategoryKey.children ||
  CategoryKey.cafe ||
  CategoryKey.other ||
  null => MoneyOwner.other,
};

MoneyOwner ownerOfObligation(ObligationKind kind) => switch (kind) {
  ObligationKind.rent => MoneyOwner.landlord,
  ObligationKind.credit => MoneyOwner.bank,
  ObligationKind.utility || ObligationKind.phone => MoneyOwner.utilities,
  ObligationKind.fuel => MoneyOwner.fuel,
  ObligationKind.other => MoneyOwner.other,
};

/// Egalar bo'yicha taqsimot (faqat musbat bo'laklar, [MoneyOwner] tartibida).
/// [categoryKeys] — kategoriya ID → standart kalit (foydalanuvchinikida null).
Map<MoneyOwner, Money> whoseMoney(
  MonthLedger ledger,
  Map<String, CategoryKey?> categoryKeys,
) {
  final zero = Money.zero(ledger.currency);
  final out = <MoneyOwner, Money>{};
  void add(MoneyOwner owner, Money m) {
    if (!m.isPositive) return;
    out[owner] = (out[owner] ?? zero) + m;
  }

  ledger.expensesByCategory.forEach(
    (id, m) => add(ownerOfCategory(categoryKeys[id]), m),
  );
  for (final line in ledger.obligations) {
    add(ownerOfObligation(line.obligation.kind), line.remainder);
  }
  add(MoneyOwner.self, ledger.netSavings);
  add(MoneyOwner.unexplained, ledger.unexplained);
  return {
    for (final owner in MoneyOwner.values)
      if (out.containsKey(owner)) owner: out[owner]!,
  };
}
