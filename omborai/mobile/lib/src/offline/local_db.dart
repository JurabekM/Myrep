import 'dart:convert';

import 'package:decimal/decimal.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';

/// Mahalliy baza: tovar keshi, qoldiq harakatlari nusxasi, sinxron holati va outbox navbati.
///
/// Qoldiq = serverdan kelgan harakatlar - hali serverga yetmagan (pending/applied) savdolar.
class LocalDb {
  LocalDb._(this._db);

  final Database _db;

  static const _schema = [
    '''CREATE TABLE products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        unit TEXT NOT NULL,
        sale_price INTEGER NOT NULL,
        barcodes TEXT NOT NULL,
        deleted INTEGER NOT NULL DEFAULT 0)''',
    '''CREATE TABLE movements (
        id TEXT PRIMARY KEY,
        store_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        qty TEXT NOT NULL,
        kind TEXT NOT NULL)''',
    'CREATE INDEX movements_store_product ON movements (store_id, product_id)',
    '''CREATE TABLE outbox (
        op_id TEXT PRIMARY KEY,
        op_type TEXT NOT NULL,
        store_id TEXT NOT NULL,
        payload TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        error_title TEXT,
        error_detail TEXT,
        created_at TEXT NOT NULL)''',
    'CREATE TABLE sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL)',
  ];

  /// [path] — fayl yo'li yoki ':memory:'. [password] berilsa, baza SQLCipher (AES-256) bilan shifrlanadi.
  /// [factory] — testda sqflite_common_ffi.
  static Future<LocalDb> open(
    String path, {
    DatabaseFactory? factory,
    String? password,
  }) async {
    Future<void> onCreate(Database db, int _) async {
      for (final statement in _schema) {
        await db.execute(statement);
      }
    }

    final Database db;
    if (password != null) {
      db = await openDatabase(
        path,
        password: password,
        version: 1,
        onCreate: onCreate,
      );
    } else {
      db = await (factory ?? databaseFactory).openDatabase(
        path,
        options: OpenDatabaseOptions(version: 1, onCreate: onCreate),
      );
    }
    return LocalDb._(db);
  }

  Future<void> close() => _db.close();

  // --- tovarlar keshi ------------------------------------------------------

