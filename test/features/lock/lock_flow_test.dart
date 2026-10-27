import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/security/security_settings.dart';
import 'package:baraka_daftari/features/lock/domain/lock_status.dart';
import 'package:baraka_daftari/features/lock/presentation/app_lock_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

Finder _appBarTitle(String title) => find.widgetWithText(AppBar, title);

void main() {
  group('birinchi ishga tushirish', () {
    testWidgets('PIN oʻrnatiladi va bosh sahifa ochiladi', (tester) async {
      final env = await pumpBarakaApp(tester, pinSet: false);
      expect(_appBarTitle('PIN kod oʻrnatish'), findsOneWidget);

      await enterPin(tester, '123456');
      await tester.pumpAndSettle();
      expect(find.textContaining('topish oson'), findsOneWidget);

      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(find.text('Kodni yana bir marta kiriting'), findsOneWidget);

      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
      expect(env.store.blobs.containsKey('pin_record'), isTrue);
    });

    testWidgets('tasdiqlash mos kelmasa qaytadan boshlanadi', (tester) async {
      final env = await pumpBarakaApp(tester, pinSet: false);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      await enterPin(tester, '135790');
      await tester.pumpAndSettle();
      expect(find.textContaining('mos kelmadi'), findsOneWidget);
      expect(find.textContaining('6 xonali kod'), findsOneWidget);
      expect(env.store.blobs.containsKey('pin_record'), isFalse);
    });

    testWidgets('biometriya ixtiyoriy yoqiladi', (tester) async {
      final api = stubbedSecurityApi(
        biometric: BiometricAvailability.available,
        biometricOutcome: BiometricOutcome.success,
      );
      final env = await pumpBarakaApp(tester, securityApi: api, pinSet: false);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();

      expect(find.text('Barmoq izi bilan kirish'), findsOneWidget);
      await tester.tap(find.byKey(const Key('biometric-enable')));
      await tester.pumpAndSettle();

      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
      final saved = await SecuritySettingsRepository(env.store).load();
      expect(saved.biometricEnabled, isTrue);
    });

    testWidgets('biometriyani rad etish ham bosh sahifaga olib boradi', (
      tester,
    ) async {
      final api = stubbedSecurityApi(
        biometric: BiometricAvailability.available,
      );
      final env = await pumpBarakaApp(tester, securityApi: api, pinSet: false);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('biometric-later')));
      await tester.pumpAndSettle();

      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
      verifyNever(() => api.authenticate(any(), any(), any()));
      expect(
        (await SecuritySettingsRepository(env.store).load()).biometricEnabled,
        isFalse,
      );
    });
  });

  group('qulf ekrani', () {
    testWidgets('toʻgʻri PIN bilan ochiladi', (tester) async {
      await pumpBarakaApp(tester, unlock: false);
      expect(find.text('PIN kodni kiriting'), findsOneWidget);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
    });

    testWidgets('notoʻgʻri PIN xabari va lockout', (tester) async {
      final env = await pumpBarakaApp(tester, unlock: false);
      await enterPin(tester, '000001');
      await tester.pumpAndSettle();
      expect(find.textContaining('yana 4 ta urinish'), findsOneWidget);

      for (var i = 0; i < 4; i++) {
        await enterPin(tester, '000001');
        await tester.pump();
      }
      expect(
        find.textContaining('Juda koʻp notoʻgʻri urinish'),
        findsOneWidget,
      );
      expect(find.textContaining('00:30'), findsOneWidget);

      // Kutish paytida toʻgʻri PIN ham oʻtmaydi (klaviatura oʻchiq).
      await enterPin(tester, testPin);
      await tester.pump();
      expect(_appBarTitle('Bosh sahifa'), findsNothing);

      env.clock.advance(const Duration(seconds: 31));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();
      expect(find.textContaining('Juda koʻp'), findsNothing);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
    });

    testWidgets('biometriya yoqilgan boʻlsa avtomatik soʻraladi', (
      tester,
    ) async {
      final api = stubbedSecurityApi(
        biometric: BiometricAvailability.available,
        biometricOutcome: BiometricOutcome.success,
      );
      await pumpBarakaApp(
        tester,
        securityApi: api,
        unlock: false,
        settings: const SecuritySettings(biometricEnabled: true),
      );
      await tester.pumpAndSettle();
      verify(() => api.authenticate(any(), any(), any())).called(1);
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
    });

    testWidgets('biometriya bekor qilinsa PIN bilan kirish mumkin', (
      tester,
    ) async {
      final api = stubbedSecurityApi(
        biometric: BiometricAvailability.available,
      );
      await pumpBarakaApp(
        tester,
        securityApi: api,
        unlock: false,
        settings: const SecuritySettings(biometricEnabled: true),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('pin-biometric')), findsOneWidget);
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
    });
  });

  group('fon → qaytish', () {
    testWidgets('timeout (2 daq) dan keyin qulflanadi', (tester) async {
      final env = await pumpBarakaApp(tester);
      env.container.read(appRouterProvider).go(AppRoutes.vault);
      await tester.pumpAndSettle();

      sendToBackground(tester);
      env.clock.advance(const Duration(minutes: 2));
      bringToForeground(tester);
      await tester.pumpAndSettle();

      expect(
        env.container.read(appLockControllerProvider),
        LockStatus.locked,
      );
      expect(find.text('PIN kodni kiriting'), findsOneWidget);

      // Qulf ochilgach oʻsha ekranga qaytiladi.
      await enterPin(tester, testPin);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Kelajagim'), findsOneWidget);
    });

    testWidgets('timeout dan oldin qaytsa qulflanmaydi', (tester) async {
      final env = await pumpBarakaApp(tester);
      sendToBackground(tester);
      env.clock.advance(const Duration(minutes: 1, seconds: 59));
      bringToForeground(tester);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);
    });

    testWidgets('sozlangan timeout ishlatiladi', (tester) async {
      final env = await pumpBarakaApp(
        tester,
        settings: const SecuritySettings(lockTimeoutMinutes: 5),
      );
      sendToBackground(tester);
      env.clock.advance(const Duration(minutes: 3));
      bringToForeground(tester);
      await tester.pumpAndSettle();
      expect(_appBarTitle('Bosh sahifa'), findsOneWidget);

      sendToBackground(tester);
      env.clock.advance(const Duration(minutes: 5));
      bringToForeground(tester);
      await tester.pumpAndSettle();
      expect(find.text('PIN kodni kiriting'), findsOneWidget);
    });
  });

  group('lockRedirect', () {
    Uri u(String s) => Uri.parse(s);

    test('qulflanganda himoyalangan sahifaga kirib boʻlmaydi', () {
      expect(
        lockRedirect(LockStatus.locked, '/vault', u('/vault')),
        '/lock?from=%2Fvault',
      );
      expect(lockRedirect(LockStatus.locked, '/lock', u('/lock')), isNull);
      expect(lockRedirect(LockStatus.loading, '/home', u('/home')), '/lock');
      expect(
        lockRedirect(LockStatus.needsSetup, '/home', u('/home')),
        '/setup',
      );
    });

    test('ochilgach faqat maʼlum ichki marshrutga qaytiladi', () {
      expect(
        lockRedirect(LockStatus.unlocked, '/lock', u('/lock?from=%2Faudit')),
        '/audit',
      );
      expect(
        lockRedirect(
          LockStatus.unlocked,
          '/lock',
          u('/lock?from=https%3A%2F%2Fevil.example'),
        ),
        '/home',
      );
      expect(
        lockRedirect(LockStatus.unlocked, '/lock', u('/lock?from=%2Fsetup')),
        '/home',
      );
      expect(lockRedirect(LockStatus.unlocked, '/home', u('/home')), isNull);
    });
  });
}
