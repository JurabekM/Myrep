import 'package:zanjir_data/zanjir_data.dart';

/// Oddiy xotiradagi server: takror `client_op_id`, LWW (`updated_at`, `rev`), append-only, `server_rev`.
/// Haqiqiy server qoidalari (audit zanjiri, RLS) — E2E testda (`test/e2e/`).
class FakeServer implements SyncTransport {
  final rows = <String, Map<String, Object?>>{}; // "table/id" → qator
  final revs = <String, int>{};
  final seenOps = <String>{};
  var rev = 0;
  var pushCalls = 0;

  /// Keyingi push javobini "yo'qotish": server qabul qiladi, mijoz xato oladi.
  bool dropNextResponse = false;
  ServerException? rejectNext;

  void seed(String table, Map<String, Object?> row) {
    rows['$table/${row['id']}'] = row;
    revs['$table/${row['id']}'] = ++rev;
  }

  @override
  Future<Map<String, String>> push(List<Map<String, Object?>> ops) async {
    pushCalls++;
    if (rejectNext != null) {
      final e = rejectNext!;
      rejectNext = null;
      throw e;
    }
    final out = <String, String>{};
    for (final op in ops) {
      final id = op['client_op_id']! as String;
      final table = op['table']! as String;
      final row = (op['row']! as Map).cast<String, Object?>();
      final key = '$table/${row['id']}';
      if (!seenOps.add(id)) {
        out[id] = 'duplicate';
        continue;
      }
      final old = rows[key];
      if (old != null && appendOnlyTables.contains(table)) {
        out[id] = 'duplicate';
      } else if (old != null && !_newer(row, old)) {
        out[id] = 'stale';
      } else {
        rows[key] = row;
        revs[key] = ++rev;
        out[id] = 'applied';
      }
    }
    if (dropNextResponse) {
      dropNextResponse = false;
      throw const ServerException(0, 'timeout');
    }
    return out;
  }

  static bool _newer(Map<String, Object?> a, Map<String, Object?> b) {
    final c = (a['updated_at']! as String).compareTo(b['updated_at']! as String);
    return c > 0 || (c == 0 && (a['rev']! as int) > (b['rev']! as int));
  }

  @override
  Future<PullPage> pull(int since, {int? limit}) async {
    final lim = limit ?? 3;
    final changes = [
      for (final e in revs.entries)
        if (e.value > since) PullChange(e.key.split('/').first, e.value, rows[e.key]!),
    ]..sort((a, b) => a.serverRev.compareTo(b.serverRev));
    final page = changes.take(lim).toList();
    return PullPage(
      changes: page,
      serverRev: page.isEmpty ? since : page.last.serverRev,
      hasMore: changes.length > lim,
    );
  }

  List<Map<String, Object?>> table(String t) => [
    for (final e in rows.entries)
      if (e.key.startsWith('$t/')) e.value,
  ];
}
