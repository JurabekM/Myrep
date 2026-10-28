import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:baraka_daftari/features/learning/data/learning_providers.dart';
import 'package:baraka_daftari/features/learning/domain/course_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> go(WidgetTester tester, TestEnv env, String route) async {
  env.container.read(appRouterProvider).go(route);
  await tester.pumpAndSettle();
}

Future<void> typeAmount(WidgetTester tester, List<String> keys) async {
  for (final k in keys) {
    await tester.tap(find.byKey(Key('amount-key-$k')).last);
    await tester.pump();
  }
}

Future<void> reveal(WidgetTester tester, Finder f) async {
  if (f.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      f,
      200,
      scrollable: find.byType(Scrollable).last,
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
  testWidgets('soat qiymati: daromad va soat → natija, tarixga yoziladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await go(tester, env, AppRoutes.learning);
    expect(find.byKey(const Key('content-disclaimer')), findsOneWidget);
    expect(find.byKey(const Key('ln-goals-need-hourly')), findsOneWidget);
    expect(
      tester.widget<TextButton>(find.byKey(const Key('ln-goal-new'))).onPressed,
      isNull,
    );

    await tapIn(tester, find.byKey(const Key('ln-hourly-open')));
    await tapIn(tester, find.byKey(const Key('ln-income')));
    await typeAmount(tester, ['6', '000', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('ln-hours')), '9');
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ln-hourly-submit')));

    expect(find.byKey(const Key('ln-hourly-result')), findsOneWidget);
    expect(find.byKey(const Key('ln-hourly-feasible-false')), findsOneWidget);
    final s = await env.container.read(learningServiceProvider.future);
    final snap = (await s.latestSnapshot())!;
    expect(snap.minutesPerDay, 540);
    expect(snap.daysPerMonth, 26);
    expect(snap.hourly.minorUnits, 2564103);
  });

  testWidgets('maqsad → kurs yoʻli → tekshiruv (qizil) → tasdiq bilan boshlash '
      '→ «oʻrgatdim»', (tester) async {
    final env = await pumpBarakaApp(tester);
    final s = await env.container.read(learningServiceProvider.future);
    await s.calculate(
      income: som(6000000),
      minutesPerDay: 540,
      daysPerMonth: 26,
    );
    await go(tester, env, AppRoutes.learning);
    expect(find.byKey(const Key('ln-hourly-result')), findsOneWidget);

    await tapIn(tester, find.byKey(const Key('ln-goal-new')));
    await tester.enterText(find.byKey(const Key('ln-goal-title')), 'Excel');
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ln-goal-save')));
    final goal = (await s.goals()).single;
    expect(goal.targetHourly.minorUnits, 5128206);
    expect(find.byKey(const Key('ln-payback-free')), findsOneWidget);

    await tapIn(tester, find.byKey(const Key('ln-item-add')));
    await tapIn(tester, find.byKey(const Key('ln-item-kind-course')));
    await tester.enterText(find.byKey(const Key('ln-item-title')), 'Kurs');
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ln-item-save')));
    // Natija maqsadisiz saqlanmaydi.
    expect(find.byKey(const Key('ln-item-error')), findsOneWidget);
    expect(await s.items(goal.meta.id), isEmpty);

    await tester.enterText(
      find.byKey(const Key('ln-item-purpose')),
      'Oylik hisobotni oʻzim tuzaman',
    );
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ln-item-cost')));
    await typeAmount(tester, ['1', '000', '000']);
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('ln-item-no-debt')), findsOneWidget);
    await tester.enterText(find.byKey(const Key('ln-item-hours')), '10');
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ln-item-save')));

    final item = (await s.items(goal.meta.id)).single;
    expect(item.kind, LearningItemKind.course);
    expect(item.cost, som(1000000));
    expect(item.studyMinutes, 600);
    expect(find.byKey(const Key('ln-payback-months')), findsOneWidget);

    // Kurs tekshiruvi: shoshirish + qaytarish sharti yoʻq → qizil.
    await tapIn(tester, find.byKey(Key('ln-item-menu-${item.meta.id}')));
    await tapIn(tester, find.byKey(const Key('ln-item-action-check')));
    for (final MapEntry(key: q, value: a) in {
      CourseQuestion.incomePromise: OfferAnswer.no,
      CourseQuestion.pressure: OfferAnswer.yes,
      CourseQuestion.referralIncome: OfferAnswer.no,
      CourseQuestion.secretMethod: OfferAnswer.no,
      CourseQuestion.curriculumShown: OfferAnswer.yes,
      CourseQuestion.teacherPractices: OfferAnswer.yes,
      CourseQuestion.refundTerms: OfferAnswer.no,
    }.entries) {
      await tapIn(tester, find.byKey(Key('ln-course-${q.name}-${a.name}')));
    }
    await reveal(tester, find.byKey(const Key('ln-course-result-red')));
    expect(find.byKey(const Key('ln-course-sign-urgency')), findsOneWidget);
    expect(find.byKey(const Key('ln-course-sign-hardExit')), findsOneWidget);
    await tapIn(tester, find.byKey(const Key('ln-course-save')));
    expect(find.byKey(const Key('ln-item-verdict-red')), findsOneWidget);

    // Qizil kursni boshlash — alohida tasdiq bilan.
    await tapIn(tester, find.byKey(Key('ln-item-menu-${item.meta.id}')));
    await tapIn(tester, find.byKey(const Key('ln-item-action-inProgress')));
    await tapIn(tester, find.byKey(const Key('ln-red-confirm')));
    expect(
      (await s.items(goal.meta.id)).single.status,
      LearningItemStatus.inProgress,
    );

    // «Oʻrgatganlarim».
    await go(tester, env, AppRoutes.learning);
    await tapIn(tester, find.byKey(const Key('ln-teach-add')));
    await tester.enterText(find.byKey(const Key('ln-teach-learner')), 'Ukam');
    await tester.enterText(
      find.byKey(const Key('ln-teach-topic')),
      'Jadvalda formula',
    );
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ln-teach-save')));
    final taught = (await s.teachings()).single;
    expect(taught.learner, 'Ukam');
    await reveal(tester, find.byKey(Key('ln-teach-${taught.meta.id}')));
    expect(find.text('Jadvalda formula'), findsOneWidget);
  });

  testWidgets('maqsad oynasi: qisqa yorliq va izoh maydon ostida', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final s = await env.container.read(learningServiceProvider.future);
    await s.calculate(
      income: som(6000000),
      minutesPerDay: 480,
      daysPerMonth: 26,
    );
    await go(tester, env, AppRoutes.learning);
    await tapIn(tester, find.byKey(const Key('ln-goal-new')));
    final why = find.byKey(const Key('ln-goal-why'));
    expect(
      find.descendant(of: why, matching: find.text('Nega aynan shu?')),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: why,
        matching: find.text(
          'Qaysi ishni tezroq, sifatliroq yoki koʻproq odamga qila olasiz?',
        ),
      ),
      findsOneWidget,
    );
  });

  testWidgets('«Tugatdim»: boʻsh natijada oyna ochiq qoladi; qoʻshimcha '
      'taxminan; 45 daqiqa daqiqada', (tester) async {
    final env = await pumpBarakaApp(tester);
    final s = await env.container.read(learningServiceProvider.future);
    await s.calculate(
      income: som(6000000),
      minutesPerDay: 480,
      daysPerMonth: 26,
    );
    final goal = await s.createGoal(title: 'Excel');
    final item = await s.addItem(
      goalId: goal.meta.id,
      kind: LearningItemKind.book,
      title: 'Kitob',
      purpose: 'Hisobotni oʻzim tuzaman',
      cost: som(1500000),
      studyMinutes: 45,
    );
    await s.logTeaching(learner: 'Ukam', topic: 'Formula', minutes: 45);
    await go(tester, env, AppRoutes.learningGoal(goal.meta.id));

    // Hisob umumiy vektorlar bilan bir xil, ekranda esa yaxlitlangan.
    expect((await s.payback(goal))!.monthlyGain.minorUnits, 599999920);
    final gain = tester.widget<Text>(find.byKey(const Key('ln-payback-gain')));
    expect(
      gain.data,
      endsWith('taxminan ${MoneyFormatter.format(som(6000000))}'),
    );
    expect(find.textContaining('45 daqiqa'), findsOneWidget);

    await tapIn(tester, find.byKey(Key('ln-item-menu-${item.meta.id}')));
    await tapIn(tester, find.byKey(const Key('ln-item-action-done')));
    await tester.tap(find.byKey(const Key('ln-item-outcome-save')));
    await tester.pumpAndSettle();
    // Boʻsh natija: oyna yopilmaydi, xato maydon ostida.
    expect(find.byKey(const Key('ln-item-outcome')), findsOneWidget);
    expect(find.text('Erishilgan natijani yozing.'), findsOneWidget);
    expect(
      (await s.items(goal.meta.id)).single.status,
      LearningItemStatus.planned,
    );

    await tester.enterText(
      find.byKey(const Key('ln-item-outcome')),
      'Hisobotni oʻzim tuzdim',
    );
    await tester.pump();
    expect(find.text('Erishilgan natijani yozing.'), findsNothing);
    await tester.tap(find.byKey(const Key('ln-item-outcome-save')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('ln-item-outcome')), findsNothing);
    final done = (await s.items(goal.meta.id)).single;
    expect(done.status, LearningItemStatus.done);
    expect(done.outcome, 'Hisobotni oʻzim tuzdim');

    final taught = (await s.teachings()).single;
    await go(tester, env, AppRoutes.learning);
    await reveal(tester, find.byKey(Key('ln-teach-${taught.meta.id}')));
    expect(
      find.descendant(
        of: find.byKey(Key('ln-teach-${taught.meta.id}')),
        matching: find.textContaining('45 daqiqa'),
      ),
      findsOneWidget,
    );
  });
}
