import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

/// Hunar shabloni (SPEC 2G.8): temirchilik ustaxonasi — CAPEX nomlari
/// tavsiya qilinadi, summani foydalanuvchi yozadi.
void main() {
  testWidgets(
    'temirchilik shabloni: tavsiya bosilsa, narx yozilib qoʻshiladi',
    (
      tester,
    ) async {
      final env = await pumpBarakaApp(tester);
      env.container.read(appRouterProvider).go(AppRoutes.ideaNew);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('capex-suggest-0')), findsNothing);

      await tester.tap(find.byKey(const Key('idea-tpl-workshop')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('capex-suggest-0')), findsOneWidget);
      expect(find.textContaining('Talab bormi'), findsOneWidget);

      await tester.tap(find.byKey(const Key('capex-suggest-0')));
      await tester.pumpAndSettle();
      for (final k in '4500000'.split('')) {
        await tester.tap(find.byKey(Key('amount-key-$k')).last);
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('amount-sheet-done')));
      await tester.pumpAndSettle();

      expect(find.text('Payvand apparati'), findsWidgets);
      final added = tester.widget<ActionChip>(
        find.byKey(const Key('capex-suggest-0')),
      );
      expect(added.onPressed, isNull, reason: 'bir xil band ikki marta yoʻq');
    },
  );
}
