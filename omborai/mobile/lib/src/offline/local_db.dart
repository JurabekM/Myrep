import 'dart:convert';

import 'package:decimal/decimal.dart';
import 'package:sqflite_sqlcipher/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../money.dart';
import '../sync/crypto.dart';
import '../sync/ops.dart' as ops;

/// Lokal baza (SQLCipher, shifrlangan), protokol v2. Desktop `offline/store.py` bilan bir xil qoidalar
/// (docs/sync-mqtt.md): imzo -> muallif faolligi -> ruxsat -> tekshiruv -> qo'llash.
/// Natija: ops.resultApplied / ops.resultDuplicate / ops.resultRejected / ops.resultPending / ops.resultSkipped.
class LocalDb {
  LocalDb._(this._db);

  final Database _db;

  static const maxDeferred = 5000;

  static const _schema = [
    '''CREATE TABLE products (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL,
        sale_price INTEGER NOT NULL, cost_price INTEGER NOT NULL DEFAULT 0,
        min_stock TEXT NOT NULL DEFAULT '0', barcodes TEXT NOT NULL DEFAULT '[]',
        deleted INTEGER NOT NULL DEFAULT 0, updated_ts TEXT NOT NULL DEFAULT '',
        updated_op TEXT NOT NULL DEFAULT '')''',
    '''CREATE TABLE product_prices (
        product_id TEXT NOT NULL, ts TEXT NOT NULL, op_id TEXT NOT NULL,
        sale_price INTEGER NOT NULL, PRIMARY KEY (product_id, ts, op_id))''',
    '''CREATE TABLE movements (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, product_id TEXT NOT NULL,
        qty TEXT NOT NULL, kind TEXT NOT NULL)''',
    'CREATE INDEX movements_store_product ON movements (store_id, product_id)',
    '''CREATE TABLE sales (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, shift_id TEXT, number TEXT NOT NULL,
        status TEXT NOT NULL, total INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE refunded_sales (
        sale_id TEXT PRIMARY KEY, op_id TEXT NOT NULL, ts TEXT NOT NULL)''',
    '''CREATE TABLE shifts (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, device TEXT NOT NULL, opened_at TEXT NOT NULL,
        opening_cash INTEGER NOT NULL, closed_at TEXT, closing_cash INTEGER, summary TEXT)''',
    'CREATE INDEX shifts_device ON shifts (device, closed_at)',
    '''CREATE TABLE outbox (
        op_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, op TEXT NOT NULL, created_at TEXT NOT NULL)''',
    '''CREATE TABLE deferred (
        op_id TEXT PRIMARY KEY, ts TEXT NOT NULL, op TEXT NOT NULL)''',
    'CREATE TABLE applied_ops (op_id TEXT PRIMARY KEY)',
    '''CREATE TABLE devices (
        device_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, public_key TEXT NOT NULL,
        role TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
        updated_ts TEXT NOT NULL DEFAULT '', updated_op TEXT NOT NULL DEFAULT '')''',
    '''CREATE TABLE store_info (
        store_id TEXT PRIMARY KEY, name TEXT NOT NULL,
        updated_ts TEXT NOT NULL DEFAULT '', updated_op TEXT NOT NULL DEFAULT '')''',
    '''CREATE TABLE users (
        id TEXT PRIMARY KEY, store_id TEXT NOT NULL, login TEXT NOT NULL, name TEXT NOT NULL,
        role TEXT NOT NULL, salt TEXT NOT NULL, pw_hash TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1, updated_ts TEXT NOT NULL DEFAULT '',
        updated_op TEXT NOT NULL DEFAULT '')''',
    'CREATE INDEX users_store_login ON users (store_id, login)',
    'CREATE TABLE sync_state (name TEXT PRIMARY KEY, value TEXT NOT NULL)',
  ];

  /// [password] — SQLCipher paroli. [factory] — testda sqflite_common_ffi (shifrsiz).
  static Future<LocalDb> open(
    String path, {
    String? password,
    DatabaseFactory? factory,
  }) async {
    Future<void> onCreate(Database db, int _) async {
      for (final statement in _schema) {
        await db.execute(statement);
      }
    }

    final Database db;
    if (password != null) {
      db = await openDatabase(path, password: password, version: 1, onCreate: onCreate);
    } else {
      db = await (factory ?? databaseFactory).openDatabase(
        path,
        options: OpenDatabaseOptions(version: 1, onCreate: onCreate),
      );
    }
    return LocalDb._(db);
  }

  Future<void> close() => _db.close();

  // --- holat ---------------------------------------------------------------------

  Future<String?> getState(String name) => _getState(_db, name);

  Future<void> setState(String name, String value) => _setState(_db, name, value);

  static Future<String?> _getState(DatabaseExecutor db, String name) async {
    final rows = await db.query('sync_state', where: 'name = ?', whereArgs: [name]);
    return rows.isEmpty ? null : rows.first['value'] as String;
  }

