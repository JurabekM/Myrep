import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/core/profile.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../support/harness.dart';
import 'main_flow.dart';

void main() {
  testWidgets('asosiy oqim: profil → obyekt → graf → sessiya → o\'lchov → yopish', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);
    final env = TestEnv();
    await runMainFlow(tester, env);
    // Profil qayta ochilganda yuklanadi (qurilma kaliti saqlangan).
    final loaded = await env.io(tester, () => ProfileService(db: env.db, keyStore: env.keys).load());
    expect(loaded?.role, 'LEAD');
    expect(await env.io(tester, () => LocalPrefRepository(env.db).get(LocalPrefRepository.orgId)), loaded?.orgId);
    await env.dispose(tester);
  });
}