  Future<void> upsertProducts(List<Map<String, dynamic>> products) async {
    final batch = _db.batch();
    for (final p in products) {
      batch.insert('products', {
        'id': p['id'],
        'name': p['name'],
        'unit': p['unit'],
        'sale_price': (p['sale_price'] as num).toInt(),
        'barcodes': jsonEncode(p['barcodes'] ?? const <String>[]),
        'deleted': p['deleted'] == true ? 1 : 0,
      }, conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit(noResult: true);
  }

  Future<Map<String, dynamic>?> productByBarcode(
    String code,
    String storeId,
  ) async {
    final rows = await _db.query('products', where: 'deleted = 0');
    for (final row in rows) {
      final codes = (jsonDecode(row['barcodes'] as String) as List<dynamic>)
          .cast<String>();
      if (codes.contains(code)) return _productMap(row, storeId);
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> searchProducts(
    String query,
    String storeId, {
    int limit = 50,
  }) async {
    final needle = query.trim().toLowerCase();
    final rows = await _db.query(
      'products',
      where: 'deleted = 0',
      orderBy: 'name',
    );
    final found = <Map<String, dynamic>>[];
    for (final row in rows) {
      if (needle.isEmpty ||
          (row['name'] as String).toLowerCase().contains(needle)) {
        found.add(await _productMap(row, storeId));
        if (found.length >= limit) break;
      }
    }
    return found;
  }

  Future<Map<String, dynamic>> _productMap(
    Map<String, Object?> row,
    String storeId,
  ) async {
    final productId = row['id'] as String;
    return {
      'id': productId,
      'name': row['name'],
      'unit': row['unit'],
      'sale_price': row['sale_price'],
      'barcodes': jsonDecode(row['barcodes'] as String),
      'stock_qty': (await balance(storeId, productId)).toString(),
    };
  }

  // --- qoldiq -----------------------------------------------------------------

  Future<Decimal> balance(String storeId, String productId) async {
    final rows = await _db.query(
      'movements',
      columns: ['qty'],
      where: 'store_id = ? AND product_id = ?',
      whereArgs: [storeId, productId],
    );
    var confirmed = Decimal.zero;
    for (final row in rows) {
      confirmed += Decimal.parse(row['qty'] as String);
    }
    return confirmed - await _pendingSold(storeId, productId);
  }

  Future<Decimal> _pendingSold(String storeId, String productId) async {
    final rows = await _db.query(
      'outbox',
      columns: ['payload'],
      where: "op_type = 'sale' AND store_id = ? AND status IN ('pending', 'applied')",
      whereArgs: [storeId],
    );
    var total = Decimal.zero;
    for (final row in rows) {
      final payload =
          jsonDecode(row['payload'] as String) as Map<String, dynamic>;
      for (final item
          in (payload['items'] as List<dynamic>).cast<Map<String, dynamic>>()) {
        if (item['product_id'] == productId) {
          total += Decimal.parse('${item['qty']}');
        }
      }
    }
    return total;
  }

  // --- outbox -------------------------------------------------------------------

  Future<void> enqueueSale(
    String storeId,
    Map<String, dynamic> payload, {
    required String createdAt,
  }) async {
    await _db.insert('outbox', {
      'op_id': payload['id'],
      'op_type': 'sale',
      'store_id': storeId,
      'payload': jsonEncode(payload),
      'created_at': createdAt,
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
  }

  Future<List<PendingOp>> pendingOps({int limit = 100, String? storeId}) async {
    final rows = await _db.query(
      'outbox',
      where: storeId == null
          ? "status = 'pending'"
          : "status = 'pending' AND store_id = ?",
      whereArgs: storeId == null ? null : [storeId],
      orderBy: 'created_at, op_id',
      limit: limit,
    );
    return [
      for (final r in rows)
        PendingOp(
          opId: r['op_id'] as String,
          opType: r['op_type'] as String,
          storeId: r['store_id'] as String,
          payload: jsonDecode(r['payload'] as String) as Map<String, dynamic>,
        ),
    ];
  }

  Future<int> pendingCount() async {
    final rows = await _db.rawQuery(
      "SELECT COUNT(*) AS n FROM outbox WHERE status = 'pending'",
    );
    return rows.first['n'] as int;
  }

  Future<List<Map<String, Object?>>> rejectedOps() =>
      _db.query('outbox', where: "status = 'rejected'", orderBy: 'created_at');

  Future<void> acknowledgeRejected(String opId) => _db.delete(
    'outbox',
    where: "op_id = ? AND status = 'rejected'",
    whereArgs: [opId],
  );

  Future<void> applyPushResults(List<Map<String, dynamic>> results) async {
    await _db.transaction((txn) async {
      for (final result in results) {
        if (result['status'] == 'applied') {
          // Qoldiq harakati pull orqali kelgandan keyin o'chiriladi (applyPull)
          await txn.update(
            'outbox',
            {'status': 'applied'},
            where: "op_id = ? AND status = 'pending'",
            whereArgs: [result['op_id']],
          );
        } else {
          await txn.update(
            'outbox',
            {
              'status': 'rejected',
              'error_title': result['error_title'],
              'error_detail': result['error_detail'],
            },
            where: 'op_id = ?',
            whereArgs: [result['op_id']],
          );
        }
      }
    });
  }

  // --- sinxron holati ------------------------------------------------------------

  Future<String?> getState(String name) async {
    final rows = await _db.query(
      'sync_state',
      where: 'name = ?',
      whereArgs: [name],
    );
    return rows.isEmpty ? null : rows.first['value'] as String;
  }

  Future<void> setState(String name, String value) async {
    await _db.insert('sync_state', {
      'name': name,
      'value': value,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<Map<String, String>> cursors() async {
    final rows = await _db.query('sync_state');
    return {for (final r in rows) r['name'] as String: r['value'] as String};
  }

  Future<void> applyPull(Map<String, dynamic> page) async {
    await _db.transaction((txn) async {
      final products = _maps(page['products']);
      for (final p in products) {
        await txn.insert('products', {
          'id': p['id'],
          'name': p['name'],
          'unit': p['unit'],
          'sale_price': (p['sale_price'] as num).toInt(),
          'barcodes': jsonEncode(p['barcodes'] ?? const <String>[]),
          'deleted': p['deleted'] == true ? 1 : 0,
        }, conflictAlgorithm: ConflictAlgorithm.replace);
      }

      final movements = _maps(page['movements']);
      for (final m in movements) {
        await txn.insert('movements', {
          'id': m['id'],
          'store_id': m['store_id'],
          'product_id': m['product_id'],
          'qty': '${m['qty']}',
          'kind': m['kind'],
        }, conflictAlgorithm: ConflictAlgorithm.ignore);
        final reference = m['reference_id'];
        if (reference != null) {
          // Serverda qo'llangan savdo: navbat yozuvi endi keraksiz
          await txn.delete(
            'outbox',
            where: "op_id = ? AND status = 'applied'",
            whereArgs: [reference],
          );
        }
      }

      final cursors = {
        for (final e in (page['cursors'] as Map).entries)
          '${e.key}': '${e.value}',
      };
      for (final entry in cursors.entries) {
        await txn.insert('sync_state', {
          'name': entry.key,
          'value': entry.value,
        }, conflictAlgorithm: ConflictAlgorithm.replace);
      }
    });
  }
}

/// JSON ro'yxatini `Map<String, dynamic>` lar ro'yxatiga aylantiradi (literal tiplari farq qilsa ham).
List<Map<String, dynamic>> _maps(Object? value) => [
  for (final item in (value as List<dynamic>? ?? const []))
    Map<String, dynamic>.from(item as Map),
];

class PendingOp {
  const PendingOp({
    required this.opId,
    required this.opType,
    required this.storeId,
    required this.payload,
  });

  final String opId;
  final String opType;
  final String storeId;
  final Map<String, dynamic> payload;
}
