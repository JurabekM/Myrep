import 'package:baraka_daftari/core/db/drift_fx_rate_repository.dart';
import 'package:baraka_daftari/core/db/seed.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/fx_rate.dart';
import 'package:baraka_daftari/core/money/fx_rate_repository.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:drift/drift.dart' hide isNotNull, isNull;
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

void main() {
  late TestDb t;
  late String hh;

  setUp(() async {
    t = TestDb.open();
    hh = await t.householdId();
  });

  group('sxema va seed', () {
    test('sxema versiyasi 9', () {
      expect(t.db.schemaVersion, 17);
    });

    test('bitta uy xoʻjaligi va 13 ta standart kategoriya', () async {
      final household = await DriftHouseholdRepository(t.db, t.clock).current();
      expect(household.meta.id, household.meta.householdId);
      expect(household.weekAnchor, DateTime.friday);
      expect(household.monthStartDay, 1);
      expect(household.baseCurrency, CurrencyCode.uzs);

      final categories = await DriftCategoryRepository(
        t.db,
        t.clock,
      ).listActive(hh);
      expect(categories.map((c) => c.systemKey), defaultCategoryKeys);
      expect(categories.map((c) => c.sortOrder), List.generate(13, (i) => i));
      expect(
        categories.map((c) => c.meta.id).toSet(),
        hasLength(13),
        reason: 'ID takrorlanmaydi',
      );
    });

    test('foreign_keys yoqilgan', () async {
      final row = await t.db.customSelect('PRAGMA foreign_keys').getSingle();
      expect(row.data.values.first, 1);
    });
  });

  group('umumiy CRUD (Income misolida)', () {
    late DriftIncomeRepository repo;

    Income income(int major, {DateTime? at}) => Income(
      meta: t.meta.create(hh),
      amount: som(major),
      source: IncomeSource.dailyWork,
      channel: PaymentChannel.cash,
      receivedAt: at ?? t.clock.nowUtc(),
    );

    setUp(() => repo = DriftIncomeRepository(t.db, t.clock));

    test('qoʻshish va oʻqish — barcha maydonlar saqlanadi', () async {
      final original = income(
        150000,
      ).copyWith(sourceType: IncomeSourceType.ter, note: 'taksi');
      await repo.add(original);
      final loaded = await repo.findById(original.meta.id);
      expect(loaded, original);
      expect(loaded!.receivedAt.isUtc, isTrue);
    });

    test('yangilash versiyani oshiradi va updatedAt ni yangilaydi', () async {
      final a = await repo.add(income(100));
      t.clock.advance(const Duration(minutes: 5));
      final b = await repo.update(a.copyWith(amount: som(120)));
      expect(b.meta.version, 2);
      expect(
        b.meta.updatedAt,
        a.meta.updatedAt.add(const Duration(minutes: 5)),
      );
      expect(b.meta.createdAt, a.meta.createdAt);
      expect((await repo.findById(a.meta.id))!.amount, som(120));
    });

    test('eskirgan versiya bilan yangilash rad etiladi', () async {
      final a = await repo.add(income(100));
      await repo.update(a.copyWith(amount: som(110)));
      expect(
        () => repo.update(a.copyWith(amount: som(999))),
        throwsA(isA<ConcurrentModificationException>()),
      );
    });

    test('soft delete: roʻyxatdan chiqadi, lekin bazada qoladi', () async {
      final a = await repo.add(income(100));
      final b = await repo.add(income(200));
      t.clock.advance(const Duration(seconds: 1));
      await repo.softDelete(a.meta.id);

      final active = await repo.listActive(hh);
      expect(active.map((e) => e.meta.id), [b.meta.id]);

      final deleted = await repo.findById(a.meta.id);
      expect(deleted!.meta.deletedAt, t.clock.nowUtc());
      expect(deleted.meta.version, 2);
      expect(await t.db.select(t.db.incomes).get(), hasLength(2));
    });

    test(
      'oʻchirilgan yozuvni qayta oʻchirish yoki yangilash mumkin emas',
      () async {
        final a = await repo.add(income(100));
        await repo.softDelete(a.meta.id);
        expect(
          () => repo.softDelete(a.meta.id),
          throwsA(isA<ConcurrentModificationException>()),
        );
        expect(
          () => repo.update(a),
          throwsA(isA<ConcurrentModificationException>()),
        );
      },
    );

    test('watchActive oʻzgarishlarni oqim sifatida beradi', () async {
      final stream = repo.watchActive(hh);
      final a = await repo.add(income(100));
      await expectLater(
        stream,
        emits(predicate<List<Income>>((l) => l.length == 1)),
      );
      await repo.softDelete(a.meta.id);
      await expectLater(stream, emits(isEmpty));
    });

    test('listInRange Toshkent sanasi boʻyicha, latest', () async {
      // 2026-10-08 18:59 UTC = 23:59 Toshkent (8-okt); 19:00 UTC = 9-okt.
      final late8 = await repo.add(
        income(1, at: DateTime.utc(2026, 10, 8, 18, 59)),
      );
      final early9 = await repo.add(
        income(2, at: DateTime.utc(2026, 10, 8, 19)),
      );
      const cal = BudgetCalendar();
      final week = cal.weekOf(LocalDate(2026, 10, 9)); // juma
      final inWeek = await repo.listInRange(hh, week);
      expect(inWeek.map((e) => e.meta.id), [early9.meta.id]);
      expect((await repo.latest(hh))!.meta.id, early9.meta.id);
      expect(late8.meta.id, isNot(early9.meta.id));
    });

    test('summa musbat boʻlishi baza darajasida ham tekshiriladi', () async {
      expect(
        () => repo.add(income(1).copyWith(amount: som(0))),
        throwsA(isA<Exception>()),
      );
    });

    test('boshqa uy xoʻjaligi yozuvlari koʻrinmaydi', () async {
      await repo.add(income(1));
      expect(await repo.listActive('boshqa'), isEmpty);
    });
  });

  group('xarajatlar va kategoriyalar', () {
    test('xarajat: kelajak maydonlari standart qiymat bilan', () async {
      final categories = DriftCategoryRepository(t.db, t.clock);
      final repo = DriftExpenseRepository(t.db, t.clock);
      final groceries = await categories.findBySystemKey(
        hh,
        CategoryKey.groceries,
      );
      final e = Expense(
        meta: t.meta.create(hh),
        amount: som(45000),
        categoryId: groceries!.meta.id,
        channel: PaymentChannel.card,
        spentAt: t.clock.nowUtc(),
      );
      await repo.add(e);
      final loaded = await repo.findById(e.meta.id);
      expect(loaded, e);
      expect(loaded!.necessity, isNull);
      expect(loaded.isGift, isFalse);
      expect(loaded.fundedByDebt, isFalse);

      final month = const BudgetCalendar().monthOf(
        Tashkent.dateOf(t.clock.nowUtc()),
      );
      expect(await repo.listInRange(hh, month), [e]);
    });

    test('mavjud boʻlmagan kategoriyaga xarajat yozilmaydi (FK)', () async {
      final repo = DriftExpenseRepository(t.db, t.clock);
      expect(
        () => repo.add(
          Expense(
            meta: t.meta.create(hh),
            amount: som(1),
            categoryId: 'yoq',
            channel: PaymentChannel.cash,
            spentAt: t.clock.nowUtc(),
          ),
        ),
        throwsA(isA<Exception>()),
      );
    });

    test('foydalanuvchi kategoriyasi: nom yoki kalit majburiy', () async {
      final repo = DriftCategoryRepository(t.db, t.clock);
      final custom = await repo.add(
        Category(meta: t.meta.create(hh), name: 'Choyxona', sortOrder: 20),
      );
      expect((await repo.findById(custom.meta.id))!.name, 'Choyxona');
      expect(
        () => repo.add(Category(meta: t.meta.create(hh))),
        throwsA(isA<Exception>()),
      );
    });
  });

  group('majburiyatlar va qarzlar', () {
    test('nasiya daftari: faqat SHOP turidagi qarzlar', () async {
      final debts = DriftDebtRepository(t.db, t.clock);
      Debt debt(CreditorType type, String name) => Debt(
        meta: t.meta.create(hh),
        creditorType: type,
        creditorName: name,
        principal: som(500000),
        remaining: som(300000),
        dueDate: LocalDate(2026, 11, 1),
        reason: 'roʻzgʻor',
      );
      final shop = await debts.add(debt(CreditorType.shop, 'Mahalla doʻkoni'));
      await debts.add(debt(CreditorType.bank, 'Bank'));
      final nasiya = await debts.listByCreditorType(hh, CreditorType.shop);
      expect(nasiya, [shop]);
      expect(nasiya.single.dueDate, LocalDate(2026, 11, 1));
    });

    test('qarz summalari bitta valyutada boʻlishi shart', () async {
      final debts = DriftDebtRepository(t.db, t.clock);
      expect(
        () => debts.add(
          Debt(
            meta: t.meta.create(hh),
            creditorType: CreditorType.bank,
            creditorName: 'Bank',
            principal: som(1),
            remaining: Money.major(1, CurrencyCode.usd),
          ),
        ),
        throwsA(isA<CurrencyMismatchException>()),
      );
    });

    test('majburiyat CRUD va kun boʻyicha tartib', () async {
      final repo = DriftObligationRepository(t.db, t.clock);
      Obligation ob(String title, int day) => Obligation(
        meta: t.meta.create(hh),
        title: title,
        kind: ObligationKind.rent,
        amount: som(2000000),
        dayOfMonth: day,
      );
      await repo.add(ob('Ijara', 25));
      await repo.add(ob('Kredit', 5));
      expect((await repo.listActive(hh)).map((o) => o.title), [
        'Kredit',
        'Ijara',
      ]);
      expect(() => repo.add(ob('Xato', 32)), throwsA(isA<Exception>()));
    });
  });

  group('«Kelajagim»: aktivlar, harakatlar, qoida', () {
    late DriftAssetRepository assets;
    late DriftVaultTransactionRepository txs;
    late Asset vault;

    setUp(() async {
      assets = DriftAssetRepository(t.db, t.clock);
      txs = DriftVaultTransactionRepository(t.db, t.clock);
      vault = await assets.add(
        Asset(
          meta: t.meta.create(hh),
          type: AssetType.vault,
          unit: QuantityUnit.minor,
          currency: CurrencyCode.uzs,
          acquiredAt: t.clock.nowUtc(),
        ),
      );
    });

    VaultTransaction tx(
      VaultTransactionType type,
      int major, {
      VaultTransactionReason reason = VaultTransactionReason.manual,
      String? note,
    }) => VaultTransaction(
      meta: t.meta.create(hh),
      vaultAssetId: vault.meta.id,
      type: type,
      amount: som(major),
      reason: reason,
      reasonNote: note,
      occurredAt: t.clock.nowUtc(),
    );

    test(
      'balans = kirimlar − chiqimlar, oʻchirilganlar hisobga olinmaydi',
      () async {
        await txs.add(
          tx(
            VaultTransactionType.deposit,
            1000000,
            reason: VaultTransactionReason.initial,
          ),
        );
        final share = await txs.add(
          tx(
            VaultTransactionType.deposit,
            50000,
            reason: VaultTransactionReason.incomeShare,
          ),
        );
        await txs.add(
          tx(
            VaultTransactionType.withdraw,
            200000,
            reason: VaultTransactionReason.withdrawal,
            note: 'Dori',
          ),
        );
        expect(await txs.balance(vault.meta.id, CurrencyCode.uzs), som(850000));
        await txs.softDelete(share.meta.id);
        expect(await txs.balance(vault.meta.id, CurrencyCode.uzs), som(800000));
        expect(await txs.listForVault(vault.meta.id), hasLength(2));
      },
    );

    test('boʻsh jamgʻarma balansi nol', () async {
      expect(await txs.balance(vault.meta.id, CurrencyCode.uzs), som(0));
    });

    test(
      'pul olish sababsiz yozilmaydi — repository va baza darajasida',
      () async {
        for (final note in [null, '', '   ']) {
          expect(
            () => txs.add(tx(VaultTransactionType.withdraw, 1, note: note)),
            throwsA(
              isA<DomainRuleException>().having(
                (e) => e.code,
                'code',
                DriftVaultTransactionRepository.withdrawReasonRequired,
              ),
            ),
          );
        }
        // Repository chetlab oʻtilsa ham baza CHECK cheklovi toʻxtatadi.
        final raw = tx(VaultTransactionType.withdraw, 1, note: ' ');
        expect(
          () => t.db.into(t.db.vaultTransactions).insert(txs.toRow(raw)),
          throwsA(isA<Exception>()),
        );
      },
    );

    test('summa musbat boʻlishi shart', () {
      expect(
        () => txs.add(tx(VaultTransactionType.deposit, 0)),
        throwsA(isA<DomainRuleException>()),
      );
    });

    test('aktivni turi boʻyicha topish va snapshotlar', () async {
      expect(
        (await assets.findFirstOfType(hh, AssetType.vault))!.meta.id,
        vault.meta.id,
      );
      expect(await assets.findFirstOfType(hh, AssetType.gold), isNull);
      for (final q in [100, 250]) {
        t.clock.advance(const Duration(days: 1));
        await assets.addSnapshot(
          AssetSnapshot(
            meta: t.meta.create(hh),
            assetId: vault.meta.id,
            quantity: q,
            takenAt: t.clock.nowUtc(),
          ),
        );
      }
      expect(
        (await assets.listSnapshots(vault.meta.id)).map((s) => s.quantity),
        [100, 250],
      );
    });

    test('ajratish qoidasi: faol qoida va cheklovlar', () async {
      final rules = DriftAllocationRuleRepository(t.db, t.clock);
      final rule = await rules.add(
        AllocationRule(
          meta: t.meta.create(hh),
          vaultAssetId: vault.meta.id,
          mode: AllocationMode.progressive,
          currency: CurrencyCode.uzs,
          basisPoints: 500,
        ),
      );
      expect(await rules.activeFor(vault.meta.id), rule);

      final fixed = await rules.add(
        AllocationRule(
          meta: t.meta.create(hh),
          vaultAssetId: vault.meta.id,
          mode: AllocationMode.fixed,
          currency: CurrencyCode.uzs,
          fixedAmount: som(300000),
        ),
      );
      await rules.update(rule.copyWith(isActive: false));
      expect(await rules.activeFor(vault.meta.id), fixed);

      expect(
        () => rules.add(
          AllocationRule(
            meta: t.meta.create(hh),
            vaultAssetId: vault.meta.id,
            mode: AllocationMode.fixed,
            currency: CurrencyCode.uzs,
          ),
        ),
        throwsA(isA<Exception>()),
        reason: 'ulush ham, summa ham yoʻq',
      );
      expect(
        () => rules.add(
          AllocationRule(
            meta: t.meta.create(hh),
            vaultAssetId: vault.meta.id,
            mode: AllocationMode.fixed,
            currency: CurrencyCode.uzs,
            basisPoints: 10001,
          ),
        ),
        throwsA(isA<Exception>()),
      );
    });
  });

  group('aʼzolar va kurslar', () {
    test('aʼzolar: egasi birinchi', () async {
      final repo = DriftMemberRepository(t.db, t.clock);
      await repo.add(Member(meta: t.meta.create(hh), displayName: 'Gulnora'));
      t.clock.advance(const Duration(seconds: 1));
      await repo.add(
        Member(meta: t.meta.create(hh), displayName: 'Akmal', isOwner: true),
      );
      expect((await repo.listActive(hh)).map((m) => m.displayName), [
        'Akmal',
        'Gulnora',
      ]);
    });

    test('eng soʻnggi kurs', () async {
      final repo = DriftFxRateRepository(t.db, t.clock);
      StoredFxRate rate(String value, DateTime date) => StoredFxRate(
        meta: t.meta.create(hh),
        rate: FxRate.parse(CurrencyCode.usd, CurrencyCode.uzs, value, date),
      );
      await repo.add(rate('12600', DateTime.utc(2026, 10)));
      final newest = await repo.add(rate('12650.5', DateTime.utc(2026, 10, 5)));
      final latest = await repo.latest(hh, CurrencyCode.usd, CurrencyCode.uzs);
      expect(latest, newest);
      expect(
        await repo.latest(hh, CurrencyCode.eur, CurrencyCode.uzs),
        isNull,
      );
    });
  });

  test('DateTime UTC sifatida millisekund aniqligida saqlanadi', () async {
    final repo = DriftIncomeRepository(t.db, t.clock);
    final at = DateTime.utc(2026, 10, 9, 7, 30, 15, 123);
    final income = await repo.add(
      Income(
        meta: t.meta.create(hh),
        amount: som(1),
        source: IncomeSource.order,
        channel: PaymentChannel.card,
        receivedAt: at,
      ),
    );
    expect((await repo.findById(income.meta.id))!.receivedAt, at);
    final raw = await t.db
        .customSelect('SELECT received_at FROM incomes')
        .getSingle();
    expect(
      raw.read<String>('received_at'),
      contains('2026-10-09T07:30:15.123'),
    );
  });

  test('ID lar UUIDv7', () async {
    final rows = await t.db.select(t.db.categories).get();
    expect(
      rows.every((r) => RegExp(r'^[0-9a-f-]{36}$').hasMatch(r.id)),
      isTrue,
    );
    expect(rows.first.id[14], '7');
    expect(Variable<String>(rows.first.id).value, rows.first.id);
  });
}
