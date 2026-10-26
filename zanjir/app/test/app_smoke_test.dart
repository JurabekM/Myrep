import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/app.dart';
import 'package:zanjir_app/theme/tokens.dart';

void main() {
  testWidgets('ilova dark mavzuda ochiladi va ogohlantirish ko\'rinadi', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: ZanjirApp()));
    await tester.pumpAndSettle();

    expect(find.text('Obyektlar'), findsOneWidget);
    expect(find.textContaining('faqat tavsiya beradi'), findsOneWidget);
    expect(find.textContaining('ishlash xavfsiz'), findsNothing);

    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
    final theme = Theme.of(tester.element(find.byWidget(scaffold)));
    expect(theme.brightness, Brightness.dark);
    expect(theme.scaffoldBackgroundColor, ZanjirColors.paper);
  });
}
