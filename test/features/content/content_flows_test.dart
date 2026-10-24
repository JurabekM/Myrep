import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';
import 'content_test.dart' show chapterJson, doc;

Money som(int major) => Money.major(major, CurrencyCode.uzs);

bool taskChecked(WidgetTester tester, String id) =>
    tester.widget<CheckboxListTile>(find.byKey(Key('task-$id')).first).value ??
    false;

Future<void> goHome(WidgetTester tester, TestEnv env) async {
  env.container.read(appRouterProvider).go(AppRoutes.home);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'avtomatik vazifalar: «Kelajagim» ochildi → 1, ulush → 2, audit → 3',
    (tester) async {
      final env = await pumpBarakaApp(tester);
      await tester.scrollUntilVisible(
        find.byKey(const Key('home-weekly-tasks')),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(
        find.text('1-bob. Avval oʻzingga toʻla · 0 / 3 bajarildi'),
        findsOneWidget,
      );
      expect(taskChecked(tester, 'ch01.t1'), isFalse);

      // 1) «Kelajagim» kartasi ochildi.
      await tapNav(tester, AppRoutes.vault);
      await tester.pumpAndSettle();
      await goHome(tester, env);
      expect(taskChecked(tester, 'ch01.t1'), isTrue);
      expect(find.text('ilova oʻzi belgiladi'), findsOneWidget);

      // 2) Daromaddan ulush ajratildi.
      await tester.tap(find.byKey(const Key('home-add-income')));
      await tester.pumpAndSettle();
      for (final k in ['1', '5', '0', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$k')));
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('income-save')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('share-allocate')));
      await tester.pumpAndSettle();
      expect(taskChecked(tester, 'ch01.t2'), isTrue);

      // 3) Oylik audit yakunlandi. (Snackbar pastki tugmalarni toʻsmasin.)
      ScaffoldMessenger.of(
        tester.element(find.byType(Scaffold).first),
      ).hideCurrentSnackBar();
      await tester.pumpAndSettle();
      await tapNav(tester, AppRoutes.audit);
      await tester.pumpAndSettle();
      for (var i = 0; i < 3; i++) {
        await tester.tap(find.byKey(const Key('audit-next')));
        await tester.pumpAndSettle();
      }
      await tester.tap(find.byKey(const Key('audit-finish')));
      await tester.pumpAndSettle();
      // Bosh ekranda kartalar ko'paydi — tepaga qaytib, vazifalar kartasigacha
      // aylantiriladi (audit tugmasi pastda edi).
      await tester.fling(
        find.byType(Scrollable).first,
        const Offset(0, 3000),
        3000,
      );
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.byKey(const Key('task-ch01.t3')),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(taskChecked(tester, 'ch01.t3'), isTrue);
      expect(find.textContaining('3 / 3 bajarildi'), findsOneWidget);

      // Bazada ham saqlangan.
      final week = await (await env.container.read(
        contentServiceProvider.future,
      )).thisWeek();
      expect(week!.done, {'ch01.t1', 'ch01.t2', 'ch01.t3'});
      expect(
        (await (await env.container.read(
          ledgerServiceProvider.future,
        )).homeKpis()).auditDone,
        isTrue,
      );
    },
  );

  testWidgets('qoʻlda belgilash va bekor qilish', (tester) async {
    final env = await pumpBarakaApp(tester);
    env.container.read(appRouterProvider).go(AppRoutes.chapter('ch01'));
    await tester.pumpAndSettle();
    await tapVisible(tester, find.byKey(const Key('task-ch01.t2')));
    await tester.pumpAndSettle();
    expect(taskChecked(tester, 'ch01.t2'), isTrue);
    await tester.tap(find.byKey(const Key('task-ch01.t2')));
    await tester.pumpAndSettle();
    expect(taskChecked(tester, 'ch01.t2'), isFalse);
  });

  group('bob ekrani', () {
    testWidgets(
      'disklеymer, qonun va PENDING diniy blok (debugʻda belgisi bilan)',
      (
        tester,
      ) async {
        final env = await pumpBarakaApp(tester);
        env.container.read(appRouterProvider).go(AppRoutes.chapter('ch01'));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('content-disclaimer')), findsOneWidget);
        expect(
          find.text('Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.'),
          findsOneWidget,
        );
        // Maslahat bloki «Maslahatchi» belgisi bilan (kitob personaji emas).
        expect(find.byKey(const Key('advisor-label')), findsOneWidget);
        expect(find.text('Maslahatchi'), findsOneWidget);
        // Testlar debug rejimida — PENDING blok tekshiruv belgisi bilan.
        await tester.scrollUntilVisible(
          find.byKey(const Key('religious-pending')),
          200,
          scrollable: find.byType(Scrollable).first,
        );
        expect(find.byKey(const Key('religious-pending')), findsOneWidget);
        await tester.scrollUntilVisible(
          find.byKey(const Key('law-text')),
          200,
          scrollable: find.byType(Scrollable).first,
        );
        expect(find.byKey(const Key('law-text')), findsOneWidget);
      },
    );

    testWidgets('release rejimida PENDING diniy blok koʻrinmaydi', (
      tester,
    ) async {
      final env = await pumpBarakaApp(
        tester,
        extraOverrides: [showPendingReligiousProvider.overrideWithValue(false)],
      );
      env.container.read(appRouterProvider).go(AppRoutes.chapter('ch01'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('religious-block')), findsNothing);
      expect(find.textContaining('Diniy matn'), findsNothing);
      await tester.scrollUntilVisible(
        find.byKey(const Key('law-text')),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.byKey(const Key('law-text')), findsOneWidget);
    });
  });

  testWidgets('«Daftar sahifasi» yoziladi va saqlanadi', (tester) async {
    final env = await pumpBarakaApp(tester);
    env.container.read(appRouterProvider).go(AppRoutes.chapter('ch01'));
    await tester.pumpAndSettle();
    await tapVisible(tester, find.byKey(const Key('open-daftar')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('content-disclaimer')), findsOneWidget);
    await tester.enterText(
      find.byKey(const Key('daftar-text')),
      'Har daromadning oʻndan biri — kelajakdagi oʻzimniki.',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('daftar-save')));
    await tester.pumpAndSettle();
    expect(find.text('Daftaringizga yozildi.'), findsOneWidget);
    expect(find.textContaining('Yozilgan'), findsOneWidget);

    final page = await (await env.container.read(
      contentServiceProvider.future,
    )).daftarPage('ch01');
    expect(page!.body, 'Har daromadning oʻndan biri — kelajakdagi oʻzimniki.');
  });

  testWidgets(
    'yangi triggerlar: xarajat yozildi → t1, daftar sahifasi yozildi → t2',
    (tester) async {
      final ch = chapterJson(1);
      final tasks = (ch['weeklyTasks'] as List).cast<Map<String, dynamic>>();
      tasks[0]['autoComplete'] = 'EXPENSE_RECORDED';
      tasks[1]['autoComplete'] = 'DAFTAR_PAGE_WRITTEN';
      final env = await pumpBarakaApp(
        tester,
        extraOverrides: [
          contentSourceProvider.overrideWithValue(() async => doc([ch])),
        ],
      );
      Future<Set<String>> done() async => (await (await env.container.read(
        contentServiceProvider.future,
      )).thisWeek())!.done;

      await tester.tap(find.byKey(const Key('home-add-expense')));
      await tester.pumpAndSettle();
      for (final k in ['4', '5', '000']) {
        await tester.tap(find.byKey(Key('amount-key-$k')).last);
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('category-groceries')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('expense-save')));
      await tester.pumpAndSettle();
      expect(await done(), {'ch01.t1'});

      env.container.read(appRouterProvider).go(AppRoutes.daftar('ch01'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('daftar-text')),
        'Avval oʻzimga toʻlayman.',
      );
      await tester.pump();
      await tester.tap(find.byKey(const Key('daftar-save')));
      await tester.pumpAndSettle();
      expect(await done(), {'ch01.t1', 'ch01.t2'});
    },
  );

  testWidgets('buzuq kontent ilovani yiqitmaydi', (tester) async {
    final env = await pumpBarakaApp(
      tester,
      extraOverrides: [
        contentSourceProvider.overrideWithValue(() async => '{buzuq json'),
      ],
    );
    expect(tester.takeException(), isNull);
    env.container.read(appRouterProvider).go(AppRoutes.content);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('content-error')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('yopiq bob qolgan vazifalar soni bilan, bosib boʻlmaydi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(
      tester,
      extraOverrides: [
        contentSourceProvider.overrideWithValue(
          () async => doc([chapterJson(1), chapterJson(2)]),
        ),
      ],
    );
    env.container.read(appRouterProvider).go(AppRoutes.content);
    await tester.pumpAndSettle();
    expect(
      find.text('Oldingi bobdan yana 2 ta vazifa bajarilsa ochiladi'),
      findsOneWidget,
    );
    expect(
      tester.widget<ListTile>(find.byKey(const Key('chapter-ch02'))).enabled,
      isFalse,
    );
  });

  testWidgets('juma bildirishnomasi bosh ekranda rejalashtiriladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    verify(
      () => env.reminders.scheduleWeekly(
        'Bugun juma — haftalik yakun',
        any(that: contains('vazifalarini')),
        'Haftalik bob',
      ),
    ).called(greaterThanOrEqualTo(1));
  });
}