  static Future<void> _setState(DatabaseExecutor db, String name, String value) async {
    await db.insert(
      'sync_state',
      {'name': name, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<String> deviceId() async {
    final existing = await getState('device_id');
    if (existing != null) return existing;
    final value = const Uuid().v4();
    await setState('device_id', value);
    return value;
  }

  Future<bool> isBootstrapped() async => (await getState('bootstrapped')) == '1';

  Future<String> nextReceiptNumber() async {
    final current = int.tryParse(await getState('receipt_seq') ?? '0') ?? 0;
    final next = current + 1;
    await setState('receipt_seq', '$next');
    final id = await deviceId();
    return '${id.substring(0, 4)}-$next';
  }

  // --- do'kon bootstrap'i ------------------------------------------------------------

  /// Do'konni shu qurilma yaratadi: o'zi egasi, bootstrap shart emas.
  Future<void> initOwner({
    required String storeId,
    required String deviceId,
    required String publicKeyHex,
    required String label,
  }) async {
    await _db.transaction((txn) async {
      await txn.insert(
        'devices',
        {
          'device_id': deviceId,
          'store_id': storeId,
          'public_key': publicKeyHex,
          'role': ops.roleOwner,
          'label': label,
          'active': 1,
          'updated_ts': '',
          'updated_op': '',
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
      await _setState(txn, 'store_id', storeId);
      await _setState(txn, 'bootstrapped', '1');
      await _setState(txn, 'bootstrap_ts', '');
    });
  }

  /// Juftlash kodi: egasi qurilmasi ishonch ildizi. Do'kon ma'lumoti egasi snapshot'i orqali keladi.
  Future<void> setPairing({
    required String storeId,
    required String ownerDeviceId,
    required String ownerPublicKeyHex,
  }) async {
    await _db.transaction((txn) async {
      await txn.insert(
        'devices',
        {
          'device_id': ownerDeviceId,
          'store_id': storeId,
          'public_key': ownerPublicKeyHex,
          'role': ops.roleOwner,
          'label': 'egasi',
          'active': 1,
          'updated_ts': '',
          'updated_op': '',
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
      await _setState(txn, 'store_id', storeId);
      await _setState(txn, 'bootstrapped', '0');
      await _setState(txn, 'bootstrap_ts', '');
    });
  }

  // --- navbat (yuborilmagan, mahalliy operatsiyalar) -----------------------------

  Future<void> enqueue(Map<String, dynamic> op) async {
    await _db.insert(
      'outbox',
      {
        'op_id': op['op_id'],
        'store_id': op['store_id'],
        'op': jsonEncode(op),
        'created_at': op['ts'],
      },
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
  }

  Future<List<Map<String, dynamic>>> pendingOps({int limit = 50}) async {
    final rows = await _db.query('outbox', orderBy: 'created_at, op_id', limit: limit);
    return [for (final r in rows) jsonDecode(r['op'] as String) as Map<String, dynamic>];
  }

  Future<int> pendingCount() async {
    final rows = await _db.rawQuery('SELECT COUNT(*) AS n FROM outbox');
    return rows.first['n'] as int;
  }

  Future<void> dropOutbox(String opId) =>
      _db.delete('outbox', where: 'op_id = ?', whereArgs: [opId]);

  Future<int> deferredCount() async {
    final rows = await _db.rawQuery('SELECT COUNT(*) AS n FROM deferred');
    return rows.first['n'] as int;
  }

  // --- o'qish: katalog, qoldiq, savdo ----------------------------------------------

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

  Future<Map<String, dynamic>> _productMap(Map<String, Object?> row, String storeId) async {
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

  Future<Map<String, dynamic>?> getProduct(String productId, String storeId) async {
    final rows = await _db.query(
      'products',
      where: 'id = ? AND deleted = 0',
      whereArgs: [productId],
    );
    return rows.isEmpty ? null : _productMap(rows.first, storeId);
  }

  Future<Map<String, dynamic>?> productByBarcode(String code, String storeId) async {
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
    final rows = await _db.query('products', where: 'deleted = 0', orderBy: 'name');
    final found = <Map<String, dynamic>>[];
    for (final r in rows) {
      if (needle.isEmpty || (r['name'] as String).toLowerCase().contains(needle)) {
        found.add(await _productMap(r, storeId));
        if (found.length >= limit) break;
      }
    }
    return found;
  }

  /// Katalog (o'chirilganlarsiz), qoldiqsiz — tahrirlash ro'yxati uchun.
  Future<List<Map<String, dynamic>>> allProducts() async {
    final rows = await _db.query('products', where: 'deleted = 0', orderBy: 'name');
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

  /// Shu qurilmaning ochiq smenasi (har bir qurilmaning o'z smenasi bor).
  Future<Map<String, dynamic>?> openShiftForDevice(String deviceId) async {
    final rows = await _db.query(
      'shifts',
      where: 'device = ? AND closed_at IS NULL',
      whereArgs: [deviceId],
    );
    return rows.isEmpty ? null : Map<String, dynamic>.from(rows.first);
  }

  Future<Map<String, dynamic>?> getShift(String shiftId) async {
    final rows = await _db.query('shifts', where: 'id = ?', whereArgs: [shiftId]);
    return rows.isEmpty ? null : Map<String, dynamic>.from(rows.first);
  }

  Future<List<Map<String, dynamic>>> sales(String storeId, {int limit = 50}) async {
    final rows = await _db.query(
      'sales',
      where: 'store_id = ?',
      whereArgs: [storeId],
      orderBy: 'created_at DESC',
      limit: limit,
    );
    return [for (final r in rows) {...r, 'payload': jsonDecode(r['payload'] as String)}];
  }

  Future<Map<String, dynamic>?> getSale(String saleId) async {
    final rows = await _db.query('sales', where: 'id = ?', whereArgs: [saleId]);
    if (rows.isEmpty) return null;
    return {...rows.first, 'payload': jsonDecode(rows.first['payload'] as String)};
  }

  Future<Map<String, dynamic>> shiftSummary(String shiftId) async {
    final rows = await _db.query('sales', where: 'shift_id = ?', whereArgs: [shiftId]);
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
        summary['total_refunds'] = (summary['total_refunds'] as int) + (r['total'] as int);
        continue;
      }
      summary['sales_count'] = (summary['sales_count'] as int) + 1;
      summary['total_sales'] = (summary['total_sales'] as int) + (r['total'] as int);
      final payload = jsonDecode(r['payload'] as String) as Map<String, dynamic>;
      for (final p in (payload['payments'] as List)) {
        final m = p as Map<String, dynamic>;
        byMethod[m['method'] as String] =
            (byMethod[m['method'] as String] ?? 0) + (m['amount'] as int);
      }
    }
    return summary;
  }

  // --- roster, foydalanuvchilar, do'kon --------------------------------------------

  Future<Map<String, dynamic>?> deviceRow(String deviceId) async {
    final rows = await _db.query('devices', where: 'device_id = ?', whereArgs: [deviceId]);
    if (rows.isEmpty) return null;
    return {...rows.first, 'active': rows.first['active'] == 1};
  }

  Future<List<Map<String, dynamic>>> listDevices(String storeId) async {
    final rows = await _db.query(
      'devices',
      where: 'store_id = ?',
      whereArgs: [storeId],
      orderBy: 'label, device_id',
    );
    return [for (final r in rows) {...r, 'active': r['active'] == 1}];
  }

  Future<bool> isOwnerDevice(String deviceId) async {
    final row = await deviceRow(deviceId);
    return row != null && row['active'] == true && row['role'] == ops.roleOwner;
  }

  Future<String?> storeName(String storeId) async {
    final rows = await _db.query('store_info', where: 'store_id = ?', whereArgs: [storeId]);
    return rows.isEmpty ? null : rows.first['name'] as String;
  }

  Future<Map<String, dynamic>?> findUser(String storeId, String login) async {
    final rows = await _db.query(
      'users',
      where: 'store_id = ? AND login = ? AND active = 1',
      whereArgs: [storeId, login.trim().toLowerCase()],
      orderBy: 'updated_ts DESC',
      limit: 1,
    );
    return rows.isEmpty ? null : Map<String, dynamic>.from(rows.first);
  }

  Future<Map<String, dynamic>?> getUser(String userId) async {
    final rows = await _db.query('users', where: 'id = ?', whereArgs: [userId]);
    return rows.isEmpty ? null : Map<String, dynamic>.from(rows.first);
  }

  Future<bool> loginExists(String storeId, String login) async {
    final rows = await _db.query(
      'users',
      columns: ['id'],
      where: 'store_id = ? AND login = ?',
      whereArgs: [storeId, login.trim().toLowerCase()],
    );
    return rows.isNotEmpty;
  }

  Future<List<Map<String, dynamic>>> listUsers(String storeId) async {
    final rows = await _db.query(
      'users',
      columns: ['id', 'login', 'name', 'role', 'active'],
      where: 'store_id = ?',
      whereArgs: [storeId],
      orderBy: 'name',
    );
    return [for (final r in rows) {...r, 'active': r['active'] == 1}];
  }

  /// Egasi snapshot'i uchun to'liq holat (docs/sync-mqtt.md, 9-bo'lim).
  Future<Map<String, dynamic>> snapshotPayload(String storeId) async {
    final info = await _db.query('store_info', where: 'store_id = ?', whereArgs: [storeId]);
    final devices = await _db.query('devices', where: 'store_id = ?', whereArgs: [storeId]);
    final users = await _db.query('users', where: 'store_id = ?', whereArgs: [storeId]);
    final products = await _db.query('products');
    final movements = await _db.query(
      'movements',
      columns: ['product_id', 'qty'],
      where: 'store_id = ?',
      whereArgs: [storeId],
    );
    final shifts = await _db.query(
      'shifts',
      where: 'store_id = ? AND closed_at IS NULL',
      whereArgs: [storeId],
    );
    final totals = <String, Decimal>{};
    for (final m in movements) {
      final pid = m['product_id'] as String;
      totals[pid] = (totals[pid] ?? Decimal.zero) + Decimal.parse(m['qty'] as String);
    }
    return {
      'store': info.isEmpty
          ? null
          : {'name': info.first['name'], 'updated_ts': info.first['updated_ts']},
      'devices': [
        for (final d in devices)
          {
            'device_id': d['device_id'],
            'public_key': d['public_key'],
            'role': d['role'],
            'label': d['label'],
            'active': d['active'] == 1,
            'updated_ts': d['updated_ts'],
          },
      ],
      'users': [
        for (final u in users)
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
      'open_shifts': [
        for (final s in shifts)
          {
            'id': s['id'],
            'device': s['device'],
            'opening_cash': s['opening_cash'],
            'opened_at': s['opened_at'],
          },
      ],
    };
  }

  // --- qabul qilish: applyOp ------------------------------------------------------------

  /// Operatsiyani tekshiradi va qo'llaydi. Natija: ops.resultApplied, ops.resultDuplicate, ops.resultRejected,
  /// ops.resultPending, ops.resultSkipped. Bitta operatsiya tranzaksiyada: xato faqat shu operatsiyani bekor qiladi.
  Future<String> applyOp(Map<String, dynamic> op) {
    return _db.transaction<String>((txn) => _guarded(txn, op));
  }

  Future<String> _guarded(Transaction txn, Map<String, dynamic> op) async {
    await txn.execute('SAVEPOINT op_guard');
    String result;
    try {
      result = await _process(txn, op);
      await txn.execute('RELEASE op_guard');
    } on _Invalid {
      await txn.execute('ROLLBACK TO op_guard');
      await txn.execute('RELEASE op_guard');
      result = ops.resultRejected;
    } on Object {
      await txn.execute('ROLLBACK TO op_guard');
      await txn.execute('RELEASE op_guard');
      result = ops.resultRejected;
    }
    return result;
  }

  Future<String> _process(Transaction txn, Map<String, dynamic> op) async {
    if (!_wellFormed(op) || !ops.knownTypes.contains(op['type'])) return ops.resultRejected;
    final kind = op['type'] as String;
    if (kind == ops.opSnapshotRequest || kind == ops.opJoinRequest) return ops.resultSkipped;
    if (await _applied(txn, op['op_id'] as String)) return ops.resultDuplicate;
    final storeId = await _getState(txn, 'store_id');
    if (op['store_id'] != storeId) return ops.resultRejected;
    if (!await _bootstrappedTxn(txn)) return _processBootstrapping(txn, op);

    final bts = await _getState(txn, 'bootstrap_ts') ?? '';
    final ts = op['ts'] as String;
    if (kind != ops.opDevice && kind != ops.opSnapshot && bts.isNotEmpty && ts.compareTo(bts) <= 0) {
      return ops.resultSkipped; // snapshot ichida (K5): bootstrap vaqtidan oldingi operatsiya
    }
    final signer = await _deviceRowTxn(txn, op['device'] as String);
    if (signer == null) return _defer(txn, op);
    if (signer.active != true || !await verifyOp(op, signer.publicKey)) return ops.resultRejected;
    if (ops.ownerOnlyTypes.contains(kind) && signer.role != ops.roleOwner) return ops.resultRejected;
    return _apply(txn, op, signer);
  }

  Future<String> _processBootstrapping(Transaction txn, Map<String, dynamic> op) async {
    final kind = op['type'] as String;
    final signer = await _deviceRowTxn(txn, op['device'] as String);
    if (signer != null &&
        (kind == ops.opDevice || kind == ops.opSnapshot) &&
        signer.active == true &&
        signer.role == ops.roleOwner &&
        await verifyOp(op, signer.publicKey)) {
      return _apply(txn, op, signer);
    }
    return _defer(txn, op);
  }

  Future<String> _apply(Transaction txn, Map<String, dynamic> op, _Signer signer) async {
    final kind = op['type'] as String;
    final String result;
    switch (kind) {
      case ops.opDevice:
        result = await _applyDevice(txn, op, signer);
      case ops.opStore:
        result = await _applyStore(txn, op);
      case ops.opUser:
        result = await _applyUser(txn, op);
      case ops.opProduct:
        result = await _applyProduct(txn, op);
      case ops.opMovement:
        result = await _applyMovement(txn, op);
      case ops.opSale:
        result = await _applySale(txn, op);
      case ops.opRefund:
        result = await _applyRefund(txn, op);
      case ops.opShiftOpen:
        result = await _applyShiftOpen(txn, op);
      case ops.opShiftClose:
        result = await _applyShiftClose(txn, op, signer);
      case ops.opSnapshot:
        result = await _applySnapshot(txn, op);
      default:
        result = ops.resultRejected;
    }
    if (result == ops.resultApplied || result == ops.resultSkipped) {
      await txn.insert(
        'applied_ops',
        {'op_id': op['op_id']},
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
    if (result == ops.resultPending) return _defer(txn, op);
    return result;
  }

  // --- dedupe va kutish buferi ---------------------------------------------------------

  Future<bool> _applied(Transaction txn, String opId) async {
    final rows = await txn.query('applied_ops', where: 'op_id = ?', whereArgs: [opId]);
    return rows.isNotEmpty;
  }

  Future<String> _defer(Transaction txn, Map<String, dynamic> op) async {
    final count = Sqflite.firstIntValue(
      await txn.rawQuery('SELECT COUNT(*) FROM deferred'),
    )!;
    if (count >= maxDeferred) return ops.resultRejected;
    await txn.insert(
      'deferred',
      {'op_id': op['op_id'], 'ts': op['ts'], 'op': jsonEncode(op)},
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
    return ops.resultPending;
  }

  /// Kutilayotgan operatsiyalarni qayta tekshiradi (roster yoki katalog o'zgargach).
  Future<void> _sweep(Transaction txn) async {
    final rows = await txn.query('deferred', orderBy: 'ts, op_id');
    for (final row in rows) {
      await txn.delete('deferred', where: 'op_id = ?', whereArgs: [row['op_id']]);
      await _guarded(txn, jsonDecode(row['op'] as String) as Map<String, dynamic>);
    }
  }

  Future<bool> _bootstrappedTxn(Transaction txn) async =>
      (await _getState(txn, 'bootstrapped')) == '1';

  // --- ko'rinishlar: qo'llash -----------------------------------------------------------

  Future<String> _applyDevice(Transaction txn, Map<String, dynamic> op, _Signer signer) async {
    if (signer.role != ops.roleOwner) return ops.resultRejected;
    final changed = await _putDevice(
      txn,
      op['store_id'] as String,
      op['payload'] as Map<String, dynamic>,
      op['ts'] as String,
      op['op_id'] as String,
    );
    if (await _bootstrappedTxn(txn)) await _sweep(txn);
    return changed ? ops.resultApplied : ops.resultSkipped;
  }

  Future<bool> _putDevice(
    Transaction txn,
    String storeId,
    Map<String, dynamic> data,
    String ts,
    String opId,
  ) async {
    final deviceId = _str(data, 'device_id');
    final publicKey = _str(data, 'public_key').toLowerCase();
    final role = data['role'];
    final active = data['active'] ?? true;
    if (!_hex64.hasMatch(publicKey) || (role != ops.roleOwner && role != ops.roleCashier)) {
      throw const _Invalid('device');
    }
    if (active is! bool) throw const _Invalid('device');
    final existing = await _deviceRowOf(txn, deviceId);
    if (existing != null) {
      if (existing.publicKey != publicKey) throw const _Invalid('device key');
      if (existing.role == ops.roleOwner && (role != ops.roleOwner || !active)) {
        throw const _Invalid('owner immutable');
      }
      if ('${existing.updatedTs}\u0000${existing.updatedOp}'.compareTo('$ts\u0000$opId') >= 0) {
        return false;
      }
    } else if (role == ops.roleOwner && !active) {
      throw const _Invalid('owner inactive');
    }
    await txn.insert(
      'devices',
      {
        'device_id': deviceId,
        'store_id': storeId,
        'public_key': publicKey,
        'role': role,
        'label': (data['label'] ?? '').toString(),
        'active': active ? 1 : 0,
        'updated_ts': ts,
        'updated_op': opId,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return true;
  }

  Future<String> _applyStore(Transaction txn, Map<String, dynamic> op) async {
    final changed = await _putStore(
      txn,
      op['store_id'] as String,
      _str(op['payload'] as Map<String, dynamic>, 'name'),
      op['ts'] as String,
      op['op_id'] as String,
    );
    return changed ? ops.resultApplied : ops.resultSkipped;
  }

  Future<bool> _putStore(Transaction txn, String storeId, String name, String ts, String opId) async {
    final rows = await txn.query('store_info', where: 'store_id = ?', whereArgs: [storeId]);
    if (rows.isNotEmpty &&
        '${rows.first['updated_ts']}\u0000${rows.first['updated_op']}'.compareTo('$ts\u0000$opId') >= 0) {
      return false;
    }
    await txn.insert(
      'store_info',
      {'store_id': storeId, 'name': name, 'updated_ts': ts, 'updated_op': opId},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return true;
  }

  Future<String> _applyUser(Transaction txn, Map<String, dynamic> op) async {
    final changed = await _putUser(
      txn,
      op['store_id'] as String,
      op['payload'] as Map<String, dynamic>,
      op['ts'] as String,
      op['op_id'] as String,
    );
    return changed ? ops.resultApplied : ops.resultSkipped;
  }

  Future<bool> _putUser(
    Transaction txn,
    String storeId,
    Map<String, dynamic> data,
    String ts,
    String opId,
  ) async {
    final userId = _str(data, 'id');
    final role = data['role'];
    final active = data['active'] ?? true;
    if ((role != ops.roleOwner && role != ops.roleCashier) || active is! bool) {
      throw const _Invalid('user');
    }
    final rows = await txn.query('users', where: 'id = ?', whereArgs: [userId]);
    if (rows.isNotEmpty &&
        '${rows.first['updated_ts']}\u0000${rows.first['updated_op']}'.compareTo('$ts\u0000$opId') >= 0) {
      return false;
    }
    await txn.insert(
      'users',
      {
        'id': userId,
        'store_id': storeId,
        'login': _str(data, 'login').trim().toLowerCase(),
        'name': _str(data, 'name'),
        'role': role,
        'salt': _str(data, 'salt'),
        'pw_hash': _str(data, 'pw_hash'),
        'active': active ? 1 : 0,
        'updated_ts': ts,
        'updated_op': opId,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return true;
  }

  Future<String> _applyProduct(Transaction txn, Map<String, dynamic> op) async {
    await _putProduct(txn, op['payload'] as Map<String, dynamic>, op['ts'] as String, op['op_id'] as String);
    if (await _bootstrappedTxn(txn)) await _sweep(txn);
    return ops.resultApplied;
  }

  Future<bool> _putProduct(
    Transaction txn,
    Map<String, dynamic> data,
    String ts,
    String opId,
  ) async {
    final productId = _str(data, 'id');
    final salePrice = _int(data, 'sale_price');
    final costPrice = _int(data, 'cost_price', 0);
    if (salePrice < 0 || costPrice < 0) throw const _Invalid('price');
    final minStock = _dec(data['min_stock'] ?? '0').toString();
    final barcodes = data['barcodes'] ?? [];
    final deleted = data['deleted'] ?? false;
    if (barcodes is! List || barcodes.any((b) => b is! String)) throw const _Invalid('barcodes');
    if (deleted is! bool) throw const _Invalid('deleted');
    // Narx tarixi: har o'zgarish saqlanadi, sotuv tekshiruvi `ts` vaqtidagi narxni oladi
    await txn.insert(
      'product_prices',
      {'product_id': productId, 'ts': ts, 'op_id': opId, 'sale_price': salePrice},
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
    final rows = await txn.query('products', where: 'id = ?', whereArgs: [productId]);
    if (rows.isNotEmpty &&
        '${rows.first['updated_ts']}\u0000${rows.first['updated_op']}'.compareTo('$ts\u0000$opId') >= 0) {
      return false;
    }
    await txn.insert(
      'products',
      {
        'id': productId,
        'name': _str(data, 'name'),
        'unit': _str(data, 'unit'),
        'sale_price': salePrice,
        'cost_price': costPrice,
        'min_stock': minStock,
        'barcodes': jsonEncode(barcodes),
        'deleted': deleted ? 1 : 0,
        'updated_ts': ts,
        'updated_op': opId,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return true;
  }

  Future<String> _applyMovement(Transaction txn, Map<String, dynamic> op) async {
    final payload = op['payload'] as Map<String, dynamic>;
    if (!ops.movementKinds.contains(payload['kind'])) return ops.resultRejected;
    final qty = _dec(payload['qty']);
    if (qty == Decimal.zero) return ops.resultRejected;
    await _insertMovement(
      txn,
      op['op_id'] as String,
      op['store_id'] as String,
      _str(payload, 'product_id'),
      qty,
      payload['kind'] as String,
    );
    return ops.resultApplied;
  }

  Future<void> _insertMovement(
    Transaction txn,
    String id,
    String storeId,
    String productId,
    Decimal qty,
    String kind,
  ) async {
    await txn.insert(
      'movements',
      {'id': id, 'store_id': storeId, 'product_id': productId, 'qty': qty.toString(), 'kind': kind},
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
  }

  Future<int?> _priceAt(Transaction txn, String productId, String ts) async {
    final rows = await txn.query(
      'product_prices',
      columns: ['sale_price'],
      where: 'product_id = ? AND ts <= ?',
      whereArgs: [productId, ts],
      orderBy: 'ts DESC, op_id DESC',
      limit: 1,
    );
    return rows.isEmpty ? null : rows.first['sale_price'] as int;
  }

  /// Sotuv narxlari katalogga mos (docs/sync-mqtt.md, 6.1). Katalog kutilsa ops.resultPending, mos bo'lmasa _Invalid.
  Future<String> _checkSale(Transaction txn, Map<String, dynamic> payload, String ts) async {
    final items = payload['items'];
    if (items is! List || items.isEmpty) throw const _Invalid('items');
    var subtotal = 0;
    for (final raw in items) {
      if (raw is! Map<String, dynamic>) throw const _Invalid('item');
      final productId = _str(raw, 'product_id');
      final qty = _dec(raw['qty']);
      if (qty <= Decimal.zero) throw const _Invalid('qty');
      final unitPrice = _int(raw, 'unit_price');
      final lineTotal = _int(raw, 'line_total');
      final price = await _priceAt(txn, productId, ts);
      if (price == null) return ops.resultPending;
      if (unitPrice != price || lineTotal != roundSom(qty * Decimal.fromInt(price))) {
        throw const _Invalid('price mismatch');
      }
      subtotal += lineTotal;
    }
    final discount = _int(payload, 'discount', 0);
    if (_int(payload, 'subtotal') != subtotal || discount < 0 || discount > subtotal) {
      throw const _Invalid('subtotal');
    }
    if (_int(payload, 'total') != subtotal - discount) throw const _Invalid('total');
    final payments = payload['payments'] ?? [];
    if (payments is! List) throw const _Invalid('payments');
    var paid = 0;
    for (final p in payments) {
      if (p is Map<String, dynamic>) paid += _int(p, 'amount');
    }
    if (paid < subtotal - discount) throw const _Invalid('payments short');
    return ops.resultApplied;
  }

  Future<String> _applySale(Transaction txn, Map<String, dynamic> op) async {
    final payload = op['payload'] as Map<String, dynamic>;
    final saleId = _str(payload, 'id');
    if (saleId != op['op_id']) throw const _Invalid('sale id');
    final verdict = await _checkSale(txn, payload, op['ts'] as String);
    if (verdict == ops.resultPending) return ops.resultPending;
    final existing = await txn.query('sales', where: 'id = ?', whereArgs: [saleId]);
    if (existing.isNotEmpty) return ops.resultRejected;
    for (final raw in payload['items'] as List) {
      final item = raw as Map<String, dynamic>;
      await _insertMovement(
        txn,
        '${op['op_id']}:${item['product_id']}',
        op['store_id'] as String,
        item['product_id'] as String,
        -_dec(item['qty']),
        'sale',
      );
    }
    final refunded = await txn.query('refunded_sales', where: 'sale_id = ?', whereArgs: [saleId]);
    await txn.insert(
      'sales',
      {
        'id': saleId,
        'store_id': op['store_id'],
        'shift_id': payload['shift_id'],
        'number': (payload['number'] ?? '').toString(),
        'status': refunded.isEmpty ? 'completed' : 'refunded',
        'total': _int(payload, 'total'),
        'payload': jsonEncode(payload),
        'created_at': payload['created_at'] ?? op['ts'],
      },
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
    return ops.resultApplied;
  }

  Future<String> _applyRefund(Transaction txn, Map<String, dynamic> op) async {
    final payload = op['payload'] as Map<String, dynamic>;
    final saleId = _str(payload, 'sale_id');
    if (op['op_id'] != ops.refundOpId(saleId)) throw const _Invalid('refund id');
    final items = _items(payload['items']);
    final already = await txn.query('refunded_sales', where: 'sale_id = ?', whereArgs: [saleId]);
    if (already.isNotEmpty) return ops.resultRejected;
    final saleRows = await txn.query('sales', where: 'id = ?', whereArgs: [saleId]);
    if (saleRows.isNotEmpty) {
      if (saleRows.first['status'] != 'completed') return ops.resultRejected;
      final sale = jsonDecode(saleRows.first['payload'] as String) as Map<String, dynamic>;
      final expected = [
        for (final i in sale['items'] as List)
          (
            (i as Map<String, dynamic>)['product_id'] as String,
            _dec(i['qty']),
          ),
      ]..sort(_compareItems);
      final given = [...items]..sort(_compareItems);
      if (expected.length != given.length) return ops.resultRejected;
      for (var k = 0; k < expected.length; k++) {
        if (expected[k].$1 != given[k].$1 || expected[k].$2 != given[k].$2) return ops.resultRejected;
      }
    }
    for (final item in items) {
      await _insertMovement(
        txn,
        'refund:$saleId:${item.$1}',
        op['store_id'] as String,
        item.$1,
        item.$2,
        'sale_return',
      );
    }
    await txn.insert('refunded_sales', {
      'sale_id': saleId,
      'op_id': op['op_id'],
      'ts': op['ts'],
    });
    if (saleRows.isNotEmpty) {
      await txn.update('sales', {'status': 'refunded'}, where: 'id = ?', whereArgs: [saleId]);
    }
    return ops.resultApplied;
  }

  Future<String> _applyShiftOpen(Transaction txn, Map<String, dynamic> op) async {
    final payload = op['payload'] as Map<String, dynamic>;
    final shiftId = _str(payload, 'shift_id');
    if (shiftId != op['op_id']) throw const _Invalid('shift id');
    final openingCash = _int(payload, 'opening_cash');
    if (openingCash < 0) throw const _Invalid('opening_cash');
    // Tranzaksiya ichida faqat txn orqali o'qiladi (db orqali o'qish osilib qolardi)
    final open = await txn.query(
      'shifts',
      where: 'device = ? AND closed_at IS NULL',
      whereArgs: [op['device']],
    );
    if (open.isNotEmpty) return ops.resultRejected;
    final same = await txn.query('shifts', where: 'id = ?', whereArgs: [shiftId]);
    if (same.isNotEmpty) return ops.resultRejected;
    await txn.insert('shifts', {
      'id': shiftId,
      'store_id': op['store_id'],
      'device': op['device'],
      'opened_at': op['ts'],
      'opening_cash': openingCash,
    });
    return ops.resultApplied;
  }

  Future<String> _applyShiftClose(Transaction txn, Map<String, dynamic> op, _Signer signer) async {
    final payload = op['payload'] as Map<String, dynamic>;
    final shiftId = _str(payload, 'shift_id');
    final closingCash = _int(payload, 'closing_cash');
    final rows = await txn.query('shifts', where: 'id = ?', whereArgs: [shiftId]);
    if (rows.isEmpty) return ops.resultPending;
    final row = rows.first;
    if (row['closed_at'] != null) return ops.resultRejected;
    if (row['device'] != op['device'] && signer.role != ops.roleOwner) return ops.resultRejected;
    final summary = payload['summary'] ?? {};
    if (summary is! Map<String, dynamic>) throw const _Invalid('summary');
    await txn.update(
      'shifts',
      {'closed_at': op['ts'], 'closing_cash': closingCash, 'summary': jsonEncode(summary)},
      where: 'id = ?',
      whereArgs: [shiftId],
    );
    return ops.resultApplied;
  }

  /// Bootstrap: egasi snapshot'i. Faqat bootstrap bo'lmagan qurilmada (K5).
  Future<String> _applySnapshot(Transaction txn, Map<String, dynamic> op) async {
    if (await _bootstrappedTxn(txn)) return ops.resultRejected;
    final payload = op['payload'] as Map<String, dynamic>;
    final storeId = op['store_id'] as String;
    final opId = op['op_id'] as String;
    final info = payload['store'];
    if (info is Map<String, dynamic>) {
      await _putStore(txn, storeId, _str(info, 'name'), (info['updated_ts'] ?? '').toString(), opId);
    }
    for (final d in (payload['devices'] ?? []) as List) {
      final m = d as Map<String, dynamic>;
      await _putDevice(txn, storeId, m, (m['updated_ts'] ?? '').toString(), opId);
    }
    for (final u in (payload['users'] ?? []) as List) {
      final m = u as Map<String, dynamic>;
      await _putUser(txn, storeId, m, (m['updated_ts'] ?? '').toString(), opId);
    }
    for (final p in (payload['products'] ?? []) as List) {
      final m = p as Map<String, dynamic>;
      await _putProduct(txn, m, (m['updated_ts'] ?? '').toString(), opId);
    }
    final balances = (payload['balances'] ?? {}) as Map<String, dynamic>;
    for (final entry in balances.entries) {
      final amount = _dec(entry.value);
      if (amount != Decimal.zero) {
        await _insertMovement(txn, 'snapshot:$opId:${entry.key}', storeId, entry.key, amount, 'snapshot');
      }
    }
    for (final s in (payload['open_shifts'] ?? []) as List) {
      final m = s as Map<String, dynamic>;
      await txn.insert(
        'shifts',
        {
          'id': _str(m, 'id'),
          'store_id': storeId,
          'device': _str(m, 'device'),
          'opened_at': _str(m, 'opened_at'),
          'opening_cash': _int(m, 'opening_cash'),
        },
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
    await _setState(txn, 'bootstrapped', '1');
    await _setState(txn, 'bootstrap_ts', op['ts'] as String);
    await _sweep(txn);
    return ops.resultApplied;
  }

  // --- roster (tranzaksiya ichida) -------------------------------------------------------

  Future<_Signer?> _deviceRowTxn(Transaction txn, String deviceId) => _deviceRowOf(txn, deviceId);

  static Future<_Signer?> _deviceRowOf(DatabaseExecutor db, String deviceId) async {
    final rows = await db.query('devices', where: 'device_id = ?', whereArgs: [deviceId]);
    if (rows.isEmpty) return null;
    final r = rows.first;
    return _Signer(
      publicKey: r['public_key'] as String,
      role: r['role'] as String,
      active: r['active'] == 1,
      updatedTs: r['updated_ts'] as String,
      updatedOp: r['updated_op'] as String,
    );
  }

  /// Qo'shilish so'rovi o'z kaliti bilan imzolanganmi, do'kon shu do'konmi, qurilma hali qo'shilmaganmi.
  Future<bool> verifyJoinRequest(Map<String, dynamic> op) async {
    if (op['type'] != ops.opJoinRequest || !_wellFormed(op)) return false;
    final payload = op['payload'] as Map<String, dynamic>;
    final publicKey = payload['public_key'];
    if (payload['device_id'] != op['device'] || publicKey is! String) return false;
    if (op['store_id'] != await getState('store_id') || !_hex64.hasMatch(publicKey)) return false;
    final existing = await deviceRow(op['device'] as String);
    if (existing != null && existing['active'] == true) return false;
    return verifyOp(op, publicKey);
  }

  /// Operatsiya muallifi faol roster qurilmasimi va imzosi to'g'rimi (snapshot_request uchun).
  Future<bool> isActiveDeviceOp(Map<String, dynamic> op) async {
    final row = await deviceRow(op['device'] as String);
    return row != null && row['active'] == true && await verifyOp(op, row['public_key'] as String);
  }

  // --- yordamchilar ----------------------------------------------------------------------

  static bool _wellFormed(Map<String, dynamic> op) {
    const keys = ['op_id', 'type', 'device', 'ts', 'store_id', 'payload', 'sig'];
    if (!keys.every(op.containsKey)) return false;
    return op['ts'] is String &&
        (op['ts'] as String).length == 27 &&
        op['payload'] is Map &&
        op['op_id'] is String &&
        op['type'] is String &&
        op['device'] is String &&
        op['store_id'] is String &&
        op['sig'] is String;
  }

  static String _str(Map<String, dynamic> data, String key) {
    final value = data[key];
    if (value is! String || value.isEmpty) throw _Invalid(key);
    return value;
  }

  static int _int(Map<String, dynamic> data, String key, [int? fallback]) {
    final value = data.containsKey(key) ? data[key] : fallback;
    if (value is! int) throw _Invalid(key);
    return value;
  }

  static Decimal _dec(Object? value) {
    if (value is bool || value == null) throw const _Invalid('qty');
    try {
      return Decimal.parse(value.toString());
    } on FormatException {
      throw const _Invalid('qty');
    }
  }

  static List<(String, Decimal)> _items(Object? raw) {
    if (raw is! List || raw.isEmpty) throw const _Invalid('items');
    final out = <(String, Decimal)>[];
    for (final i in raw) {
      if (i is! Map<String, dynamic>) throw const _Invalid('items');
      final qty = _dec(i['qty']);
      if (qty <= Decimal.zero) throw const _Invalid('qty');
      out.add((_str(i, 'product_id'), qty));
    }
    return out;
  }

  static int _compareItems((String, Decimal) a, (String, Decimal) b) {
    final byId = a.$1.compareTo(b.$1);
    return byId != 0 ? byId : a.$2.compareTo(b.$2);
  }

  static final _hex64 = RegExp(r'^[0-9a-f]{64}$');
}

/// Imzo muallifi (roster qatori).
class _Signer {
  const _Signer({
    required this.publicKey,
    required this.role,
    required this.active,
    required this.updatedTs,
    required this.updatedOp,
  });

  final String publicKey;
  final String role;
  final bool active;
  final String updatedTs;
  final String updatedOp;
}

/// Operatsiya shakli yoki qiymati noto'g'ri: rad etiladi.
class _Invalid implements Exception {
  const _Invalid(this.reason);

  final String reason;
}
