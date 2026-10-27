import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/features/budget/data/drift_budget_repositories.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/budget/domain/havas_service.dart';
import 'package:baraka_daftari/features/budget/domain/insights_service.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/domain/expense_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

void main() {
  late TestDb t;
  late ExpenseService expenses;
  late HavasService havas;
  late InsightsService insights;
  late HouseholdService households;
  late MemberPinService memberPins;
  late Member owner;
  late Member wife;

  setUp(() async {
    t = TestDb.open();
    final hh = DriftHouseholdRepository(t.db, t.clock);
    final members = DriftMemberRepository(t.db, t.clock);
    final cats = DriftCategoryRepository(t.db, t.clock);
    final exp = DriftExpenseRepository(t.db, t.clock);
    households = HouseholdService(
      households: hh,
      members: members,
      metaFactory: t.meta,
    );
    memberPins = MemberPinService(
      pins: PinService(
        store: InMemorySecureBlobStore(),
        hasher: ReferencePinHasher(),
        clock: t.clock,
        iterations: 1000,
      ),
      members: members,
    );
    expenses = ExpenseService(
      households: hh,
      expenses: exp,
      categories: cats,
      templates: DriftExpenseTemplateRepository(t.db, t.clock),
      necessityChanges: DriftNecessityChangeRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    havas = HavasService(
      households: hh,
      members: members,
      limits: DriftHavasLimitRepository(t.db, t.clock),
      consents: DriftLimitConsentRepository(t.db, t.clock),
      memberPins: memberPins,
      expenses: exp,
      categories: cats,
      metaFactory: t.meta,
      clock: t.clock,
    );
    insights = InsightsService(
      households: hh,
      expenses: exp,
      categories: cats,
      obligations: DriftObligationRepository(t.db, t.clock),
      habits: DriftHabitRepository(t.db, t.clock),
      treats: DriftScheduledTreatRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    owner = (await households.members(ownerName: 'Men')).single;
    wife = await households.addMember('Zuhra', MemberRole.adult);
  });

  Future<Category> cat(CategoryKey key) async =>
      (await expenses.categories()).firstWhere((c) => c.systemKey == key);

  Future<Expense> spend(
    CategoryKey key,
    int major, {
    Necessity? necessity,
    bool gift = false,
    bool debt = false,
    bool ostentation = false,
  }) async => expenses.add(
    amount: som(major),
    categoryId: (await cat(key)).meta.id,
    channel: PaymentChannel.cash,
    necessity: necessity,
    isGift: gift,
    fundedByDebt: debt,
    isOstentation: ostentation,
  );

  group('uch toifa (SPEC 2B.2)', () {
    test(
      'standart toifalar: bola = kerak, ijara = zarur, sadaqa toifasiz',
      () async {
        expect(
          (await cat(CategoryKey.children)).defaultNecessity,
          Necessity.kerak,
        );
        expect((await cat(CategoryKey.rent)).defaultNecessity, Necessity.zarur);
        expect(
          (await cat(CategoryKey.snacks)).defaultNecessity,
          Necessity.havas,
        );
        expect((await cat(CategoryKey.sadaqa)).defaultNecessity, isNull);
      },
    );

    test(
      'xarajatda toifa kategoriyadan olinadi, oʻzgartirsa boʻladi',
      () async {
        expect(
          (await spend(CategoryKey.groceries, 50000)).necessity,
          Necessity.zarur,
        );
        expect(
          (await spend(
            CategoryKey.groceries,
            50000,
            necessity: Necessity.havas,
          )).necessity,
          Necessity.havas,
        );
      },
    );

    test(
      'kategoriya toifasini oʻzgartirish tarixga yoziladi (kim, qachon)',
      () async {
        final phone = await cat(CategoryKey.phone);
        final updated = await expenses.setCategoryNecessity(
          phone,
          Necessity.zarur,
          memberId: wife.meta.id,
        );
        expect(updated.defaultNecessity, Necessity.zarur);
        t.clock.advance(const Duration(days: 1));
        await expenses.setCategoryNecessity(updated, Necessity.havas);
        final history = await expenses.necessityHistory(phone.meta.id);
        expect(history.map((h) => (h.from, h.to)), [
          (Necessity.zarur, Necessity.havas),
          (Necessity.kerak, Necessity.zarur),
        ]);
        expect(history.last.memberId, wife.meta.id);
        expect(
          history.first.meta.createdAt.isAfter(history.last.meta.createdAt),
          isTrue,
        );
        // Oʻzgarishsiz — tarixga yozilmaydi.
        await expenses.setCategoryNecessity(
          await cat(CategoryKey.phone),
          Necessity.havas,
        );
        expect(await expenses.necessityHistory(phone.meta.id), hasLength(2));
      },
    );
  });

  group('havas chegarasi — oilaviy kelishuv (SPEC 2B.3)', () {
    test('2 kattadan 1 tasi tasdiqlasa — chegara faol emas', () async {
      final limit = await havas.propose(som(500000), proposedBy: owner.meta.id);
      final (check, agreed) = await havas.consent(limit, owner, '');
      expect(check, isA<PinAccepted>());
      expect(agreed, isFalse);
      final o = await havas.overview();
      expect(o.active, isNull);
      expect(o.usage, isNull);
      expect(o.pending!.waitingFor.map((m) => m.displayName), ['Zuhra']);
    });

    test('ikkalasi tasdiqlasa — faol; qayta tasdiq takrorlanmaydi', () async {
      final limit = await havas.propose(som(500000));
      await havas.consent(limit, owner, '');
      final (_, agreed) = await havas.consent(limit, wife, '');
      expect(agreed, isTrue);
      final (_, again) = await havas.consent(limit, wife, '');
      expect(again, isFalse);
      final o = await havas.overview();
      expect(o.active!.limit.amount, som(500000));
      expect(o.pending, isNull);
    });

    test('shaxsiy PIN boʻlsa — notoʻgʻri PIN rozilik bermaydi', () async {
      wife = await memberPins.setPin(wife, '482915');
      final limit = await havas.propose(som(500000));
      await havas.consent(limit, owner, '');
      final (check, agreed) = await havas.consent(limit, wife, '111111');
      expect(check, isA<PinRejected>());
      expect(agreed, isFalse);
      expect((await havas.overview()).active, isNull);
      expect((await havas.consent(limit, wife, '482915')).$2, isTrue);
    });

    test('bola rozilik bera olmaydi va kelishuvga kerak emas', () async {
      final son = await households.addMember('Ali', MemberRole.child);
      final limit = await havas.propose(som(300000));
      await expectLater(
        havas.consent(limit, son, ''),
        throwsA(isA<DomainRuleException>()),
      );
      await havas.consent(limit, owner, '');
      expect((await havas.consent(limit, wife, '')).$2, isTrue);
    });

    test('yangi taklif kelishilguncha eski chegara amalda', () async {
      final old = await havas.propose(som(500000));
      await havas.consent(old, owner, '');
      await havas.consent(old, wife, '');
      t.clock.advance(const Duration(minutes: 1));
      final next = await havas.propose(som(400000));
      await havas.consent(next, owner, '');
      final o = await havas.overview();
      expect(o.active!.limit.meta.id, old.meta.id);
      expect(o.pending!.limit.meta.id, next.meta.id);
    });

    test('80 % — yaqin, 100 % — oshdi; bloklash yoʻq', () async {
      final limit = await havas.propose(som(100000));
      await havas.consent(limit, owner, '');
      await havas.consent(limit, wife, '');
      await spend(CategoryKey.snacks, 79000);
      expect((await havas.overview()).usage!.level, LimitLevel.ok);
      await spend(CategoryKey.cafe, 1000);
      expect((await havas.overview()).usage!.level, LimitLevel.near);
      await spend(CategoryKey.cafe, 25000);
      final usage = (await havas.overview()).usage!;
      expect(usage.level, LimitLevel.over);
      expect(usage.remaining, som(-5000));
    });
  });

  group('isrof va saxovat (SPEC 2B.8)', () {
    test(
      'sadaqa havas hisobiga kirmaydi — «havas» deb belgilansa ham',
      () async {
        await spend(CategoryKey.sadaqa, 200000);
        await spend(CategoryKey.sadaqa, 50000, necessity: Necessity.havas);
        await spend(CategoryKey.snacks, 30000);
        final o = await havas.overview();
        expect(o.spent, som(30000));
        expect(o.sadaqa, som(250000));
      },
    );

    test('sovgʻa hisobga kirmaydi; obroʻ va qarzga havas alohida', () async {
      await spend(CategoryKey.cafe, 40000, gift: true);
      await spend(CategoryKey.other, 300000, ostentation: true);
      final debt = await spend(
        CategoryKey.other,
        900000,
        necessity: Necessity.havas,
        debt: true,
      );
      await spend(CategoryKey.groceries, 100000, debt: true);
      final o = await havas.overview();
      expect(o.spent, som(900000));
      expect(o.gifts, som(40000));
      expect(o.ostentation, som(300000));
      expect(o.debtFundedHavas.map((e) => e.meta.id), [debt.meta.id]);
    });
  });

  group('jamlash effekti (SPEC 2B.1)', () {
    test(
      'yillik jamlash: 30 kunda 300 000 → oyiga 300 000, yiliga 3 650 000',
      () {
        final r = Rollup(som(300000), 30);
        expect(r.perWeek, som(70000));
        expect(r.perMonth, som(300000));
        expect(r.perYear, som(3650000));
      },
    );

    test('kuniga 2 ta ichimlik (2 × 6 000) — yiliga 4 380 000', () async {
      for (var day = 0; day < 30; day++) {
        await spend(CategoryKey.snacks, 6000);
        await spend(CategoryKey.snacks, 6000);
        t.clock.advance(const Duration(days: 1));
      }
      t.clock.advance(const Duration(days: -1));
      final s = await insights.spending();
      final line = s.lines.single;
      expect(line.subject.systemKey, CategoryKey.snacks);
      expect(line.rollup.total, som(360000));
      expect(line.rollup.perYear, som(4380000));
    });

    test('ijara bilan taqqoslash: oyiga 1,2 mln — ijaraning 40 %i', () async {
      final obligations = ObligationService(
        households: DriftHouseholdRepository(t.db, t.clock),
        obligations: DriftObligationRepository(t.db, t.clock),
        debts: DriftDebtRepository(t.db, t.clock),
        categories: DriftCategoryRepository(t.db, t.clock),
        installments: DriftDebtInstallmentRepository(t.db, t.clock),
        payments: DriftDebtPaymentRepository(t.db, t.clock),
        metaFactory: t.meta,
      );
      await obligations.addObligation(
        title: 'Uy ijarasi',
        kind: ObligationKind.rent,
        amount: som(3000000),
        dayOfMonth: 5,
      );
      await spend(CategoryKey.cafe, 1200000);
      // Majburiyat kategoriyalari jamlashga kirmaydi.
      await spend(CategoryKey.rent, 3000000);
      final s = await insights.spending();
      expect(s.lines.map((l) => l.subject.systemKey), [CategoryKey.cafe]);
      expect(s.reference!.title, 'Uy ijarasi');
      expect(s.shareOfReference(s.lines.single.rollup.perMonth), 4000);
    });

    test('30 kundan eski xarajat oynaga kirmaydi', () async {
      await spend(CategoryKey.cafe, 100000);
      t.clock.advance(const Duration(days: 30));
      expect((await insights.spending()).lines, isEmpty);
    });
  });

  group('shablonlar va «oxirgisini takrorlash» (SPEC 2B.1)', () {
    test('shablon bir bosishda yoziladi, toifa kategoriyadan', () async {
      final tpl = await expenses.addTemplate(
        title: 'Somsa',
        amount: som(8000),
        categoryId: (await cat(CategoryKey.snacks)).meta.id,
      );
      final e = await expenses.recordTemplate(tpl, memberId: wife.meta.id);
      expect(e.amount, som(8000));
      expect(e.necessity, Necessity.havas);
      expect(e.memberId, wife.meta.id);
      expect((await expenses.templates()).single.title, 'Somsa');
    });

    test('oxirgisini takrorlash — yangi vaqt bilan nusxa', () async {
      await expectLater(
        expenses.repeatLast(),
        throwsA(isA<DomainRuleException>()),
      );
      final first = await spend(CategoryKey.fuel, 120000, debt: true);
      t.clock.advance(const Duration(hours: 3));
      final copy = await expenses.repeatLast();
      expect(copy.meta.id, isNot(first.meta.id));
      expect(copy.amount, first.amount);
      expect(copy.categoryId, first.categoryId);
      expect(copy.fundedByDebt, isTrue);
      expect(copy.spentAt, t.clock.nowUtc());
    });

    test('suring bilan oʻchirish «Bekor qilish» bilan qaytariladi', () async {
      final e = await spend(CategoryKey.fuel, 50000);
      await expenses.delete(e.meta.id);
      expect((await expenses.latest())?.meta.id, isNot(e.meta.id));
      await expenses.restore(e.meta.id);
      expect((await expenses.latest())?.meta.id, e.meta.id);
    });
  });

  group('odatlar va «Juma shirinligi»', () {
    test('odat statistikasi: oyiga va yiliga', () async {
      final habit = await insights.addHabit('Sigaret');
      for (var i = 0; i < 30; i++) {
        await expenses.add(
          amount: som(15000),
          categoryId: (await cat(CategoryKey.dailySmall)).meta.id,
          channel: PaymentChannel.cash,
          habitId: habit.meta.id,
        );
      }
      final line = (await insights.habits()).single;
      expect(line.rollup.perMonth, som(450000));
      expect(line.rollup.perYear, som(5475000));
    });

    test('shirinlik: kun 1–7, summa musbat', () async {
      final treat = await insights.addTreat(
        title: 'Juma shirinligi',
        amount: som(30000),
      );
      expect(treat.weekday, DateTime.friday);
      await expectLater(
        insights.addTreat(title: 'x', amount: som(1), weekday: 8),
        throwsA(isA<DomainRuleException>()),
      );
      final off = await insights.setTreatActive(treat, on: false);
      expect((await insights.treats()).single.isActive, isFalse);
      expect(off.isActive, isFalse);
    });
  });
}
