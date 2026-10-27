import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/partnerships/domain/distribution.dart';
import 'package:baraka_daftari/features/partnerships/domain/idea_math.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:flutter_test/flutter_test.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

/// Mudaraba: Gʻayrat — kapital (30 mln, 40 %), Dilnoza — mehnat (60 %).
final mudaraba = [
  DistributionParty(
    role: PartnerRole.capitalProvider,
    shareBp: 4000,
    capital: som(30000000),
  ),
  DistributionParty(role: PartnerRole.worker, shareBp: 6000, capital: som(0)),
];

void main() {
  group('taqsimot (SPEC 2E.1, 2E.3)', () {
    test('mudaraba foyda: ulushlar boʻyicha, yigʻindi aynan sof foyda', () {
      final r = distribute(
        type: PartnershipType.mudaraba,
        parties: mudaraba,
        net: const Money(333333333, uzs),
      );
      expect(r.shares, [
        const Money(133333333, uzs),
        const Money(200000000, uzs),
      ]);
      expect(Money.sum(r.shares, uzs), const Money(333333333, uzs));
      expect(r.buyoutPaid, som(0));
    });

    test('mudaraba zarar: kapital egasida, mehnat egasi — 0', () {
      final r = distribute(
        type: PartnershipType.mudaraba,
        parties: mudaraba,
        net: som(-4000000),
      );
      expect(r.shares, [som(-4000000), som(0)]);
    });

    test('mudaraba zarar, beparvolik — izoh bilan mehnat egasiga', () {
      expect(
        () => distribute(
          type: PartnershipType.mudaraba,
          parties: mudaraba,
          net: som(-4000000),
          negligence: true,
        ),
        throwsA(
          isA<DomainRuleException>().having(
            (e) => e.code,
            'code',
            PartnershipRules.errNegligenceNote,
          ),
        ),
      );
      final r = distribute(
        type: PartnershipType.mudaraba,
        parties: mudaraba,
        net: som(-4000000),
        negligence: true,
        note: 'Mato namlikda saqlangan',
      );
      expect(r.shares, [som(0), som(-4000000)]);
    });

    test('musharaka zarar: kapitalga mutanosib', () {
      final r = distribute(
        type: PartnershipType.musharaka,
        parties: [
          DistributionParty(
            role: PartnerRole.both,
            shareBp: 5000,
            capital: som(20000000),
          ),
          DistributionParty(
            role: PartnerRole.both,
            shareBp: 5000,
            capital: som(10000000),
          ),
        ],
        net: som(-3000000),
      );
      expect(r.shares, [som(-2000000), som(-1000000)]);
      expect(r.buyoutPaid, som(0), reason: 'zararda buyout yoʻq');
    });

    test('buyout bilan foyda: mehnat egasi ulushidan ayirilib, egaga', () {
      final r = distribute(
        type: PartnershipType.mudaraba,
        parties: mudaraba,
        net: som(5000000),
        buyoutDue: som(1000000),
        buyoutRemaining: som(30000000),
      );
      // 40/60: 2 mln va 3 mln; buyout 1 mln: 3 mln → 2 mln, 2 mln → 3 mln.
      expect(r.buyout, [som(1000000), som(-1000000)]);
      expect(r.shares, [som(3000000), som(2000000)]);
      expect(r.buyoutPaid, som(1000000));
      expect(Money.sum(r.shares, uzs), som(5000000));
    });

    test('buyout qolgan ulush va mehnat egasi ulushidan oshmaydi', () {
      final small = distribute(
        type: PartnershipType.mudaraba,
        parties: mudaraba,
        net: som(5000000),
        buyoutDue: som(1000000),
        buyoutRemaining: som(400000),
      );
      expect(small.buyoutPaid, som(400000));
      final poor = distribute(
        type: PartnershipType.mudaraba,
        parties: mudaraba,
        net: som(1000000),
        buyoutDue: som(5000000),
        buyoutRemaining: som(30000000),
      );
      expect(poor.buyoutPaid, som(600000), reason: 'ulushi 600 000');
      expect(poor.shares[1], som(0));
    });
  });

  group('«Hunardan ishga»: payback (SPEC 2E.4)', () {
    // Overlock + bichish stoli + 2 o'ram mato = 8 mln.
    final capex = som(8000000);

    test('CAPEX 8 mln, oyiga 2 mln foyda → 4 oy', () {
      final r = evaluateScenario(
        scenario: IdeaScenario.base,
        capex: capex,
        income: som(6000000),
        expense: som(4000000),
      );
      expect(r.net, som(2000000));
      expect(r.paybackMonths, 4);
    });

    test('uch stsenariy va sheriklikdagi ulush', () {
      final (pess, opt) = defaultScenarioIncomes(som(6000000));
      expect(pess, som(4200000));
      expect(opt, som(7800000));
      final p = evaluateScenario(
        scenario: IdeaScenario.pessimistic,
        capex: capex,
        income: pess,
        expense: som(4000000),
      );
      expect(p.paybackMonths, 40);
      final o = evaluateScenario(
        scenario: IdeaScenario.optimistic,
        capex: capex,
        income: opt,
        expense: som(4000000),
      );
      expect(o.paybackMonths, 3, reason: '8 / 3,8 = 2,1 → 3');
      // Sheriklikda 60 % ulush: oyiga 1,2 mln → 7 oy.
      final shared = evaluateScenario(
        scenario: IdeaScenario.base,
        capex: capex,
        income: som(6000000),
        expense: som(4000000),
        myShareBp: 6000,
      );
      expect(shared.myNet, som(1200000));
      expect(shared.paybackMonths, 7);
    });

    test('zarar yoki nol foyda — qoplanmaydi', () {
      expect(
        evaluateScenario(
          scenario: IdeaScenario.pessimistic,
          capex: capex,
          income: som(3000000),
          expense: som(4000000),
        ).paybackMonths,
        isNull,
      );
      expect(
        evaluateScenario(
          scenario: IdeaScenario.base,
          capex: capex,
          income: som(4000000),
          expense: som(4000000),
        ).paybackMonths,
        isNull,
      );
    });
  });

  group('OfferCheck qaror jadvali (SPEC 2E.5)', () {
    const safe = {
      OfferQuestion.guaranteed: OfferAnswer.no,
      OfferQuestion.lossShared: OfferAnswer.yes,
      OfferQuestion.realGoods: OfferAnswer.yes,
      OfferQuestion.recruitment: OfferAnswer.no,
      OfferQuestion.pressure: OfferAnswer.no,
      OfferQuestion.writtenContract: OfferAnswer.yes,
      // 7-qonun (SPEC 2G.1).
      OfferQuestion.exitEasy: OfferAnswer.yes,
      OfferQuestion.license: OfferAnswer.yes,
      OfferQuestion.verifiedInPerson: OfferAnswer.yes,
    };

    test('hammasi joyida — yashil, bayroq yoʻq', () {
      final e = evaluateOffer(safe);
      expect(e.verdict, OfferVerdict.green);
      expect(e.flags, isEmpty);
    });

    // Har savol: (xavfli javob, kutilgan bayroq).
    const table = <(OfferQuestion, OfferAnswer, OfferVerdict)>[
      (OfferQuestion.guaranteed, OfferAnswer.yes, OfferVerdict.red),
      (OfferQuestion.lossShared, OfferAnswer.no, OfferVerdict.red),
      (OfferQuestion.realGoods, OfferAnswer.no, OfferVerdict.red),
      (OfferQuestion.recruitment, OfferAnswer.yes, OfferVerdict.red),
      (OfferQuestion.pressure, OfferAnswer.yes, OfferVerdict.yellow),
      (OfferQuestion.writtenContract, OfferAnswer.no, OfferVerdict.yellow),
      (OfferQuestion.exitEasy, OfferAnswer.no, OfferVerdict.yellow),
      (OfferQuestion.license, OfferAnswer.no, OfferVerdict.yellow),
      (OfferQuestion.verifiedInPerson, OfferAnswer.no, OfferVerdict.yellow),
    ];
    for (final (q, a, level) in table) {
      test('${q.name} = ${a.name} → ${level.name}', () {
        final e = evaluateOffer({...safe, q: a});
        expect(e.verdict, level);
        expect(e.flags, [OfferFlag(q, level)]);
      });
    }

    test('bilmayman — har savolda sariq bayroq', () {
      for (final q in OfferQuestion.values) {
        final e = evaluateOffer({...safe, q: OfferAnswer.unknown});
        expect(e.verdict, OfferVerdict.yellow, reason: q.name);
        expect(e.flags, [OfferFlag(q, OfferVerdict.yellow)]);
      }
      expect(evaluateOffer({}).flags, hasLength(OfferQuestion.values.length));
    });

    test('qizil sariqdan ustun, hamma bayroqlar izohlanadi', () {
      final e = evaluateOffer({
        ...safe,
        OfferQuestion.guaranteed: OfferAnswer.yes,
        OfferQuestion.pressure: OfferAnswer.yes,
        OfferQuestion.writtenContract: OfferAnswer.no,
      });
      expect(e.verdict, OfferVerdict.red);
      expect(e.flags.map((f) => f.question), [
        OfferQuestion.guaranteed,
        OfferQuestion.pressure,
        OfferQuestion.writtenContract,
      ]);
    });

    test('javoblar JSON orqali saqlanadi', () {
      final json = offerAnswersToJson(safe);
      expect(offerAnswersFromJson(json), safe);
    });
  });
}
