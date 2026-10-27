import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/theme/tokens.dart';

import 'support/harness.dart';

void main() {
  testWidgets('profil yo\'q — kirish ekrani, dark mavzu, ogohlantirish ko\'rinadi', (tester) async {
    final env = TestEnv();
    await tester.pumpWidget(env.app());
    await settle(tester);

    expect(find.text('Kirish'), findsWidgets);
    expect(find.textContaining('faqat tavsiya beradi'), findsOneWidget);
    expect(find.textContaining('ishlash xavfsiz'), findsNothing);
    final theme = Theme.of(tester.element(find.byType(Scaffold).first));
    expect(theme.brightness, Brightness.dark);
    expect(theme.scaffoldBackgroundColor, ZanjirColors.paper);

    // Server manzili sozlanmagan — faqat oflayn profil.
    expect(find.byKey(const Key('login.notConfigured')), findsOneWidget);
    expect(find.byType(TextFormField), findsNothing);
    expect(find.text('Oflayn profil yaratish'), findsOneWidget);
    await env.dispose(tester);
  });
}
