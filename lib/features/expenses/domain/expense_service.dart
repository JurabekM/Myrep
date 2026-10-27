import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';

/// Xarajat kiritish (SPEC 2.3, 2B.1–2B.2): toifa kategoriyadan avtomatik,
/// shablonlar, «oxirgisini takrorlash», kategoriya toifasi tarixi bilan.
class ExpenseService {
  ExpenseService({
    required HouseholdRepository households,
    required ExpenseRepository expenses,
    required CategoryRepository categories,
    required ExpenseTemplateRepository templates,
    required NecessityChangeRepository necessityChanges,
    required SyncMetaFactory metaFactory,
    required Clock clock,
  }) : _households = households,
       _expenses = expenses,
       _categories = categories,
       _templates = templates,
       _changes = necessityChanges,
       _meta = metaFactory,
       _clock = clock;

  static const errNotPositive = 'expense_amount_must_be_positive';
  static const errTitleRequired = 'template_title_required';
  static const errNothingToRepeat = 'expense_nothing_to_repeat';

  final HouseholdRepository _households;
  final ExpenseRepository _expenses;
  final CategoryRepository _categories;
  final ExpenseTemplateRepository _templates;
  final NecessityChangeRepository _changes;
  final SyncMetaFactory _meta;
  final Clock _clock;

  Future<String> _hh() async => (await _households.current()).meta.id;

  Future<CurrencyCode> currency() async =>
      (await _households.current()).baseCurrency;

  /// Arxivlanmagan kategoriyalar (tartib bo'yicha).
  Future<List<Category>> categories() async => [
    for (final c in await _categories.listActive(await _hh()))
      if (!c.isArchived) c,
  ];

  /// [necessity] berilmasa — kategoriyaning standart toifasi yoziladi
  /// (sadaqa — toifasiz).
  Future<Expense> add({
    required Money amount,
    required String categoryId,
    required PaymentChannel channel,
    String? memberId,
    DateTime? spentAt,
    String? note,
    Necessity? necessity,
    bool isGift = false,
    bool isOstentation = false,
    bool fundedByDebt = false,
    String? habitId,
  }) async {
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final hh = await _hh();
    final category = await _categories.findById(categoryId);
    return _expenses.add(
      Expense(
        meta: _meta.create(hh),
        amount: amount,
        categoryId: categoryId,
        channel: channel,
        memberId: memberId,
        spentAt: spentAt ?? _clock.nowUtc(),
        note: note,
        necessity: necessity ?? category?.defaultNecessity,
        isGift: isGift,
        isOstentation: isOstentation,
        fundedByDebt: fundedByDebt,
        habitId: habitId,
      ),
    );
  }

  Future<List<Expense>> listIn(DateRange range) async =>
      _expenses.listInRange(await _hh(), range);

  Future<void> delete(String id) => _expenses.softDelete(id);

  /// «Bekor qilish»: o'chirilgan xarajatni qaytaradi.
  Future<void> restore(String id) => _expenses.restore(id);

  // --- Tez kiritish ---

  Future<Expense?> latest() async => _expenses.latest(await _hh());

  /// Oxirgi xarajatni hozirgi vaqt bilan takrorlaydi (izohsiz).
  Future<Expense> repeatLast({String? memberId}) async {
    final last = await latest();
    if (last == null) throw const DomainRuleException(errNothingToRepeat);
    return add(
      amount: last.amount,
      categoryId: last.categoryId,
      channel: last.channel,
      memberId: memberId ?? last.memberId,
      necessity: last.necessity,
      isGift: last.isGift,
      isOstentation: last.isOstentation,
      fundedByDebt: last.fundedByDebt,
      habitId: last.habitId,
    );
  }

  Future<List<ExpenseTemplate>> templates() async =>
      _templates.listActive(await _hh());

  Future<ExpenseTemplate> addTemplate({
    required String title,
    required Money amount,
    required String categoryId,
    PaymentChannel channel = PaymentChannel.cash,
    Necessity? necessity,
    String? habitId,
  }) async {
    if (title.trim().isEmpty) throw const DomainRuleException(errTitleRequired);
    if (!amount.isPositive) throw const DomainRuleException(errNotPositive);
    final hh = await _hh();
    final count = (await _templates.listActive(hh)).length;
    return _templates.add(
      ExpenseTemplate(
        meta: _meta.create(hh),
        title: title.trim(),
        amount: amount,
        categoryId: categoryId,
        channel: channel,
        necessity: necessity,
        habitId: habitId,
        sortOrder: count,
      ),
    );
  }

  Future<void> deleteTemplate(String id) => _templates.softDelete(id);

  /// Shablon bo'yicha bir bosishda yozish (vidjet ham shuni ishlatadi).
  Future<Expense> recordTemplate(
    ExpenseTemplate t, {
    String? memberId,
    DateTime? spentAt,
  }) => add(
    amount: t.amount,
    categoryId: t.categoryId,
    channel: t.channel,
    memberId: memberId,
    spentAt: spentAt,
    necessity: t.necessity,
    habitId: t.habitId,
  );

  // --- Kategoriya toifasi (SPEC 2B.2) ---

  /// Kategoriyaning standart toifasini o'zgartiradi va tarixga yozadi.
  /// Eski xarajatlar o'zgarmaydi (ular yozilgan paytdagi toifani saqlaydi).
  Future<Category> setCategoryNecessity(
    Category category,
    Necessity? necessity, {
    String? memberId,
  }) async {
    if (category.defaultNecessity == necessity) return category;
    final updated = await _categories.update(
      category.copyWith(defaultNecessity: necessity),
    );
    await _changes.add(
      NecessityChange(
        meta: _meta.create(category.meta.householdId),
        categoryId: category.meta.id,
        from: category.defaultNecessity,
        to: necessity,
        memberId: memberId,
      ),
    );
    return updated;
  }

  Future<List<NecessityChange>> necessityHistory(String categoryId) =>
      _changes.forCategory(categoryId);
}
