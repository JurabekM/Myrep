import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/partnerships/data/drift_venture_repositories.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

const Map<OfferQuestion, OfferAnswer> safe = {
  OfferQuestion.guaranteed: OfferAnswer.no,
  OfferQuestion.lossShared: OfferAnswer.yes,
  OfferQuestion.realGoods: OfferAnswer.yes,
  OfferQuestion.recruitment: OfferAnswer.no,
  OfferQuestion.pressure: OfferAnswer.no,
  OfferQuestion.writtenContract: OfferAnswer.yes,
  OfferQuestion.exitEasy: OfferAnswer.yes,
  OfferQuestion.license: OfferAnswer.yes,
  OfferQuestion.verifiedInPerson: OfferAnswer.yes,
};

/// «Tez Foyda»: kafolatli foyda, yangi odam, shoshirish, ishni ko'rsatmadi.
const Map<OfferQuestion, OfferAnswer> tezFoyda = {
  OfferQuestion.guaranteed: OfferAnswer.yes,
  OfferQuestion.lossShared: OfferAnswer.no,
  OfferQuestion.realGoods: OfferAnswer.unknown,
  OfferQuestion.recruitment: OfferAnswer.yes,
  OfferQuestion.pressure: OfferAnswer.yes,
  OfferQuestion.writtenContract: OfferAnswer.yes,
  OfferQuestion.exitEasy: OfferAnswer.unknown,
  OfferQuestion.license: OfferAnswer.unknown,
  OfferQuestion.verifiedInPerson: OfferAnswer.no,
};

