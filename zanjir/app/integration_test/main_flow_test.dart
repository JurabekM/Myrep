import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import '../test/flow/main_flow.dart';
import '../test/support/harness.dart';

/// Qurilma/emulyatorda: `flutter test integration_test` (CI — Android emulyator jobi).
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('asosiy oqim (qurilmada)', (tester) async {
    final env = TestEnv();
    await runMainFlow(tester, env);
    await env.dispose(tester);
  });
}
