import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/theme/tokens.dart';

import 'support/harness.dart';

void main() {
  testWidgets('profil yo\'q — boshlang\'ich ekran, dark mavzu, ogohlantirish ko\'rinadi', (tester) async {
    final env = TestEnv();
    await tester.pumpWidget(env.app());
    await settle(tester);

    expect(find.text('ZANJIR'), findsWidgets);
    expect(find.textContaining('faqat tavsiya beradi'), findsOneWidget);
    expect(find.textContaining('ishlash xavfsiz'), findsNothing);
    final theme = Theme.of(tester.element(find.byType(Scaffold).first));
    expect(theme.brightness, Brightness.dark);
    expect(theme.scaffoldBackgroundColor, ZanjirColors.paper);

    // Ilova to'liq oflayn (ADR-0017): kirish/parol maydonlari yo'q, faqat oflayn profil.
    expect(find.textContaining('to\'liq oflayn'), findsOneWidget);
    expect(find.byType(TextFormField), findsNothing);
    expect(find.byKey(const Key('start.create')), findsOneWidget);
    await env.dispose(tester);
  });
}
