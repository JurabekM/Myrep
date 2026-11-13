// Solver unumdorligi: dart run benchmark/solver_bench.dart [tugunlar soni]
// Talab (prompt 5.3/10): 2000 tugun, o'rta Android qurilma — < 500 ms.
import 'package:zanjir_core/zanjir_core.dart';

import '../test/solver/big_graph.dart';

void main(List<String> args) {
  final size = args.isEmpty ? 2000 : int.parse(args.first);
  final big = buildBigGraph(size);
  print('Graf: ${big.graph.nodes.length} tugun, ${big.graph.edges.length} qirra');
  for (final (name, zone) in [('barg', big.leafZone), ('fider', big.feederZone), ('asosiy shina', big.mainBusZone)]) {
    for (var i = 0; i < 3; i++) {
      planIsolation(big.graph, zone);
    }
    final times = <int>[];
    late IsolationResult r;
    for (var i = 0; i < 10; i++) {
      final sw = Stopwatch()..start();
      r = planIsolation(big.graph, zone, earthingSystem: EarthingSystem.tnS);
      times.add(sw.elapsedMicroseconds);
    }
    times.sort();
    final cut = r is IsolationPlan ? '${r.cut.length} apparat, narx ${r.cost}' : 'BLOCKED';
    print(
      '$name: mediana ${(times[5] / 1000).toStringAsFixed(1)} ms, max ${(times.last / 1000).toStringAsFixed(1)} ms — $cut',
    );
  }
}
