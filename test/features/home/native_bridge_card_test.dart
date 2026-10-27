import 'package:baraka_daftari/app/router/app_router.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

void main() {
  Future<void> openHome(WidgetTester tester, MockSecurityApi api) async {
    final env = await pumpBarakaApp(tester, securityApi: api);
    env.container.read(appRouterProvider).go(AppRoutes.settings);
    await tester.pumpAndSettle();
  }

  testWidgets('native javob bosh sahifada koʻrinadi', (tester) async {
    final api = stubbedSecurityApi();
    when(
      api.ping,
    ).thenAnswer((_) async => NativeInfo(apiVersion: 1, androidSdkInt: 34));
    await openHome(tester, api);
    expect(find.text('Ishlayapti · API v1 · Android SDK 34'), findsOneWidget);
  });

  testWidgets('native xato boʻlsa yiqilmaydi, holat koʻrsatiladi', (
    tester,
  ) async {
    final api = stubbedSecurityApi();
    when(api.ping).thenThrow(PlatformException(code: 'channel-error'));
    await openHome(tester, api);
    expect(find.text('Native qatlam bilan aloqa yoʻq'), findsOneWidget);
  });
}
