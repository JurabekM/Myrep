import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:flutter_test/flutter_test.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

void main() {
  group('zaxira maqsadi (SPEC 2C.3)', () {
    test('3 oy oʻrtachasi × 6; milestone 3 va 6 oy', () {
      final avg = averageMonthlyEssential(
        monthTotals: [som(2400000), som(2600000), som(2500000)],
      );
      expect(avg, som(2500000));
      final r = ReserveStatus(balance: som(3500000), monthlyEssential: avg);
      expect(r.target, som(15000000));
      expect(r.firstMilestone, som(7500000));
      expect(r.monthsTenths, 14, reason: '«1,4 / 6 oy»');
      expect(r.firstMilestoneReached, isFalse);
      expect(r.missing, som(11500000));

      final three = ReserveStatus(balance: som(7500000), monthlyEssential: avg);
      expect(three.monthsTenths, 30);
      expect(three.firstMilestoneReached, isTrue);
      expect(three.isFull, isFalse);

      final full = ReserveStatus(balance: som(16000000), monthlyEssential: avg);
      expect(full.isFull, isTrue);
      expect(full.missing, const Money.zero(CurrencyCode.uzs));
    });

    test('3 oydan kam maʼlumot — taxminiy summa soʻraladi', () {
      expect(
        averageMonthlyEssential(
          monthTotals: [
            som(2000000),
            const Money.zero(CurrencyCode.uzs),
            som(1),
          ],
        ),
        isNull,
        reason: 'boʻsh oy hisobga olinmaydi — 2 oy',
      );
      final est = averageMonthlyEssential(
        monthTotals: [som(2000000)],
        estimate: som(3000000),
      );
      expect(est, som(3000000));
      final unknown = ReserveStatus(balance: som(5000000));
      expect(unknown.needsEstimate, isTrue);
      expect(unknown.target, isNull);
      expect(unknown.monthsTenths, 0);
      expect(unknown.isFull, isFalse);
    });

    test('oʻrtacha butun soʻmgacha yaxlitlanadi', () {
      expect(
        averageMonthlyEssential(
          monthTotals: [som(1000000), som(1000000), som(1000001)],
        ),
        som(1000000),
      );
    });
  });

  group('ulush taqsimoti — avval qorovul', () {
    final reserve = ReserveStatus(
      balance: som(14000000),
      monthlyEssential: som(2500000),
    );

    test('maqsadgacha qorovul, ortgani — oʻsadigan (darvoza ochiq)', () {
      final s = splitShare(
        amount: som(1500000),
        reserve: reserve,
        growthOpen: true,
      );
      expect(s.qorovul, som(1000000));
      expect(s.osadigan, som(500000));
    });

    test('darvoza yopiq yoki maqsad nomaʼlum — hammasi qorovul', () {
      expect(
        splitShare(
          amount: som(1500000),
          reserve: reserve,
          growthOpen: false,
        ).osadigan,
        const Money.zero(CurrencyCode.uzs),
      );
      expect(
        splitShare(
          amount: som(100),
          reserve: ReserveStatus(balance: som(0)),
          growthOpen: true,
        ).qorovul,
        som(100),
      );
    });
  });

  test('qayta toʻldirish rejasi: 6 oyga, 1 000 soʻmgacha yuqoriga', () {
    final p = refillPlan(som(1000000));
    expect(p.months, 6);
    expect(p.monthly, som(167000));
    expect(refillPlan(som(600)).monthly, som(100));
    // Kasrli so'm chiqmaydi: 5 000 / 6 = 833,33 → yuqoriga, butun so'mda 834.
    expect(refillPlan(som(5000)).monthly, som(834));
  });

  group('tayyorgarlik darvozasi — holatlar matritsasi', () {
    final full = ReserveStatus(
      balance: som(15000000),
      monthlyEssential: som(2500000),
    );
    final half = ReserveStatus(
      balance: som(7500000),
      monthlyEssential: som(2500000),
    );
    final unknown = ReserveStatus(balance: som(99000000));
    final cases = <(String, ReserveStatus, bool, bool, bool)>[
      // (nomi, zaxira, qarz tayyor, chetlab oʻtilgan, ochiqmi)
      ('6 oy + qarz yoʻq', full, true, false, true),
      ('6 oy + faol qarz', full, false, false, false),
      ('3 oy + qarz yoʻq', half, true, false, false),
      ('3 oy + faol qarz', half, false, false, false),
      ('maqsad nomaʼlum', unknown, true, false, false),
      ('3 oy, ongli chetlab oʻtilgan', half, true, true, true),
      ('faol qarz, chetlab oʻtilgan', full, false, true, true),
    ];
    for (final (name, reserve, debt, bypass, open) in cases) {
      test(name, () {
        final g = GateState(
          reserve: reserve,
          debtReady: debt,
          bypassed: bypass,
        );
        expect(g.isOpen, open);
        expect(g.ready, reserve.isFull && debt);
      });
    }
  });
}
