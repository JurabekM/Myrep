import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/audit/data/drift_monthly_report_repository.dart';
import 'package:baraka_daftari/features/budget/data/drift_budget_repositories.dart';
import 'package:baraka_daftari/features/budget/domain/rescue.dart';
import 'package:baraka_daftari/features/budget/domain/rescue_service.dart';
import 'package:baraka_daftari/features/envelopes/data/drift_envelope_repositories.dart';
import 'package:baraka_daftari/features/envelopes/domain/envelope_service.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/domain/expense_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/subscriptions/data/drift_subscription_repository.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription.dart';
import 'package:baraka_daftari/features/subscriptions/domain/subscription_service.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

/// Toshkent vaqti (UTC+5) → UTC.
DateTime tashkent(int y, int m, int d, [int h = 12, int min = 0]) =>
    DateTime.utc(y, m, d, h, min).subtract(const Duration(hours: 5));

void main() {
  group('formula (SPEC 2B.7)', () {
    test('havas kamaydi: bazaviy 300 000 / 30 kun, 3 kunda 10 000', () {
      final r = computeRescue(
        currency: uzs,
        elapsedDays: 3,
        currentHavas: som(10000),
        baselineHavas: som(300000),
        subscriptions: som(2000),
        envelopeLeftovers: som(5000),
        transferred: const Money.zero(uzs),
      );
      expect(r.havasDelta, som(20000));
      expect(r.total, som(27000));
      expect(r.available, som(27000));
      expect(r.spentMore, isFalse);
    });

    test('manfiy holat: koʻproq sarflangan — 0 koʻrsatiladi, ayblanmaydi', () {
      final r = computeRescue(
        currency: uzs,
        elapsedDays: 3,
        currentHavas: som(50000),
        baselineHavas: som(300000),
        subscriptions: som(2000),
        envelopeLeftovers: const Money.zero(uzs),
        transferred: const Money.zero(uzs),
      );
      expect(r.havasDelta, som(-20000));
      expect(r.spentMore, isTrue);
      expect(r.havasShown, const Money.zero(uzs));
      // Manfiy qism boshqa qutqarishlarni yemaydi.
      expect(r.total, som(2000));

      final none = computeRescue(
        currency: uzs,
        elapsedDays: 7,
        currentHavas: som(900000),
        baselineHavas: som(300000),
        subscriptions: const Money.zero(uzs),
        envelopeLeftovers: const Money.zero(uzs),
        transferred: const Money.zero(uzs),
      );
      expect(none.total, const Money.zero(uzs));
      expect(none.available, const Money.zero(uzs));
    });

    test('bazaviy oy yoʻq — havas qismi 0, qolganlari hisoblanadi', () {
      final r = computeRescue(
        currency: uzs,
        elapsedDays: 5,
        currentHavas: som(80000),
        subscriptions: som(4000),
        envelopeLeftovers: som(6000),
        transferred: som(3000),
      );
      expect(r.hasBaseline, isFalse);
      expect(r.havasDelta, const Money.zero(uzs));
      expect(r.total, som(10000));
      expect(r.available, som(7000));
    });

    test('notoʻgʻri kunlar rad etiladi', () {
      expect(
        () => computeRescue(
          currency: uzs,
          elapsedDays: 0,
          currentHavas: som(1),
          subscriptions: som(0),
          envelopeLeftovers: som(0),
          transferred: som(0),
        ),
        throwsArgumentError,
      );
    });
  });

  group('obuna tejami', () {
    test('bekor qilingan obunaning yillik tejami', () {
      Money yearly(int major, SubscriptionCycle c) => yearlyCost(som(major), c);
      expect(yearly(49000, SubscriptionCycle.monthly), som(588000));
      expect(yearly(400000, SubscriptionCycle.yearly), som(400000));
      expect(
        monthlyEquivalent(som(400000), SubscriptionCycle.yearly),
        const Money(3333333, uzs),
      );
    });

    test('davrda: bekor qilingan kundan boshlab, oʻtgan kunlar boʻyicha', () {
      final week = DateRange(LocalDate(2026, 10, 9), LocalDate(2026, 10, 16));
      Money savings(LocalDate cancelled, LocalDate today) =>
          subscriptionSavings(
            currency: uzs,
            cancelled: [(som(30000), cancelled)],
            period: week,
            today: today,
          );
      // Haftadan oldin bekor qilingan: 3 kun × 1 000.
      expect(
        savings(LocalDate(2026, 9, 1), LocalDate(2026, 10, 11)),
        som(3000),
      );
      // Hafta ichida (10-10) bekor qilingan: 10-10 … 10-11 = 2 kun.
      expect(
        savings(LocalDate(2026, 10, 10), LocalDate(2026, 10, 11)),
        som(2000),
      );
      // Kelajakdagi sana — hisobga kirmaydi.
      expect(
        savings(LocalDate(2026, 10, 20), LocalDate(2026, 10, 11)),
        const Money.zero(uzs),
      );
    });
  });

  group('servislar', () {
    late TestDb t;
    late ExpenseService expenses;
    late SubscriptionService subs;
    late EnvelopeService envelopes;
    late RescueService rescue;
    late VaultService vault;
    late DriftEnvelopePeriodRepository periods;

    setUp(() {
      t = TestDb.open();
      final hh = DriftHouseholdRepository(t.db, t.clock);
      final exp = DriftExpenseRepository(t.db, t.clock);
      final cats = DriftCategoryRepository(t.db, t.clock);
      final rescues = DriftSavingsRescueRepository(t.db, t.clock);
      periods = DriftEnvelopePeriodRepository(t.db, t.clock);
      expenses = ExpenseService(
        households: hh,
        expenses: exp,
        categories: cats,
        templates: DriftExpenseTemplateRepository(t.db, t.clock),
        necessityChanges: DriftNecessityChangeRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      subs = SubscriptionService(
        households: hh,
        subscriptions: DriftSubscriptionRepository(t.db, t.clock),
        rescues: rescues,
        metaFactory: t.meta,
        clock: t.clock,
      );
      envelopes = EnvelopeService(
        households: hh,
        envelopes: DriftEnvelopeRepository(t.db, t.clock),
        periods: periods,
        expenses: exp,
        rescues: rescues,
        metaFactory: t.meta,
        clock: t.clock,
      );
      vault = VaultService(
        households: hh,
        assets: DriftAssetRepository(t.db, t.clock),
        transactions: DriftVaultTransactionRepository(t.db, t.clock),
        rules: DriftAllocationRuleRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      rescue = RescueService(
        households: hh,
        expenses: exp,
        categories: cats,
        reports: DriftMonthlyReportRepository(t.db, t.clock),
        rescues: rescues,
        vault: vault,
        metaFactory: t.meta,
        clock: t.clock,
      );
    });

    Future<Category> cat(CategoryKey key) async =>
        (await expenses.categories()).firstWhere((c) => c.systemKey == key);

    Future<void> spend(CategoryKey key, int major, DateTime at) async =>
        expenses.add(
          amount: som(major),
          categoryId: (await cat(key)).meta.id,
          channel: PaymentChannel.card,
          spentAt: at,
        );

    test('obuna: yillik narx, unutilgan, bekor qilish → qutqarish', () async {
      final s = await subs.add(title: 'Kino', price: som(49000));
      expect(s.yearly, som(588000));
      expect(subs.isForgotten(s), isFalse);
      t.clock.advance(const Duration(days: 30));
      expect(subs.isForgotten((await subs.list()).single), isTrue);
      final used = await subs.markUsed((await subs.list()).single);
      expect(subs.isForgotten(used), isFalse);

      final cancelled = await subs.cancel(used);
      expect(cancelled.isActive, isFalse);
      expect(subs.isForgotten(cancelled), isFalse);
      await expectLater(
        subs.cancel(cancelled),
        throwsA(isA<DomainRuleException>()),
      );
      expect(
        SubscriptionService.annualTotal(await subs.list(), uzs),
        const Money.zero(uzs),
      );
    });

    test(
      'konvert davri hafta chegarasida yopiladi (payshanba 23:59 / juma 00:00)',
      () async {
        final groceries = await cat(CategoryKey.groceries);
        final e = await envelopes.create(
          title: 'Bozor',
          weeklyLimit: som(200000),
          isCash: false,
          categoryIds: [groceries.meta.id],
        );
        // Juma 2026-10-09 — hafta 10-09 … 10-15.
        expect(
          (await envelopes.status()).single.week.start,
          LocalDate(2026, 10, 9),
        );

        t.clock.setNow(tashkent(2026, 10, 15, 23, 59));
        await spend(CategoryKey.groceries, 50000, t.clock.nowUtc());
        // Boshqa kategoriya konvertga kirmaydi.
        await spend(CategoryKey.cafe, 70000, t.clock.nowUtc());
        final thursday = (await envelopes.status()).single;
        expect(thursday.week.start, LocalDate(2026, 10, 9));
        expect(thursday.current.spent, som(50000));
        expect(thursday.current.left, som(150000));

        t.clock.setNow(tashkent(2026, 10, 16, 0));
        await spend(CategoryKey.groceries, 30000, t.clock.nowUtc());
        final friday = (await envelopes.status()).single;
        expect(friday.week.start, LocalDate(2026, 10, 16));
        expect(friday.current.spent, som(30000));
        expect(friday.pendingClose, isEmpty, reason: 'karta — avtomatik');

        final closed = (await periods.forEnvelope(e.meta.id)).first;
        expect(closed.weekStart, LocalDate(2026, 10, 9));
        expect(closed.isClosed, isTrue);
        expect(closed.leftover, som(150000));
        // Ikki marta yopilmaydi.
        await envelopes.status();
        expect(
          (await rescue.overview()).week.envelopes,
          som(150000),
          reason: 'qoldiq yangi haftada qutqarilgan',
        );
      },
    );

    test('naqd konvert: qoldiq kiritilguncha kutadi; oshib ketsa 0', () async {
      final cafe = await cat(CategoryKey.cafe);
      await envelopes.create(
        title: 'Havas',
        weeklyLimit: som(100000),
        categoryIds: [cafe.meta.id],
      );
      await envelopes.status();
      t.clock.setNow(tashkent(2026, 10, 14));
      await spend(CategoryKey.cafe, 130000, t.clock.nowUtc());
      expect((await envelopes.status()).single.current.isOver, isTrue);

      t.clock.setNow(tashkent(2026, 10, 17));
      final pending = (await envelopes.status()).single.pendingClose.single;
      await envelopes.closeWithLeftover(pending, const Money.zero(uzs));
      expect((await envelopes.status()).single.pendingClose, isEmpty);
      expect((await rescue.overview()).week.envelopes, const Money.zero(uzs));
      final reread = (await periods.forEnvelope(pending.envelopeId)).first;
      expect(reread.isClosed, isTrue);
      await expectLater(
        envelopes.closeWithLeftover(reread, som(1)),
        throwsA(isA<DomainRuleException>()),
      );
    });

    test('kategoriya bitta konvertga tegishli', () async {
      final g = (await cat(CategoryKey.groceries)).meta.id;
      final first = await envelopes.create(
        title: 'A',
        weeklyLimit: som(1000),
        categoryIds: [g],
      );
      await envelopes.create(
        title: 'B',
        weeklyLimit: som(1000),
        categoryIds: [g],
      );
      final list = await envelopes.envelopes();
      expect(
        list.firstWhere((e) => e.meta.id == first.meta.id).categoryIds,
        isEmpty,
      );
    });

    test('qutqarilgan pul: bazaviy oy + obuna, oʻtkazish bir marta', () async {
      // Bazaviy oy — sentabr (30 kun): havas 300 000.
      await spend(CategoryKey.snacks, 300000, tashkent(2026, 9, 10));
      await rescue.setBaseline(LocalDate(2026, 9, 15));
      expect(
        await rescue.baseline(),
        DateRange(LocalDate(2026, 9, 1), LocalDate(2026, 10, 1)),
      );

      final s = await subs.add(title: 'Musiqa', price: som(30000));
      t.clock.setNow(tashkent(2026, 10, 10));
      await subs.cancel(s);
      t.clock.setNow(tashkent(2026, 10, 11));
      await spend(CategoryKey.cafe, 10000, t.clock.nowUtc());
      // Sadaqa va sovgʻa havasga kirmaydi.
      await spend(CategoryKey.sadaqa, 500000, t.clock.nowUtc());

      final o = await rescue.overview();
      expect(o.week.havasDelta, som(20000)); // 300 000 × 3/30 − 10 000
      expect(o.week.subscriptions, som(2000)); // 1 000 × 2 kun
      expect(o.week.total, som(22000));

      expect(await rescue.transferWeek(), som(22000));
      final after = await rescue.overview();
      expect(after.week.transferred, som(22000));
      expect(after.week.available, const Money.zero(uzs));
      expect((await vault.overview()).balance, som(22000));
      await expectLater(
        rescue.transferWeek(),
        throwsA(isA<DomainRuleException>()),
      );
    });

    test(
      'qutqarilgan pul qarzga: qarz qolganidan oshmaydi, bir marta',
      () async {
        await spend(CategoryKey.snacks, 300000, tashkent(2026, 9, 10));
        await rescue.setBaseline(LocalDate(2026, 9, 15));
        t.clock.setNow(tashkent(2026, 10, 11));
        expect((await rescue.overview()).week.available, som(30000));

        final paid = <Money>[];
        final moved = await rescue.transferWeekTo((amount) async {
          paid.add(amount);
          return 'payment-1';
        }, max: som(12000));
        expect(moved, som(12000));
        expect(paid, [som(12000)]);
        final after = await rescue.overview();
        expect(after.week.transferred, som(12000));
        expect(after.week.available, som(18000));
        expect((await vault.overview()).balance, const Money.zero(uzs));
      },
    );

    test('koʻproq sarflangan hafta — 0, oʻtkazib boʻlmaydi', () async {
      await spend(CategoryKey.snacks, 300000, tashkent(2026, 9, 10));
      await rescue.setBaseline(LocalDate(2026, 9, 1));
      t.clock.setNow(tashkent(2026, 10, 11));
      await spend(CategoryKey.cafe, 90000, t.clock.nowUtc());
      final o = await rescue.overview();
      expect(o.week.spentMore, isTrue);
      expect(o.week.total, const Money.zero(uzs));
      await expectLater(
        rescue.transferWeek(),
        throwsA(isA<DomainRuleException>()),
      );
    });
  });
}
