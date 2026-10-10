import '../api/api_client.dart';
import 'local_db.dart';

class SyncReport {
  const SyncReport({
    required this.pushed,
    required this.applied,
    required this.rejected,
    required this.pulledProducts,
    required this.pulledMovements,
  });

  final int pushed;
  final int applied;
  final int rejected;
  final int pulledProducts;
  final int pulledMovements;
}

/// Avval navbat yuboriladi (push), keyin o'zgarishlar olinadi (pull).
class SyncService {
  SyncService(this._api, this._db, {this.batchSize = 100});

  final ApiClient _api;
  final LocalDb _db;
  final int batchSize;

  Future<SyncReport> runOnce(String storeId) async {
    final push = await _push();
    final pull = await _pull(storeId);
    return SyncReport(
      pushed: push.$1,
      applied: push.$2,
      rejected: push.$3,
      pulledProducts: pull.$1,
      pulledMovements: pull.$2,
    );
  }

  Future<(int, int, int)> _push() async {
    var total = 0;
    var applied = 0;
    var rejected = 0;
    while (true) {
      final ops = await _db.pendingOps(limit: batchSize);
      if (ops.isEmpty) break;
      final response = await _api.syncPush([
        for (final op in ops)
          {'type': op.opType, 'op_id': op.opId, 'payload': op.payload},
      ]);
      final results = (response['results'] as List<dynamic>)
          .cast<Map<String, dynamic>>();
      await _db.applyPushResults(results);
      total += ops.length;
      applied += results.where((r) => r['status'] == 'applied').length;
      rejected += results.where((r) => r['status'] == 'rejected').length;
      if (ops.length < batchSize) break;
    }
    return (total, applied, rejected);
  }

  Future<(int, int)> _pull(String storeId) async {
    var products = 0;
    var movements = 0;
    while (true) {
      final page = await _api.syncPull(storeId, await _db.cursors());
      await _db.applyPull(page);
      products += (page['products'] as List<dynamic>).length;
      movements += (page['movements'] as List<dynamic>).length;
      if (page['has_more'] != true) break;
    }
    return (products, movements);
  }
}
