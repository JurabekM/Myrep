import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import '../test/flow/isolation_flow.dart';
import '../test/support/harness.dart';

/// Qurilma/emulyatorda: `flutter test integration_test` (CI — Android emulyator jobi).
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('ajratish rejasi oqimi (qurilmada)', (tester) async {
    final (env, demo, _) = await startWithSession(tester);
    await runIsolationFlow(tester, env, demo);
    await env.dispose(tester);
  });
}
