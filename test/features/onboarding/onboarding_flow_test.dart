import 'dart:typed_data';

import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/features/backup/data/backup_providers.dart';
import 'package:baraka_daftari/features/backup/domain/backup_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/lock/domain/lock_status.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/fake_backup_cipher.dart';
import '../../helpers/pump_app.dart';

Future<void> next(WidgetTester tester) async {
  await tester.pump();
  await tester.tap(find.byKey(const Key('ob-next')));
  await tester.pumpAndSettle();
}

void main() {
  group('appRedirect', () {
    final home = Uri.parse(AppRoutes.home);
    test('onboarding tugamagan: hamma yopiq yoʻl → /onboarding', () {
      for (final r in [AppRoutes.home, AppRoutes.vault, AppRoutes.debts]) {
        expect(
          appRedirect(LockStatus.unlocked, r, Uri.parse(r), onboarded: false),
          AppRoutes.onboarding,
          reason: r,
        );
      }
      // Qulf ochilgach ham bosh sahifa emas — onboarding.
      expect(
        appRedirect(
          LockStatus.unlocked,
          AppRoutes.lock,
          Uri.parse(AppRoutes.lock),
          onboarded: false,
        ),
        AppRoutes.onboarding,
      );
      // Onboarding va zaxiradan tiklash ochiq.
      for (final r in AppRoutes.preOnboarding) {
        expect(
          appRedirect(LockStatus.unlocked, r, Uri.parse(r), onboarded: false),
          isNull,
        );
      }
    });

    test('qulf onboarding’dan ustun; tugagach /onboarding → bosh', () {
      expect(
        appRedirect(
          LockStatus.locked,
          AppRoutes.onboarding,
          Uri.parse(AppRoutes.onboarding),
          onboarded: false,
        ),
        startsWith(AppRoutes.lock),
      );
      expect(
        appRedirect(
          LockStatus.unlocked,
          AppRoutes.onboarding,
          Uri.parse(AppRoutes.onboarding),
          onboarded: true,
        ),
        AppRoutes.home,
      );
      expect(
        appRedirect(LockStatus.unlocked, AppRoutes.home, home, onboarded: true),
        isNull,
      );
      // Holat hali oʻqilmagan — faqat qulf qoidasi.
      expect(
        appRedirect(LockStatus.unlocked, AppRoutes.home, home, onboarded: null),
        isNull,
      );
    });
  });

  testWidgets('yangi oʻrnatish: til → oila → daromad → qarz bor → Qarzlar', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester, onboarded: false);
    expect(find.text('2 / 5'), findsOneWidget);
    expect(find.byKey(const Key('ob-restore')), findsOneWidget);

    // Boshqa boʻlimga oʻtib boʻlmaydi.
    env.container.read(appRouterProvider).go(AppRoutes.vault);
    await tester.pumpAndSettle();
    expect(find.text('2 / 5'), findsOneWidget);

    await next(tester);
    expect(find.text('3 / 5'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('ob-owner')), 'Akmal');
    await tester.enterText(find.byKey(const Key('ob-member-name')), 'Zuhra');
    await tester.pump();
    await tester.tap(find.byKey(const Key('ob-member-add')));
    await tester.pumpAndSettle();
    expect(find.text('Zuhra'), findsOneWidget);

    await next(tester);
    expect(find.text('4 / 5'), findsOneWidget);
    // Daromad turi tanlanmaguncha davom etib boʻlmaydi.
    expect(
      tester.widget<FilledButton>(find.byKey(const Key('ob-next'))).onPressed,
      isNull,
    );
    await tester.tap(find.byKey(const Key('ob-income-orders')));
    await next(tester);
    expect(find.text('5 / 5'), findsOneWidget);
    await tester.tap(find.byKey(const Key('ob-debt-yes')));
    await tester.pump();
    expect(find.textContaining('70 %'), findsOneWidget);
    await next(tester);

    expect(find.widgetWithText(AppBar, 'Qarzlar'), findsOneWidget);
    final hh = await DriftHouseholdRepository(env.db, env.clock).current();
    expect(hh.incomeKind, IncomeKind.orders);
    expect(hh.onboardedAt, isNotNull);
    final names = (await env.db.select(env.db.members).get())
        .map((m) => m.displayName)
        .toSet();
    expect(names, {'Akmal', 'Zuhra'});
    verify(
      () => env.reminders.scheduleIncomeReminder(
        IncomeReminderKind.weekly,
        any(),
        'Daromadni yozdingizmi?',
        any(),
        'Daromad eslatmalari',
      ),
    ).called(greaterThanOrEqualTo(1));

    // Bosh sahifa daromad turiga moslashgan.
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    expect(find.text('Buyurtma puli'), findsOneWidget);
  });

  testWidgets('maosh: oylik kuni saqlanadi, qarz yoʻq → bosh sahifa', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester, onboarded: false);
    await next(tester);
    await next(tester);
    await tester.tap(find.byKey(const Key('ob-income-salary')));
    await tester.pumpAndSettle();
    await tapVisible(tester, find.byKey(const Key('ob-salary-day')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('10').last);
    await tester.pumpAndSettle();
    await next(tester);
    await tester.tap(find.byKey(const Key('ob-debt-no')));
    await next(tester);

    expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
    expect(find.text('Maosh'), findsOneWidget);
    final hh = await DriftHouseholdRepository(env.db, env.clock).current();
    expect(hh.monthStartDay, 10);
    expect(hh.incomeKind, IncomeKind.salary);
    verify(
      () => env.reminders.scheduleIncomeReminder(
        IncomeReminderKind.monthly,
        10,
        any(),
        any(),
        any(),
      ),
    ).called(greaterThanOrEqualTo(1));

    // Onboarding qayta ochilmaydi.
    env.container.read(appRouterProvider).go(AppRoutes.onboarding);
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
  });

  testWidgets('zaxira: eksport, oʻzgartirish, import — tiklanadi', (
    tester,
  ) async {
    final saved = <(Uint8List, String)>[];
    Uint8List? picked;
    final env = await pumpBarakaApp(
      tester,
      extraOverrides: [
        backupCipherProvider.overrideWithValue(FakeCipher()),
        backupSaverProvider.overrideWithValue(
          (bytes, name) async => saved.add((bytes, name)),
        ),
        backupPickerProvider.overrideWithValue(() async => picked),
      ],
    );
    await tester.tap(find.byKey(const Key('nav-settings')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('settings-backup')));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppBar, 'Zaxira nusxa'), findsOneWidget);

    Finder exportBtn() => find.byKey(const Key('backup-export'));
    bool exportEnabled() =>
        tester.widget<ButtonStyleButton>(exportBtn()).onPressed != null;

    await tester.enterText(find.byKey(const Key('backup-password')), 'qisqa');
    await tester.enterText(
      find.byKey(const Key('backup-password-repeat')),
      'qisqa',
    );
    await tester.pump();
    expect(exportEnabled(), isFalse);
    await tester.enterText(
      find.byKey(const Key('backup-password')),
      'maxfiy-parol',
    );
    await tester.enterText(
      find.byKey(const Key('backup-password-repeat')),
      'boshqa-parol',
    );
    await tester.pump();
    expect(find.text('Parollar mos emas.'), findsOneWidget);
    expect(exportEnabled(), isFalse);
    await tester.enterText(
      find.byKey(const Key('backup-password-repeat')),
      'maxfiy-parol',
    );
    await tester.pump();
    await tester.tap(exportBtn());
    await tester.pumpAndSettle();
    expect(saved, hasLength(1));
    expect(saved.single.$2, endsWith('.bkd'));

    // Nusxadan keyin oʻzgarish: yangi aʼzo.
    await (await env.container.read(
      householdServiceProvider.future,
    )).addMember('Begona', MemberRole.adult);

    // Notoʻgʻri parol — xato, maʼlumot oʻzgarmaydi.
    picked = saved.single.$1;
    Future<void> importWith(String password) async {
      await tester.tap(find.byKey(const Key('backup-import')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('backup-import-password')),
        password,
      );
      await tester.pump();
      await tester.tap(find.byKey(const Key('backup-import-ok')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('backup-import-confirm')));
      await tester.pumpAndSettle();
    }

    await importWith('boshqa-parol');
    expect(find.text('Parol notoʻgʻri yoki fayl buzilgan.'), findsOneWidget);
    expect(
      (await env.db.select(env.db.members).get()).map((m) => m.displayName),
      contains('Begona'),
    );

    await importWith('maxfiy-parol');
    expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
    expect(find.textContaining('Tiklandi:'), findsOneWidget);
    expect(
      (await env.db.select(env.db.members).get()).map((m) => m.displayName),
      isNot(contains('Begona')),
    );
  });

  testWidgets('yangi telefon: onboarding → «Zaxiradan tiklash» → bosh sahifa', (
    tester,
  ) async {
    Uint8List? picked;
    final env = await pumpBarakaApp(
      tester,
      onboarded: false,
      extraOverrides: [
        backupCipherProvider.overrideWithValue(FakeCipher()),
        backupPickerProvider.overrideWithValue(() async => picked),
      ],
    );
    // Eski telefondagi nusxa: onboarding tugagan, daromad turi — kunlik.
    await env.db.customStatement(
      'UPDATE households SET onboarded_at = created_at, '
      "income_kind = 'dailyCash'",
    );
    picked = await BackupService(
      env.db,
      FakeCipher(),
      env.clock,
    ).export('maxfiy-parol');
    await env.db.customStatement(
      'UPDATE households SET onboarded_at = NULL, income_kind = NULL',
    );

    await tester.tap(find.byKey(const Key('ob-restore')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('backup-import')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('backup-import-password')),
      'maxfiy-parol',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('backup-import-ok')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('backup-import-confirm')));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
    expect(find.text('Bugungi tushum'), findsOneWidget);
  });

  testWidgets('eski foydalanuvchi: sozlamalarda daromad turi tanlanadi', (
    tester,
  ) async {
    // Qurilmada topilgan: migratsiyadan keyin tur `null` — ro'yxat chiqmasdi.
    final env = await pumpBarakaApp(tester);
    expect(find.text('Daromad'), findsOneWidget);
    await tester.tap(find.byKey(const Key('nav-settings')));
    await tester.pumpAndSettle();
    expect(find.text('Tanlang'), findsOneWidget);
    await tester.tap(find.byKey(const Key('settings-income-kind-select')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Buyurtma boʻyicha').last);
    await tester.pumpAndSettle();
    final hh = await DriftHouseholdRepository(env.db, env.clock).current();
    expect(hh.incomeKind, IncomeKind.orders);
    verify(
      () => env.reminders.scheduleIncomeReminder(
        IncomeReminderKind.weekly,
        any(),
        any(),
        any(),
        any(),
      ),
    ).called(1);
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    expect(find.text('Buyurtma puli'), findsOneWidget);
  });
}
