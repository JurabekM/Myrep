import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

Future<void> tapIn(WidgetTester tester, Finder f) async {
  if (f.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      f,
      200,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
  await tester.tap(f);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets("ko'rik ekrani: roziman, e'tiroz, bayonnoma yakunlanadi", (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final s = await env.container.read(agreementServiceProvider.future);
    final acc = await env.container.read(accountabilityServiceProvider.future);
    final today = Tashkent.dateOf(env.clock.nowUtc());
    final a = await s.create(
      type: AgreementType.rent,
      title: 'Doʻkon ijarasi',
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
        AgreementParty(id: 'p2', name: 'Bahodir'),
      ],
      effectiveFrom: today.plusDays(-40),
    );
    await acc.openReview(a);

    env.container
        .read(appRouterProvider)
        .go(AppRoutes.agreementReview(a.meta.id));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('ac-cutoff')), findsOneWidget);
    expect(find.byKey(const Key('ac-review-complete')), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('ac-review-complete')))
          .onPressed,
      isNull,
      reason: 'hamma tomon javob bermagan',
    );

    await tapIn(tester, find.byKey(const Key('ac-ack-agree-p1')));
    await tapIn(tester, find.byKey(const Key('ac-ack-object-p2')));
    await tester.enterText(
      find.byKey(const Key('ac-object-note')),
      'Kassa farqi',
    );
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('ac-object-save')));
    await tapIn(tester, find.byKey(const Key('ac-review-complete')));

    expect(find.byKey(const Key('ac-minutes-share')), findsOneWidget);
    final v = await acc.view(a);
    expect(v.minutes, hasLength(1));
    expect(v.review.isOpen, isFalse);
  });
}