Future<void> reveal(WidgetTester tester, Finder f) async {
  if (f.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      f,
      200,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  group('besh xavf belgisi (SPEC 2G.1)', () {
    test('ikki sariq belgi bahoni qizilga koʻtaradi', () {
      final one = evaluateOffer({
        ...safe,
        OfferQuestion.pressure: OfferAnswer.yes,
      });
      expect(one.verdict, OfferVerdict.yellow);
      expect(one.level, ScamLevel.caution);

      final two = evaluateOffer({
        ...safe,
        OfferQuestion.pressure: OfferAnswer.yes,
        OfferQuestion.exitEasy: OfferAnswer.no,
      });
      expect(two.signs, [ScamSign.urgency, ScamSign.hardExit]);
      expect(two.level, ScamLevel.flee);
      expect(two.verdict, OfferVerdict.red, reason: 'har biri sariq edi');
    });

    test('«Tez Foyda»: toʻrt belgi, ribo + gʻarar + qimor', () {
      final e = evaluateOffer(tezFoyda);
      expect(e.verdict, OfferVerdict.red);
      expect(e.signs, hasLength(4));
      expect(e.categories, [
        OfferCategory.ribo,
        OfferCategory.gharar,
        OfferCategory.qimor,
      ]);
    });

    test('eski yozuvdagi nomaʼlum savol kodi oʻqishni buzmaydi', () {
      final a = offerAnswersFromJson(
        '{"guaranteed":"yes","futureQuestion":"no","pressure":"maybe"}',
      );
      expect(a, {OfferQuestion.guaranteed: OfferAnswer.yes});
    });
  });

  group('«toʻxta, maslahatlash» (SPEC 2G.6)', () {
    late TestDb t;
    late OfferCheckService s;

    setUp(() {
      t = TestDb.open();
      s = OfferCheckService(
        households: DriftHouseholdRepository(t.db, t.clock),
        checks: DriftOfferCheckRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
    });

    test('summa va vaʼda qilingan stavka saqlanadi', () async {
      final (r, e) = await s.save(
        'Tez Foyda',
        tezFoyda,
        amount: som(10000 * 12650),
        promisedMonthlyBp: 3500,
      );
      expect(e.verdict, OfferVerdict.red);
      final back = (await s.history()).single;
      expect(back.meta.id, r.meta.id);
      expect(back.amount, som(10000 * 12650));
      expect(back.promisedMonthlyBp, 3500);
      expect(back.decision, isNull);
      await expectLater(
        s.save('x', safe, promisedMonthlyBp: -1),
        rule(OfferCheckService.errBadRate),
      );
    });

    test(
      'pul qoʻyish maslahatchisiz va 24 soatdan oldin bloklanadi',
      () async {
        final (r, _) = await s.save('Tez Foyda', tezFoyda);
        await expectLater(
          s.decide(r, OfferDecision.accepted),
          rule(OfferCheckService.errAdvisorRequired),
        );
        await expectLater(
          s.decide(r, OfferDecision.accepted, advisor: 'Shavkat aka'),
          rule(OfferCheckService.errCoolingOff),
        );
        // Keyinga qoldirish darhol mumkin, maslahatchi saqlanadi.
        final later = await s.decide(
          r,
          OfferDecision.postponed,
          advisor: 'Shavkat aka',
        );
        expect(later.decision, OfferDecision.postponed);
        expect(later.advisor, 'Shavkat aka');

        t.clock.advance(const Duration(hours: 23, minutes: 59));
        await expectLater(
          s.decide(r, OfferDecision.accepted),
          rule(OfferCheckService.errCoolingOff),
        );
        t.clock.advance(const Duration(minutes: 1));
        final done = await s.decide(r, OfferDecision.accepted);
        expect(done.decision, OfferDecision.accepted);
        expect(done.advisor, 'Shavkat aka', reason: 'avval yozilgani olinadi');
        expect(done.decidedAt, t.clock.nowUtc());

        await expectLater(
          s.decide(r, OfferDecision.declined),
          rule(OfferCheckService.errDecided),
        );
      },
    );

    test('rad etish darhol, keyin qaror oʻzgarmaydi', () async {
      final (r, _) = await s.save('Tez Foyda', tezFoyda);
      final d = await s.decide(r, OfferDecision.declined);
      expect(d.decision, OfferDecision.declined);
      await expectLater(
        s.decide(r, OfferDecision.postponed),
        rule(OfferCheckService.errDecided),
      );
    });
  });

  testWidgets('taklif ekrani: «Tez Foyda» — qizil, besh belgi, rad etish', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    env.container.read(appRouterProvider).go(AppRoutes.offerCheck);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('offer-verify')), findsOneWidget);

    for (final MapEntry(key: q, value: a) in tezFoyda.entries) {
      await tapIn(tester, find.byKey(Key('offer-${q.name}-${a.name}')));
    }
    await tapIn(tester, find.byKey(const Key('offer-rate')));
    await tester.enterText(find.byKey(const Key('offer-rate')), '35');
    await tester.pumpAndSettle();
    final yearly = find.byKey(const Key('offer-rate-yearly'));
    await reveal(tester, yearly);
    expect(
      find.descendant(of: yearly, matching: find.textContaining('5,2')),
      findsOneWidget,
    );

    await tapIn(tester, find.byKey(const Key('offer-evaluate')));
    expect(find.byKey(const Key('offer-result-red')), findsOneWidget);
    expect(find.byKey(const Key('offer-signs-flee')), findsOneWidget);
    for (final s in [
      ScamSign.guaranteedHighReturn,
      ScamSign.urgency,
      ScamSign.recruitmentIncome,
      ScamSign.noRealBusiness,
    ]) {
      expect(find.byKey(Key('offer-sign-${s.name}')), findsOneWidget);
    }
    expect(find.byKey(const Key('offer-cat-qimor')), findsOneWidget);

    // Pul qo'yish 24 soat va maslahatsiz ochilmaydi.
    final accept = find.byKey(const Key('offer-accept'));
    await reveal(tester, accept);
    expect(tester.widget<OutlinedButton>(accept).onPressed, isNull);
    expect(find.byKey(const Key('offer-accept-wait')), findsOneWidget);

    await tapIn(tester, find.byKey(const Key('offer-decline')));
    final saved = await (await env.container.read(
      offerCheckServiceProvider.future,
    )).history();
    expect(saved.single.decision, OfferDecision.declined);
    expect(saved.single.promisedMonthlyBp, 3500);
  });
}
