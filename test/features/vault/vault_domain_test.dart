import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/habit.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';
import '../../helpers/pump_app.dart' show testPin;

Money som(int major) => Money.major(major, CurrencyCode.uzs);

/// Toshkent vaqtida berilgan payt → UTC.
DateTime tashkent(int y, int m, int d, [int h = 12, int min = 0]) =>
    DateTime.utc(y, m, d, h, min).subtract(Tashkent.utcOffset);

void main() {
  group('streak — haftalar jumadan (soxta soat bilan)', () {
    const cal = BudgetCalendar();
    // 2026-10-09 — juma.
    HabitStats habit(List<DateTime> at, DateTime now) => computeHabit(
      savingInstants: at,
      calendar: cal,
      today: Tashkent.dateOf(now),
    );

    test('payshanba 23:59 va juma 00:00 — har xil haftalar', () {
      final thu = tashkent(2026, 10, 8, 23, 59);
      final fri = tashkent(2026, 10, 9, 0);
      final s = habit([thu, fri], tashkent(2026, 10, 9, 10));
      expect(s.totalWeeks, 2);
      expect(s.currentStreakWeeks, 2);
      expect(s.thisWeekDone, isTrue);
      expect(s.currentWeek.start, LocalDate(2026, 10, 9));
    });

    test('bir haftadagi bir nechta ajratish bitta hafta hisoblanadi', () {
      final s = habit([
        tashkent(2026, 10, 9),
        tashkent(2026, 10, 12),
        tashkent(2026, 10, 15, 23, 59), // payshanba — hali oʻsha hafta
      ], tashkent(2026, 10, 15, 23, 59));
      expect(s.totalWeeks, 1);
      expect(s.currentStreakWeeks, 1);
    });

    test('joriy hafta hali boʻsh — streak uzilmaydi', () {
      final s = habit([
        tashkent(2026, 9, 25),
        tashkent(2026, 10, 2),
      ], tashkent(2026, 10, 10));
      expect(s.thisWeekDone, isFalse);
      expect(s.currentStreakWeeks, 2);
    });

    test('bir hafta tushib qolsa streak uziladi, jami saqlanadi', () {
      final s = habit([
        tashkent(2026, 9, 18),
        // 25-sentabr haftasi boʻsh
        tashkent(2026, 10, 2),
        tashkent(2026, 10, 9),
      ], tashkent(2026, 10, 9, 18));
      expect(s.currentStreakWeeks, 2);
      expect(s.totalWeeks, 3);
    });

    test('oʻtgan hafta ham boʻsh boʻlsa streak 0', () {
      final s = habit([tashkent(2026, 9, 25)], tashkent(2026, 10, 9, 1));
      expect(s.currentStreakWeeks, 0);
      expect(s.totalWeeks, 1);
    });

    test('UTC va Toshkent: juma 00:30 Toshkent = payshanba 19:30 UTC', () {
      final s = habit([
        DateTime.utc(2026, 10, 8, 19, 30),
      ], DateTime.utc(2026, 10, 8, 20));
      expect(s.currentWeek.start, LocalDate(2026, 10, 9));
      expect(s.thisWeekDone, isTrue);
    });

    test('kelajakdagi yozuvlar hisobga olinmaydi', () {
      final s = habit([tashkent(2026, 10, 20)], tashkent(2026, 10, 9));
      expect(s.totalWeeks, 0);
    });

    test('streakWeeksSince: taklif haftasidan keyingi haftalar', () {
      final at = [
        for (var i = 0; i < 6; i++)
          tashkent(2026, 9, 4).add(Duration(days: 7 * i)),
      ];
      final today = Tashkent.dateOf(tashkent(2026, 10, 9, 18));
      expect(
        streakWeeksSince(
          savingInstants: at,
          calendar: cal,
          today: today,
          since: null,
        ),
        6,
      );
      expect(
        streakWeeksSince(
          savingInstants: at,
          calendar: cal,
          today: today,
          since: tashkent(2026, 9, 19),
        ),
        3,
      );
    });
  });

  group('VaultService', () {
    late TestDb t;
    late VaultService vault;
    late IncomeService incomes;
    late PinService pins;

    setUp(() async {
      t = TestDb.open();
      t.clock.advance(Duration.zero);
      vault = VaultService(
        households: DriftHouseholdRepository(t.db, t.clock),
        assets: DriftAssetRepository(t.db, t.clock),
        transactions: DriftVaultTransactionRepository(t.db, t.clock),
        rules: DriftAllocationRuleRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      incomes = IncomeService(
        households: DriftHouseholdRepository(t.db, t.clock),
        incomes: DriftIncomeRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      pins = PinService(
        store: InMemorySecureBlobStore(),
        hasher: ReferencePinHasher(),
        clock: t.clock,
      );
      await pins.setPin(testPin);
    });

    Future<Income> income(int major) => incomes.add(
      amount: som(major),
      source: IncomeSource.dailyWork,
      channel: PaymentChannel.cash,
    );

    test('birinchi ochilishda jamgʻarma va 5 % qoida yaratiladi', () async {
      final o = await vault.overview();
      expect(o.vault.type, AssetType.vault);
      expect(o.rule.basisPoints, VaultService.defaultBasisPoints);
      expect(o.balance, som(0));
      expect(o.habit.currentStreakWeeks, 0);
      // Ikkinchi chaqiruv yangisini yaratmaydi.
      expect((await vault.overview()).vault.meta.id, o.vault.meta.id);
    });

    group('ulush taklifi (percentOf orqali, double yoʻq)', () {
      test('5 %: 150 000 → 7 500 → 1 000 soʻmgacha yuqoriga = 8 000', () async {
        expect(await vault.suggestShare(await income(150000)), som(8000));
      });

      test('10 %: 8 000 000 → 800 000 (aniq)', () async {
        await vault.updateRule(
          mode: AllocationMode.fixed,
          basisPoints: 1000,
        );
        expect(await vault.suggestShare(await income(8000000)), som(800000));
      });

      test('kichik daromad: butun soʻmgacha, daromaddan oshmaydi', () async {
        expect(await vault.suggestShare(await income(500)), som(25));
        expect(await vault.suggestShare(await income(1)), som(1));
      });

      test('qatʼiy oylik summa: maqsaddan qolgani', () async {
        await vault.updateRule(
          mode: AllocationMode.fixed,
          fixedAmount: som(300000),
        );
        final first = await income(200000);
        expect(await vault.suggestShare(first), som(200000));
        await vault.allocateFromIncome(first, som(200000));
        expect(await vault.suggestShare(await income(500000)), som(100000));
        await vault.depositManual(som(100000));
        expect(await vault.suggestShare(await income(500000)), isNull);
      });

      test('ajratish DEPOSIT sifatida daromadga bogʻlanadi', () async {
        final inc = await income(150000);
        final tx = await vault.allocateFromIncome(inc, som(8000));
        expect(tx.type, VaultTransactionType.deposit);
        expect(tx.reason, VaultTransactionReason.incomeShare);
        expect(tx.incomeId, inc.meta.id);
        expect((await vault.overview()).balance, som(8000));
      });
    });

    group('«avval yigʻilgan pul» — boshlangʻich balans', () {
      test('bir martalik INITIAL DEPOSIT, odatga kirmaydi', () async {
        await vault.setInitialBalance(som(2000000));
        final o = await vault.overview();
        expect(o.balance, som(2000000));
        expect(o.hasInitialBalance, isTrue);
        expect(o.habit.totalWeeks, 0);
        expect(
          () => vault.setInitialBalance(som(1)),
          throwsA(
            isA<DomainRuleException>().having(
              (e) => e.code,
              'code',
              VaultService.errInitialExists,
            ),
          ),
        );
      });
    });

    group('pul olish — PIN va sababsiz boʻlmaydi', () {
      setUp(() => vault.setInitialBalance(som(1000000)));

      Future<PinApproval?> approve([String pin = testPin]) async =>
          (await pins.approve(pin)).$2;

      Matcher rule(String code) => throwsA(
        isA<DomainRuleException>().having((e) => e.code, 'code', code),
      );

      test('sababsiz — rad', () async {
        for (final reason in ['', '   ']) {
          expect(
            () async => vault.withdraw(
              amount: som(1000),
              reason: reason,
              approval: await approve(),
              emergencyConfirmed: true,
            ),
            rule(VaultService.errReasonRequired),
          );
        }
      });

      test('PIN siz yoki notoʻgʻri PIN bilan — rad', () async {
        expect(
          () => vault.withdraw(
            amount: som(1000),
            reason: 'Dori',
            approval: null,
            emergencyConfirmed: true,
          ),
          rule(VaultService.errPinRequired),
        );
        expect(await approve('000001'), isNull);
      });

      test('ruxsat bir martalik va 1 daqiqada eskiradi', () async {
        final a = await approve();
        await vault.withdraw(
          amount: som(1000),
          reason: 'Dori',
          approval: a,
          emergencyConfirmed: true,
        );
        expect(
          () => vault.withdraw(
            amount: som(1000),
            reason: 'Dori',
            approval: a,
            emergencyConfirmed: true,
          ),
          rule(VaultService.errPinRequired),
        );
        final b = await approve();
        t.clock.advance(const Duration(minutes: 1, seconds: 1));
        expect(
          () => vault.withdraw(
            amount: som(1000),
            reason: 'Dori',
            approval: b,
            emergencyConfirmed: true,
          ),
          rule(VaultService.errPinRequired),
        );
      });

      test(
        'qorovul puldan — «favqulodda holatmi?» tasdigʻisiz boʻlmaydi',
        () async {
          expect(
            () async => vault.withdraw(
              amount: som(1000),
              reason: 'Dori',
              approval: await approve(),
            ),
            rule(VaultService.errEmergencyRequired),
          );
        },
      );

      test('balansdan ortiq olib boʻlmaydi', () async {
        expect(
          () async => vault.withdraw(
            amount: som(1000001),
            reason: 'Dori',
            approval: await approve(),
            emergencyConfirmed: true,
          ),
          rule(VaultService.errInsufficient),
        );
      });

      test('toʻgʻri holatda WITHDRAW yoziladi, sabab saqlanadi', () async {
        final tx = await vault.withdraw(
          amount: som(250000),
          reason: '  Bolaning davolanishi ',
          approval: await approve(),
          emergencyConfirmed: true,
        );
        expect(tx.type, VaultTransactionType.withdraw);
        expect(tx.reasonNote, 'Bolaning davolanishi');
        expect((await vault.overview()).balance, som(750000));
      });
    });

    group('progressiv rejim', () {
      Future<void> saveWeekly(int weeks) async {
        for (var i = 0; i < weeks; i++) {
          await vault.depositManual(som(10000));
          t.clock.advance(const Duration(days: 7));
        }
        t.clock.advance(const Duration(days: -7));
      }

      test('4 hafta ketma-ket — +1 % taklifi, 3 hafta — yoʻq', () async {
        await vault.updateRule(
          mode: AllocationMode.progressive,
          basisPoints: 500,
        );
        t.clock.advance(const Duration(days: 7));
        await saveWeekly(3);
        expect((await vault.overview()).progressionOffer, isNull);
        t.clock.advance(const Duration(days: 7));
        await saveWeekly(1);
        expect((await vault.overview()).progressionOffer, 600);
      });

      test(
        'qabul qilinsa ulush oshadi, keyingi taklif yana 4 haftadan keyin',
        () async {
          await vault.updateRule(
            mode: AllocationMode.progressive,
            basisPoints: 500,
          );
          t.clock.advance(const Duration(days: 7));
          await saveWeekly(4);
          final rule = await vault.answerProgression(accept: true);
          expect(rule.basisPoints, 600);
          expect((await vault.overview()).progressionOffer, isNull);
          t.clock.advance(const Duration(days: 7));
          await saveWeekly(4);
          expect((await vault.overview()).progressionOffer, 700);
        },
      );

      test('rad etilsa ulush oʻzgarmaydi', () async {
        await vault.updateRule(
          mode: AllocationMode.progressive,
          basisPoints: 500,
        );
        t.clock.advance(const Duration(days: 7));
        await saveWeekly(4);
        final rule = await vault.answerProgression(accept: false);
        expect(rule.basisPoints, 500);
        expect((await vault.overview()).progressionOffer, isNull);
      });

      test(
        '10 % (maqsad) ga yetgach taklif yoʻq; oddiy rejimda ham yoʻq',
        () async {
          await vault.updateRule(
            mode: AllocationMode.progressive,
            basisPoints: 1000,
          );
          t.clock.advance(const Duration(days: 7));
          await saveWeekly(5);
          expect((await vault.overview()).progressionOffer, isNull);
          await vault.updateRule(mode: AllocationMode.fixed, basisPoints: 500);
          expect((await vault.overview()).progressionOffer, isNull);
        },
      );
    });

    test('notoʻgʻri qoidalar rad etiladi', () {
      for (final call in [
        () => vault.updateRule(mode: AllocationMode.fixed),
        () => vault.updateRule(mode: AllocationMode.fixed, basisPoints: 0),
        () => vault.updateRule(mode: AllocationMode.fixed, basisPoints: 10001),
        () => vault.updateRule(
          mode: AllocationMode.progressive,
          fixedAmount: som(1),
        ),
        () => vault.updateRule(
          mode: AllocationMode.fixed,
          basisPoints: 500,
          fixedAmount: som(1),
        ),
      ]) {
        expect(call, throwsA(isA<DomainRuleException>()));
      }
    });

    test('daromad: oldindan tanlov va oxirgi summalar', () async {
      var d = await incomes.defaults();
      expect(d.source, IncomeSource.dailyWork);
      expect(d.channel, PaymentChannel.cash);
      expect(d.recentAmounts, isEmpty);
      await incomes.add(
        amount: som(150000),
        source: IncomeSource.order,
        channel: PaymentChannel.card,
      );
      t.clock.advance(const Duration(minutes: 1));
      await income(200000);
      t.clock.advance(const Duration(minutes: 1));
      await income(150000);
      d = await incomes.defaults();
      expect(d.source, IncomeSource.dailyWork);
      expect(d.recentAmounts, [som(150000), som(200000)]);
      expect(
        () => incomes.add(
          amount: som(0),
          source: IncomeSource.order,
          channel: PaymentChannel.cash,
        ),
        throwsA(isA<DomainRuleException>()),
      );
    });
  });
}
