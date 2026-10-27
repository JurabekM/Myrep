import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/features/home/presentation/home_slots.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

void main() {
  test(
    'standart kartalar va boʻlimlar tartiblangan, kalitlar takrorlanmaydi',
    () {
      final c = ProviderContainer();
      addTearDown(c.dispose);
      final cards = c.read(homeCardSlotsProvider);
      expect(cards.map((s) => s.id), [
        'quick',
        'due',
        'debtFree',
        'audit',
        'offerCheck',
        'havas',
        'accountability',
        'rescue',
        'weekly-tasks',
      ]);
      final sections = c.read(homeSectionsProvider);
      expect(sections.first.route, AppRoutes.vault);
      expect(sections.map((s) => s.route).toSet(), hasLength(sections.length));
      expect(
        sections.map((s) => s.order).toList(),
        [...sections.map((s) => s.order)]..sort(),
      );
    },
  );

  testWidgets('yangi modul kartasi bosh ekranga order boʻyicha qoʻshiladi', (
    tester,
  ) async {
    await pumpBarakaApp(
      tester,
      extraOverrides: [
        homeCardSlotsProvider.overrideWithValue([
          HomeCardSlot(
            id: 'audit',
            order: 100,
            builder: (_) => const Text('audit-stub'),
          ),
          HomeCardSlot(
            id: 'budget',
            order: 50,
            builder: (_) => const Text('budget-stub'),
          ),
        ]),
      ],
    );
    expect(find.byKey(const Key('home-card-budget')), findsOneWidget);
    expect(find.byKey(const Key('home-card-audit')), findsOneWidget);
    expect(
      tester.getTopLeft(find.text('budget-stub')).dy,
      lessThan(tester.getTopLeft(find.text('audit-stub')).dy),
    );
    expect(find.byKey(const Key('home-weekly-tasks')), findsNothing);
  });
}
