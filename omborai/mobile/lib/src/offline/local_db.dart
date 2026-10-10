import 'dart:convert';

import 'package:decimal/decimal.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../sync/ops.dart' as ops;

/// Lokal baza (SQLCipher, shifrlangan). Barcha ma'lumot MQTT operatsiyalaridan quriladi (docs/sync-mqtt.md).
/// Qoidalar desktop bilan bir xil: qoldiq = movements; tovar LWW; bitta ochiq smena; qaytarish op_id bo'yicha.
class LocalDb {
  LocalDb._(this._db);

  final Database _db;

  static const _schema = [
    '''CREATE TABLE products (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL,
        sale_price INTEGER NOT NULL, cost_price INTEGER NOT NULL DEFAULT 0,
        min_stock TEXT NOT NULL DEFAULT '0', barcodes TEXT NOT NULL DEFAULT '[]',
        deleted INTEGER NOT NULL DEFAULT 0, updated_ts TEXT NOT NULL DEFAULT '')''',
    '''CREATE TABLE movements (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, product_id TEXT NOT NULL,
        qty TEXT NOT NULL, kind TEXT NOT NULL)''',
    'CREATE INDEX movements_store_product ON movements (store_id, product_id)',
    '''CREATE TABLE sales (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, shift_id TEXT, number TEXT NOT NULL,
        status TEXT NOT NULL, total INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE shifts (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, opened_at TEXT NOT NULL,
        opening_cash INTEGER NOT NULL, closed_at TEXT, closing_cash INTEGER, summary TEXT)''',
    '''CREATE TABLE outbox (
        op_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, op TEXT NOT NULL, created_at TEXT NOT NULL)''',
    'CREATE TABLE applied_ops (op_id TEXT PRIMARY KEY)',
    'CREATE TABLE sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL)',
  ];

  /// v2: do'kon ma'lumoti va foydalanuvchilar (serversiz login, MQTT orqali sinxronlanadi).
  static const _schemaV2 = [
    '''CREATE TABLE IF NOT EXISTS store_info (
        store_id TEXT PRIMARY KEY, name TEXT NOT NULL, updated_ts TEXT NOT NULL DEFAULT '')''',
    '''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, login TEXT NOT NULL, name TEXT NOT NULL,
        role TEXT NOT NULL, salt TEXT NOT NULL, pw_hash TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1, updated_ts TEXT NOT NULL DEFAULT '')''',
    'CREATE INDEX IF NOT EXISTS users_store_login ON users (store_id, login)',
  ];

  /// [password] — SQLCipher paroli. [factory] — testda sqflite_common_ffi (shifrsiz).
  static Future<LocalDb> open(
    String path, {
    String? password,
    DatabaseFactory? factory,
  }) async {
    Future<void> onCreate(Database db, int _) async {
      for (final statement in [..._schema, ..._schemaV2]) {
        await db.execute(statement);
      }
    }

    Future<void> onUpgrade(Database db, int from, int _) async {
      if (from < 2) {
        for (final statement in _schemaV2) {
          await db.execute(statement);
        }
      }
    }

    final Database db;
    if (password != null) {
      db = await openDatabase(
        path,
        password: password,
        version: 2,
        onCreate: onCreate,
        onUpgrade: onUpgrade,
      );
    } else {
      db = await (factory ?? databaseFactory).openDatabase(
        path,
        options: OpenDatabaseOptions(
          version: 2,
          onCreate: onCreate,
          onUpgrade: onUpgrade,
        ),
      );
    }
    return LocalDb._(db);
  }

  Future<void> close() => _db.close();

  // --- holat -----------------------------------------------------------------

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

  Future<String> deviceId() async {
    final existing = await getState('device_id');
    if (existing != null) return existing;
    final value = const Uuid().v4();
    await setState('device_id', value);
    return value;
  }

  Future<String> nextReceiptNumber() async {
    final current = int.tryParse(await getState('receipt_seq') ?? '0') ?? 0;
    final next = current + 1;
    await setState('receipt_seq', '$next');
    final id = await deviceId();
    return '${id.substring(0, 4)}-$next';
  }

  // --- navbat -------------------------------------------------------------------

