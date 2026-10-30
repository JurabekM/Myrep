import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';

import '../support/harness.dart';
import 'main_flow.dart';

/// Emulyator/telefon o'lchamidagi ekran: lazy ro'yxatlar va pastki ogohlantirish banneri bilan asosiy oqim
/// (CI `zanjir-emulator` dan oldin shu yerda ushlanadi). Alohida faylda — test holati boshqa testdan o'tmasin.
void main() {
  testWidgets('asosiy oqim kichik ekranda (360×640, emulyator kabi)', (tester) async {
    tester.view.physicalSize = const Size(720, 1280);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(tester.view.reset);
    final env = TestEnv();
    await runMainFlow(tester, env);
    await env.dispose(tester);
  });
}
