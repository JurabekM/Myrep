import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/app/widgets/paged_list.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('PagedList: 30 tadan quriladi, «Yana koʻrsatish» qoʻshadi', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('uz'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: ListView(
            children: [
              PagedList(
                count: 70,
                itemBuilder: (context, i) => Text('qator $i'),
              ),
            ],
          ),
        ),
      ),
    );
    expect(find.text('qator 29', skipOffstage: false), findsOneWidget);
    expect(find.text('qator 30', skipOffstage: false), findsNothing);
    expect(find.text('Yana koʻrsatish (40)', skipOffstage: false), findsOne);

    await tester.ensureVisible(find.byKey(const Key('paged-more')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('paged-more')));
    await tester.pump();
    expect(find.text('qator 59', skipOffstage: false), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('paged-more')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('paged-more')));
    await tester.pump();
    expect(find.text('qator 69', skipOffstage: false), findsOneWidget);
    expect(find.byKey(const Key('paged-more')), findsNothing);
  });
}