  Future<void> enqueue(Map<String, dynamic> op) async {
    await _db.insert('outbox', {
      'op_id': op['op_id'],
      'store_id': op['store_id'],
      'op': jsonEncode(op),
      'created_at': op['ts'],
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
  }

  Future<List<Map<String, dynamic>>> pendingOps({int limit = 50}) async {
    final rows = await _db.query(
      'outbox',
      orderBy: 'created_at, op_id',
      limit: limit,
    );
    return [
      for (final r in rows)
        jsonDecode(r['op'] as String) as Map<String, dynamic>,
    ];
  }

  Future<int> pendingCount() async {
    final rows = await _db.rawQuery('SELECT COUNT(*) AS n FROM outbox');
    return rows.first['n'] as int;
  }

  Future<void> dropOutbox(String opId) =>
      _db.delete('outbox', where: 'op_id = ?', whereArgs: [opId]);

  // --- o'qish ---------------------------------------------------------------------

  Future<Decimal> balance(String storeId, String productId) async {
    final rows = await _db.query(
      'movements',
      columns: ['qty'],
      where: 'store_id = ? AND product_id = ?',
      whereArgs: [storeId, productId],
    );
    var total = Decimal.zero;
    for (final r in rows) {
      total += Decimal.parse(r['qty'] as String);
    }
    return total;
  }

  Future<Map<String, dynamic>> _productMap(
    Map<String, Object?> row,
    String storeId,
  ) async {
    final id = row['id'] as String;
    return {
      'id': id,
      'name': row['name'],
      'unit': row['unit'],
      'sale_price': row['sale_price'],
      'cost_price': row['cost_price'],
      'min_stock': row['min_stock'],
      'barcodes': jsonDecode(row['barcodes'] as String),
      'stock_qty': (await balance(storeId, id)).toString(),
    };
  }

  Future<Map<String, dynamic>?> getProduct(
    String productId,
    String storeId,
  ) async {
    final rows = await _db.query(
      'products',
      where: 'id = ? AND deleted = 0',
      whereArgs: [productId],
    );
    return rows.isEmpty ? null : _productMap(rows.first, storeId);
  }

  Future<Map<String, dynamic>?> productByBarcode(
    String code,
    String storeId,
  ) async {
    final rows = await _db.query('products', where: 'deleted = 0');
    for (final r in rows) {
      if ((jsonDecode(r['barcodes'] as String) as List).contains(code)) {
        return _productMap(r, storeId);
      }
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
    for (final r in rows) {
      if (needle.isEmpty ||
          (r['name'] as String).toLowerCase().contains(needle)) {
        found.add(await _productMap(r, storeId));
        if (found.length >= limit) break;
      }
    }
    return found;
  }

  /// Katalog (o'chirilganlarsiz), qoldiqsiz — tahrirlash ro'yxati uchun.
  Future<List<Map<String, dynamic>>> allProducts() async {
    final rows = await _db.query(
      'products',
      where: 'deleted = 0',
      orderBy: 'name',
    );
    return [
      for (final r in rows)
        {
          'id': r['id'],
          'name': r['name'],
          'unit': r['unit'],
          'sale_price': r['sale_price'],
          'cost_price': r['cost_price'],
          'min_stock': r['min_stock'],
          'barcodes': jsonDecode(r['barcodes'] as String),
        },
    ];
  }

  Future<Map<String, dynamic>?> openShift(String storeId) async {
    final rows = await _db.query(
      'shifts',
      where: 'store_id = ? AND closed_at IS NULL',
      whereArgs: [storeId],
    );
    return rows.isEmpty ? null : Map<String, dynamic>.from(rows.first);
  }

  Future<List<Map<String, dynamic>>> sales(
    String storeId, {
    int limit = 50,
  }) async {
    final rows = await _db.query(
      'sales',
      where: 'store_id = ?',
      whereArgs: [storeId],
      orderBy: 'created_at DESC',
      limit: limit,
    );
    return [
      for (final r in rows)
        {...r, 'payload': jsonDecode(r['payload'] as String)},
    ];
  }

  Future<Map<String, dynamic>?> getSale(String saleId) async {
    final rows = await _db.query('sales', where: 'id = ?', whereArgs: [saleId]);
    if (rows.isEmpty) return null;
    return {
      ...rows.first,
      'payload': jsonDecode(rows.first['payload'] as String),
    };
  }

  Future<Map<String, dynamic>> shiftSummary(String shiftId) async {
    final rows = await _db.query(
      'sales',
      where: 'shift_id = ?',
      whereArgs: [shiftId],
    );
    final summary = <String, dynamic>{
      'sales_count': 0,
      'total_sales': 0,
      'refunds_count': 0,
      'total_refunds': 0,
      'by_method': <String, int>{},
    };
    final byMethod = summary['by_method'] as Map<String, int>;
    for (final r in rows) {
      if (r['status'] == 'refunded') {
        summary['refunds_count'] = (summary['refunds_count'] as int) + 1;
        summary['total_refunds'] =
            (summary['total_refunds'] as int) + (r['total'] as int);
        continue;
      }
      summary['sales_count'] = (summary['sales_count'] as int) + 1;
      summary['total_sales'] =
          (summary['total_sales'] as int) + (r['total'] as int);
      final payload =
          jsonDecode(r['payload'] as String) as Map<String, dynamic>;
      for (final p in (payload['payments'] as List)) {
        final m = p as Map<String, dynamic>;
        byMethod[m['method'] as String] =
            (byMethod[m['method'] as String] ?? 0) + (m['amount'] as int);
      }
    }
    return summary;
  }

  Future<int> appliedCount() async {
    final rows = await _db.rawQuery('SELECT COUNT(*) AS n FROM applied_ops');
    return rows.first['n'] as int;
  }

  Future<Map<String, dynamic>> snapshotPayload(String storeId) async {
    final products = await _db.query('products');
    final movements = await _db.query(
      'movements',
      where: 'store_id = ?',
      whereArgs: [storeId],
    );
    final shift = await openShift(storeId);
    final info = await _db.query(
      'store_info',
      where: 'store_id = ?',
      whereArgs: [storeId],
    );
    final userRows = await _db.query(
      'users',
      where: 'store_id = ?',
      whereArgs: [storeId],
    );
    final totals = <String, Decimal>{};
    for (final m in movements) {
      final pid = m['product_id'] as String;
      totals[pid] =
          (totals[pid] ?? Decimal.zero) + Decimal.parse(m['qty'] as String);
    }
    return {
      'products': [
        for (final p in products)
          {
            'id': p['id'],
            'name': p['name'],
            'unit': p['unit'],
            'sale_price': p['sale_price'],
            'cost_price': p['cost_price'],
            'min_stock': p['min_stock'],
            'barcodes': jsonDecode(p['barcodes'] as String),
            'deleted': p['deleted'] == 1,
            'updated_ts': p['updated_ts'],
          },
      ],
      'balances': {
        for (final e in totals.entries)
          if (e.value != Decimal.zero) e.key: e.value.toString(),
      },
      'open_shift': shift,
      'store': info.isEmpty
          ? null
          : {
              'name': info.first['name'],
              'updated_ts': info.first['updated_ts'],
            },
      'users': [
        for (final u in userRows)
          {
            'id': u['id'],
            'login': u['login'],
            'name': u['name'],
            'role': u['role'],
            'salt': u['salt'],
            'pw_hash': u['pw_hash'],
            'active': u['active'] == 1,
            'updated_ts': u['updated_ts'],
          },
      ],
    };
  }

  // --- do'kon va foydalanuvchilar ----------------------------------------

  Future<String?> storeName(String storeId) async {
    final rows = await _db.query(
      'store_info',
      columns: ['name'],
      where: 'store_id = ?',
      whereArgs: [storeId],
    );
    return rows.isEmpty ? null : rows.first['name'] as String;
  }

  /// Faol foydalanuvchi (login bo'yicha, katta-kichik harfga bog'liq emas). Xesh va tuz ham qaytadi.
  Future<Map<String, dynamic>?> findUser(String storeId, String login) async {
    final rows = await _db.query(
      'users',
      where: 'store_id = ? AND login = ? AND active = 1',
      whereArgs: [storeId, login.trim().toLowerCase()],
      orderBy: 'updated_ts DESC',
      limit: 1,
    );
    return rows.isEmpty ? null : rows.first;
  }

  Future<Map<String, dynamic>?> getUser(String userId) async {
    final rows = await _db.query('users', where: 'id = ?', whereArgs: [userId]);
    return rows.isEmpty ? null : rows.first;
  }

  /// Login band bo'lsa true (nofaol foydalanuvchilar ham hisobga olinadi).
  Future<bool> loginExists(String storeId, String login) async {
    final rows = await _db.query(
      'users',
      columns: ['id'],
      where: 'store_id = ? AND login = ?',
      whereArgs: [storeId, login.trim().toLowerCase()],
      limit: 1,
    );
    return rows.isNotEmpty;
  }

  Future<List<Map<String, dynamic>>> listUsers(String storeId) => _db.query(
    'users',
    columns: ['id', 'login', 'name', 'role', 'active'],
    where: 'store_id = ?',
    whereArgs: [storeId],
    orderBy: 'name',
  );

  Future<void> _upsertStore(
    DatabaseExecutor txn,
    String storeId,
    String name,
    String ts,
  ) async {
    final rows = await txn.query(
      'store_info',
      columns: ['updated_ts'],
      where: 'store_id = ?',
      whereArgs: [storeId],
    );
    if (rows.isNotEmpty &&
        (rows.first['updated_ts'] as String).compareTo(ts) >= 0) {
      return;
    }
    await txn.insert('store_info', {
      'store_id': storeId,
      'name': name,
      'updated_ts': ts,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// Foydalanuvchi: eng so'nggi o'zgarish g'olib (LWW), tovar kabi.
  Future<void> _upsertUser(
    DatabaseExecutor txn,
    String storeId,
    Map<String, dynamic> u,
    String ts,
  ) async {
    final rows = await txn.query(
      'users',
      columns: ['updated_ts'],
      where: 'id = ?',
      whereArgs: [u['id']],
    );
    if (rows.isNotEmpty &&
        (rows.first['updated_ts'] as String).compareTo(ts) >= 0) {
      return;
    }
    await txn.insert('users', {
      'id': u['id'],
      'store_id': storeId,
      'login': u['login'],
      'name': u['name'],
      'role': u['role'],
      'salt': u['salt'],
      'pw_hash': u['pw_hash'],
      'active': u['active'] == false ? 0 : 1,
      'updated_ts': ts,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  // --- qo'llash -----------------------------------------------------------------------

  /// Operatsiyani bir marta qo'llaydi. Yangi bo'lsa true; dublikat yoki e'tiborsiz bo'lsa false.
  Future<bool> applyOp(Map<String, dynamic> op) async {
    final kind = op['type'] as String;
    if (kind == ops.opSnapshotRequest) return false;
    return _db.transaction((txn) async {
      if (kind == ops.opSnapshot && await _appliedCount(txn) > 0) return false;
      final inserted = await txn.insert('applied_ops', {
        'op_id': op['op_id'],
      }, conflictAlgorithm: ConflictAlgorithm.ignore);
      if (inserted == 0) return false;
      switch (kind) {
        case ops.opSale:
          await _applySale(txn, op);
        case ops.opRefund:
          await _applyRefund(txn, op);
        case ops.opShiftOpen:
          await _applyShiftOpen(txn, op);
        case ops.opShiftClose:
          await _applyShiftClose(txn, op);
        case ops.opMovement:
          final p = op['payload'] as Map<String, dynamic>;
          await _insertMovement(
            txn,
            op['op_id'] as String,
            op['store_id'] as String,
            p['product_id'] as String,
            Decimal.parse('${p['qty']}'),
            p['kind'] as String,
          );
        case ops.opUser:
          await _upsertUser(
            txn,
            op['store_id'] as String,
            op['payload'] as Map<String, dynamic>,
            op['ts'] as String,
          );
        case ops.opStore:
          await _upsertStore(
            txn,
            op['store_id'] as String,
            (op['payload'] as Map<String, dynamic>)['name'] as String,
            op['ts'] as String,
          );
        case ops.opProduct:
          await _upsertProduct(
            txn,
            op['payload'] as Map<String, dynamic>,
            op['ts'] as String,
          );
        case ops.opSnapshot:
          await _applySnapshot(txn, op);
        default:
          throw ArgumentError("Noma'lum operatsiya turi: $kind");
      }
      return true;
    });
  }

  Future<int> _appliedCount(DatabaseExecutor txn) async {
    final rows = await txn.rawQuery('SELECT COUNT(*) AS n FROM applied_ops');
    return rows.first['n'] as int;
  }

  Future<void> _insertMovement(
    DatabaseExecutor txn,
    String id,
    String storeId,
    String productId,
    Decimal qty,
    String kind,
  ) async {
    await txn.insert('movements', {
      'id': id,
      'store_id': storeId,
      'product_id': productId,
      'qty': qty.toString(),
      'kind': kind,
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
  }

  Future<void> _applySale(DatabaseExecutor txn, Map<String, dynamic> op) async {
    final p = op['payload'] as Map<String, dynamic>;
    for (final item in (p['items'] as List)) {
      final i = item as Map<String, dynamic>;
      await _insertMovement(
        txn,
        '${op['op_id']}:${i['product_id']}',
        op['store_id'] as String,
        i['product_id'] as String,
        -Decimal.parse('${i['qty']}'),
        'sale',
      );
    }
    await txn.insert('sales', {
      'id': p['id'],
      'store_id': op['store_id'],
      'shift_id': p['shift_id'],
      'number': '${p['number']}',
      'status': 'completed',
      'total': p['total'],
      'payload': jsonEncode(p),
      'created_at': p['created_at'],
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
  }

  Future<void> _applyRefund(
    DatabaseExecutor txn,
    Map<String, dynamic> op,
  ) async {
    final saleId = (op['payload'] as Map<String, dynamic>)['sale_id'] as String;
    final rows = await txn.query('sales', where: 'id = ?', whereArgs: [saleId]);
    if (rows.isEmpty || rows.first['status'] != 'completed') return;
    final payload =
        jsonDecode(rows.first['payload'] as String) as Map<String, dynamic>;
    for (final item in (payload['items'] as List)) {
      final i = item as Map<String, dynamic>;
      await _insertMovement(
        txn,
        'refund:$saleId:${i['product_id']}',
        op['store_id'] as String,
        i['product_id'] as String,
        Decimal.parse('${i['qty']}'),
        'sale_return',
      );
    }
    await txn.update(
      'sales',
      {'status': 'refunded'},
      where: 'id = ?',
      whereArgs: [saleId],
    );
  }

  Future<void> _applyShiftOpen(
    DatabaseExecutor txn,
    Map<String, dynamic> op,
  ) async {
    final p = op['payload'] as Map<String, dynamic>;
    final open = await txn.query(
      'shifts',
      where: 'store_id = ? AND closed_at IS NULL',
      whereArgs: [op['store_id']],
    );
    if (open.isNotEmpty) return; // ikkinchi ochiq smena e'tiborsiz
    await txn.insert('shifts', {
      'id': p['shift_id'],
      'store_id': op['store_id'],
      'opened_at': op['ts'],
      'opening_cash': p['opening_cash'],
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
  }

  Future<void> _applyShiftClose(
    DatabaseExecutor txn,
    Map<String, dynamic> op,
  ) async {
    final p = op['payload'] as Map<String, dynamic>;
    await txn.update(
      'shifts',
      {
        'closed_at': op['ts'],
        'closing_cash': p['closing_cash'],
        'summary': jsonEncode(p['summary'] ?? {}),
      },
      where: 'id = ? AND closed_at IS NULL',
      whereArgs: [p['shift_id']],
    );
  }

  Future<void> _applySnapshot(
    DatabaseExecutor txn,
    Map<String, dynamic> op,
  ) async {
    final p = op['payload'] as Map<String, dynamic>;
    final store = p['store'] as Map<String, dynamic>?;
    if (store != null) {
      await _upsertStore(
        txn,
        op['store_id'] as String,
        store['name'] as String,
        store['updated_ts'] as String,
      );
    }
    for (final user in (p['users'] as List? ?? const [])) {
      final u = user as Map<String, dynamic>;
      await _upsertUser(
        txn,
        op['store_id'] as String,
        u,
        u['updated_ts'] as String,
      );
    }
    for (final product in (p['products'] as List)) {
      final m = product as Map<String, dynamic>;
      await _upsertProduct(txn, m, m['updated_ts'] as String);
    }
    final balances = p['balances'] as Map<String, dynamic>;
    for (final entry in balances.entries) {
      await _insertMovement(
        txn,
        'snapshot:${op['op_id']}:${entry.key}',
        op['store_id'] as String,
        entry.key,
        Decimal.parse(entry.value as String),
        'snapshot',
      );
    }
    final shift = p['open_shift'] as Map<String, dynamic>?;
    if (shift != null) {
      await txn.insert('shifts', {
        'id': shift['id'],
        'store_id': op['store_id'],
        'opened_at': shift['opened_at'],
        'opening_cash': shift['opening_cash'],
      }, conflictAlgorithm: ConflictAlgorithm.ignore);
    }
  }

  /// Eng so'nggi o'zgarish g'olib: eski ts'li operatsiya yangisini o'chirmaydi.
  Future<void> _upsertProduct(
    DatabaseExecutor txn,
    Map<String, dynamic> p,
    String ts,
  ) async {
    final rows = await txn.query(
      'products',
      columns: ['updated_ts'],
      where: 'id = ?',
      whereArgs: [p['id']],
    );
    if (rows.isNotEmpty &&
        (rows.first['updated_ts'] as String).compareTo(ts) >= 0) {
      return;
    }
    await txn.insert('products', {
      'id': p['id'],
      'name': p['name'],
      'unit': p['unit'],
      'sale_price': (p['sale_price'] as num).toInt(),
      'cost_price': ((p['cost_price'] ?? 0) as num).toInt(),
      'min_stock': '${p['min_stock'] ?? '0'}',
      'barcodes': jsonEncode(p['barcodes'] ?? const <String>[]),
      'deleted': p['deleted'] == true ? 1 : 0,
      'updated_ts': ts,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }
}
