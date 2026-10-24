import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/security/integrity/integrity_service.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/fakes.dart';
import '../../helpers/pump_app.dart';

void main() {
  group('FLAG_SECURE marshrut darajasida', () {
    testWidgets('moliyaviy ekranda yoqiladi, boblarda oʻchadi', (tester) async {
      final env = await pumpBarakaApp(tester);
      final api = env.api;
      final router = env.container.read(appRouterProvider);

      // Qulf va bosh sahifa — yoqilgan, ortiqcha chaqiruv yoʻq.
      verify(() => api.setSecureFlag(enabled: true)).called(1);
      verifyNever(() => api.setSecureFlag(enabled: false));

      router.go(AppRoutes.content);
      await tester.pumpAndSettle();
      verify(() => api.setSecureFlag(enabled: false)).called(1);
      router.go(AppRoutes.home);
      await tester.pumpAndSettle();
      verify(() => api.setSecureFlag(enabled: true)).called(1);

      for (final route in [
        AppRoutes.incomeNew,
        AppRoutes.vault,
        AppRoutes.audit,
      ]) {
        router.go(AppRoutes.content);
        await tester.pumpAndSettle();
        router.go(route);
        await tester.pumpAndSettle();
        expect(AppRoutes.secure, contains(route));
      }
      verify(() => api.setSecureFlag(enabled: true)).called(3);
    });

    // Regressiya: qurilmada push qilingan «Boblar» ekrani ham qora chiqqan —
    // `currentConfiguration.uri` asosiy manzilni (/home) bergan.
    testWidgets('bosh sahifadan push qilingan ekranlar ham hisobga olinadi', (
      tester,
    ) async {
      final env = await pumpBarakaApp(tester);
      final api = env.api;
      clearInteractions(api);

      await tapNav(tester, AppRoutes.content);
      await tester.pumpAndSettle();
      verify(() => api.setSecureFlag(enabled: false)).called(1);

      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
      verify(() => api.setSecureFlag(enabled: true)).called(1);

      await tapNav(tester, AppRoutes.vault);
      await tester.pumpAndSettle();
      verifyNever(() => api.setSecureFlag(enabled: false));
    });

    test('barcha moliyaviy marshrutlar himoyalangan, boblar emas', () {
      expect(
        AppRoutes.secure,
        containsAll([
          AppRoutes.lock,
          AppRoutes.pinSetup,
          AppRoutes.home,
          AppRoutes.incomeNew,
          AppRoutes.vault,
          AppRoutes.audit,
        ]),
      );
      expect(AppRoutes.secure, isNot(contains(AppRoutes.content)));
    });
  });

  group('integrity', () {
    IntegritySignals signals({
      bool rooted = false,
      bool emulator = false,
      bool debugger = false,
      bool debuggable = false,
      bool? signatureValid,
    }) => IntegritySignals(
      isRooted: rooted,
      isEmulator: emulator,
      isDebuggerAttached: debugger,
      isDebuggableBuild: debuggable,
      signatureSha256: 'AB',
      isSignatureValid: signatureValid,
    );

    test('signallardan xavflar', () {
      expect(risksFrom(signals(), releaseMode: true), isEmpty);
      expect(risksFrom(signals(debuggable: true), releaseMode: false), isEmpty);
      expect(risksFrom(signals(debuggable: true), releaseMode: true), {
        IntegrityRisk.debuggable,
      });
      expect(
        risksFrom(
          signals(rooted: true, emulator: true, signatureValid: false),
          releaseMode: false,
        ),
        {
          IntegrityRisk.rooted,
          IntegrityRisk.emulator,
          IntegrityRisk.signatureMismatch,
        },
      );
      expect(
        risksFrom(signals(signatureValid: true), releaseMode: true),
        isEmpty,
      );
    });

    testWidgets(
      'ogohlantirish koʻrsatiladi, bloklamaydi va lokal logga yoziladi',
      (tester) async {
        final api = stubbedSecurityApi(
          signals: signals(rooted: true, emulator: true),
        );
        final env = await pumpBarakaApp(
          tester,
          securityApi: api,
          unlock: false,
        );
        expect(find.byKey(const Key('integrity-banner')), findsOneWidget);
        expect(
          find.textContaining('root huquqlari, emulyator'),
          findsOneWidget,
        );

        final log =
            env.container.read(integrityLogProvider) as RecordingIntegrityLog;
        expect(log.entries.single, {
          IntegrityRisk.rooted,
          IntegrityRisk.emulator,
        });

        await tester.tap(find.byKey(const Key('integrity-dismiss')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('integrity-banner')), findsNothing);

        // Ilova bloklanmaydi.
        await enterPin(tester, testPin);
        await tester.pumpAndSettle();
        expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
      },
    );

    testWidgets('sogʻlom qurilmada ogohlantirish yoʻq', (tester) async {
      await pumpBarakaApp(tester, unlock: false);
      expect(find.byKey(const Key('integrity-banner')), findsNothing);
    });

    testWidgets('native xato boʻlsa ilova yiqilmaydi', (tester) async {
      final api = stubbedSecurityApi();
      when(api.getIntegritySignals).thenThrow(Exception('x'));
      await pumpBarakaApp(tester, securityApi: api);
      expect(find.widgetWithText(AppBar, 'Bosh sahifa'), findsOneWidget);
    });
  });
}
