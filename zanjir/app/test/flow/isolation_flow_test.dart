import 'package:flutter_test/flutter_test.dart';

import '../support/harness.dart';
import 'isolation_flow.dart';

void main() {
  testWidgets('ajratish rejasi: qoralama → tasdiqlash → ketma-ket qadamlar → yakunlash', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    await runIsolationFlow(tester, env, demo);
    await env.dispose(tester);
  });
}
