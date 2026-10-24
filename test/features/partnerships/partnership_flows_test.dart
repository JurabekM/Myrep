import 'dart:async';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/household/presentation/member_views.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/agreements.dart';
import '../../helpers/pump_app.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

Future<void> open(WidgetTester tester, TestEnv env, String route) async {
  env.container
    ..invalidate(partnershipsProvider)
    ..invalidate(partnershipViewProvider);
  unawaited(env.container.read(appRouterProvider).push<void>(route));
  await tester.pumpAndSettle();
}

/// Element ekranda bo'lmasa — ro'yxat boshiga qaytib, pastga aylantirish.
Future<void> reveal(WidgetTester tester, Finder f) async {
  final scrollable = find.byType(Scrollable).first;
  if (f.evaluate().isEmpty) {
    await tester.fling(scrollable, const Offset(0, 3000), 5000);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(f, 200, scrollable: scrollable);
  }
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> tapIn(WidgetTester tester, Finder f) async {
  await reveal(tester, f);
  await tester.tap(f);
  await tester.pumpAndSettle();
}

FilledButton button(WidgetTester tester, String key) =>
    tester.widget<FilledButton>(find.byKey(Key(key)));

/// Barcha imzolovchilar imzolaydi (imzo chizish UI'si qarz testlarida —
/// PNG kodlash soxta vaqtda tugamaydi).
Future<void> signAll(WidgetTester tester, TestEnv env, String id) async {
  final service = await env.container.read(partnershipServiceProvider.future);
  // 9 savolsiz imzolab bo'lmaydi (Vazifa 9A).
  await completeAgreementIn(env.container, AgreementSource.partnership, id);
  env.container.invalidate(partnershipViewProvider(id));
  final v = (await env.container.read(partnershipViewProvider(id).future))!;
  for (final s in v.signers) {
    await service.sign(v.partnership, s, s.name, [1, 2, 3]);
  }
  env.container.invalidate(partnershipViewProvider(id));
  await tester.pumpAndSettle();
}

Future<Partnership> seed(TestEnv env, {required bool meProvider}) async {
  await env.container.read(membersProvider.future);
  final s = await env.container.read(partnershipServiceProvider.future);
  return s.create(
    title: 'Tikuvchilik sexi',
    type: PartnershipType.mudaraba,
    partners: [
      PartnerDraft(
        name: 'Gʻayrat',
        role: PartnerRole.capitalProvider,
        profit: const ProfitShareInput.percent(4000),
        capital: [
          CapitalItem(
            kind: CapitalKind.equipment,
            title: 'Tikuv mashinasi',
            amount: som(30000000),
          ),
        ],
        isMe: meProvider,
      ),
      PartnerDraft(
        name: 'Dilnoza',
        role: PartnerRole.worker,
        profit: const ProfitShareInput.percent(6000),
        isMe: !meProvider,
      ),
    ],
    termMonths: 12,
    reportPeriod: ReportPeriod.monthly,
    endTerms: 'Uskuna egasiga qaytadi',
    disputeTerms: 'Oqsoqol huzurida',
  );
}

void main() {
  testWidgets('usta: kafolatli daromad bloklanadi, shartnoma yaratiladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    await env.container.read(membersProvider.future);
    await open(tester, env, AppRoutes.partnerships);
    await tester.tap(find.byKey(const Key('pn-new')));
    await tester.pumpAndSettle();

    // 1. Tur va rol.
    await tester.enterText(find.byKey(const Key('pn-title')), 'Sex');
    await tester.pump();
    await tester.tap(find.byKey(const Key('pn-type-mudaraba')));
    await tester.tap(find.byKey(const Key('pn-myrole-capitalProvider')));
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('pn-next')));
    // 2. Tomonlar.
    await tester.enterText(find.byKey(const Key('pn-my-name')), 'Gʻayrat');
    await tester.enterText(
      find.byKey(const Key('pn-partner-name')),
      'Dilnoza',
    );
    await tester.pump();
    await tapIn(tester, find.byKey(const Key('pn-next')));
    // 3. Kapital — bo'sh bo'lsa keyingi qadam yo'q.
    await reveal(tester, find.byKey(const Key('pn-next')));
    expect(button(tester, 'pn-next').onPressed, isNull);
    await tapIn(tester, find.byKey(const Key('pn-capital-add-me')));
    await tester.tap(find.byKey(const Key('pn-capital-kind-equipment')));
    await tester.enterText(
      find.byKey(const Key('pn-capital-title')),
      'Tikuv mashinasi',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('pn-capital-ok')));
    await tester.pumpAndSettle();
    for (final k in ['3', '0', '000', '000']) {
      await tester.tap(find.byKey(Key('amount-key-$k')).last);
      await tester.pump();
    }
    await tester.tap(find.byKey(const Key('amount-sheet-done')));
    await tester.pumpAndSettle();
    await tapIn(tester, find.byKey(const Key('pn-next')));

    // 4. Foyda: qat'iy summa va kafolat — «bu sheriklik emas».
    for (final m in ['fixed', 'guaranteed']) {
      await tapIn(tester, find.byKey(Key('pn-profit-$m')));
      expect(find.byKey(const Key('pn-not-partnership')), findsOneWidget);
      await reveal(tester, find.byKey(const Key('pn-next')));
      expect(button(tester, 'pn-next').onPressed, isNull, reason: m);
    }
    await tapIn(tester, find.byKey(const Key('pn-profit-percent')));
    expect(find.byKey(const Key('pn-not-partnership')), findsNothing);
    await tester.enterText(find.byKey(const Key('pn-my-share')), '40');
    await tester.pump();
    expect(find.textContaining('60 %'), findsOneWidget);
    await tapIn(tester, find.byKey(const Key('pn-next')));
    // 5. Shartlar (standart matnlar to'ldirilgan).
    await tapIn(tester, find.byKey(const Key('pn-witness-add')));
    await tester.enterText(find.byKey(const Key('pn-witness-name')), 'Bekzod');
    await tester.tap(find.byKey(const Key('pn-witness-ok')));
    await tester.pumpAndSettle();
    await tapIn(tester, find.byKey(const Key('pn-next')));
    // 6. Ko'rib chiqish.
    expect(find.byKey(const Key('pn-template-pending')), findsOneWidget);
    await tapIn(tester, find.byKey(const Key('pn-create')));

    final list = await env.container.read(partnershipsProvider.future);
    final p = list.single;
    expect(p.status, PartnershipStatus.draft);
    final v = (await env.container.read(
      partnershipViewProvider(p.meta.id).future,
    ))!;
    expect(v.partners.map((x) => x.profitShareBp), [4000, 6000]);
    expect(v.signers, hasLength(3));
    await reveal(tester, find.byKey(const Key('pn-sign-first')));
    expect(find.byKey(const Key('pn-sign-first')), findsOneWidget);
  });

  testWidgets('kapital kirituvchi: imzolar → darvoza yopiq → ongli boshlash', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final p = await seed(env, meProvider: true);
    await open(tester, env, AppRoutes.partnership(p.meta.id));
    await signAll(tester, env, p.meta.id);
    // Imzolangan tomonlarda «Imzolash» tugmasi qolmaydi (qayta imzo yo'q).
    final signed = (await env.container.read(
      partnershipViewProvider(p.meta.id).future,
    ))!;
    for (final s in signed.signers) {
      await reveal(tester, find.byKey(Key('pn-signer-${s.meta.id}')));
      expect(find.byKey(Key('pn-sign-${s.meta.id}')), findsNothing);
    }
    await reveal(tester, find.byKey(const Key('pn-gate')));
    expect(find.byKey(const Key('pn-gate')), findsOneWidget);
    await tapIn(tester, find.byKey(const Key('pn-activate')));
    // Darvoza yopiq — ongli qaror so'raladi.
    expect(find.byKey(const Key('pn-gate-bypass')), findsOneWidget);
    await tester.tap(find.byKey(const Key('pn-gate-bypass')));
    await tester.pumpAndSettle();
    final v = (await env.container.read(
      partnershipViewProvider(p.meta.id).future,
    ))!;
    expect(v.partnership.status, PartnershipStatus.active);

    // O'zgarish — yangi versiya, hamma qayta imzolaydi.
    await tapIn(tester, find.byKey(const Key('pn-amend')));
    await tester.enterText(find.byKey(const Key('pn-amend-term')), '18');
    await tester.tap(find.byKey(const Key('pn-amend-ok')));
    await tester.pumpAndSettle();
    expect(find.text('Shartnoma, 2-versiya'), findsOneWidget);
    expect(find.byKey(const Key('pn-resign')), findsOneWidget);
  });

  testWidgets('kapital qabul qiluvchi: darvoza yoʻq, «qarz emas» va rozilik', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final p = await seed(env, meProvider: false);
    await open(tester, env, AppRoutes.partnership(p.meta.id));
    await signAll(tester, env, p.meta.id);
    await reveal(tester, find.byKey(const Key('pn-receive')));
    expect(find.byKey(const Key('pn-gate')), findsNothing);
    await reveal(tester, find.byKey(const Key('pn-activate')));
    expect(button(tester, 'pn-activate').onPressed, isNull);
    await tapIn(tester, find.byKey(const Key('pn-ack')));
    final owner = (await env.container.read(membersProvider.future)).single;
    await tapIn(tester, find.byKey(Key('pn-consent-${owner.meta.id}')));
    await reveal(tester, find.byKey(const Key('pn-activate')));
    expect(button(tester, 'pn-activate').onPressed, isNotNull);
    await tapIn(tester, find.byKey(const Key('pn-activate')));
    expect(find.byKey(const Key('pn-gate-bypass')), findsNothing);
    final v = (await env.container.read(
      partnershipViewProvider(p.meta.id).future,
    ))!;
    expect(v.partnership.status, PartnershipStatus.active);
  });

  testWidgets('sheriklik sahifasi — FLAG_SECURE (parametrli marshrut)', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final p = await seed(env, meProvider: true);
    final router = env.container.read(appRouterProvider)..go(AppRoutes.content);
    await tester.pumpAndSettle();
    clearInteractions(env.api);
    router.go(AppRoutes.partnership(p.meta.id));
    await tester.pumpAndSettle();
    verify(() => env.api.setSecureFlag(enabled: true)).called(1);
  });
}
