import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

import 'big_graph.dart';

/// Prompt 5.3/10: 2000 tugunli graf o'rta Android qurilmada < 500 ms.
/// Desktop/CI qurilmasi tezroq — bu yerda zaxira bilan 250 ms chegara qo'yilgan.
void main() {
  test('2000 tugunli graf — planIsolation < 250 ms (CI)', () {
    final big = buildBigGraph(2000);
    expect(big.graph.nodes.length, greaterThanOrEqualTo(2000));
    // JIT isishi.
    for (var i = 0; i < 3; i++) {
      planIsolation(big.graph, big.leafZone);
    }
    for (final zone in [big.leafZone, big.feederZone, big.mainBusZone]) {
      final sw = Stopwatch()..start();
      final r = planIsolation(big.graph, zone, earthingSystem: EarthingSystem.tnS);
      sw.stop();
      expect(r, isA<IsolationPlan>());
      expect(sw.elapsedMilliseconds, lessThan(250), reason: 'zona $zone: ${sw.elapsedMilliseconds} ms');
    }
  });
}
