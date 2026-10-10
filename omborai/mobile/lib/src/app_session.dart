import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:decimal/decimal.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import 'auth.dart';
import 'domain/cart.dart';
import 'offline/local_db.dart';
import 'sync/crypto.dart';
import 'sync/mqtt_sync.dart';
import 'sync/ops.dart' as ops;

/// Lokal baza paroli: birinchi ishga tushirishda tasodifiy 256-bit, Keystore'da saqlanadi.
class DbPasswordStore {
  DbPasswordStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<String> load() async {
    final existing = await _storage.read(key: 'db_password');
    if (existing != null) return existing;
    final random = Random.secure();
    final password = base64Url.encode(
      List<int>.generate(32, (_) => random.nextInt(256)),
    );
    await _storage.write(key: 'db_password', value: password);
    return password;
  }
}

/// Do'kon kaliti (MQTT shifrlash). Birinchi qurilma yaratadi; qolganlari hex matnni kiritib juftlanadi.
class StoreKeyStore {
  StoreKeyStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<Uint8List?> read() async {
    final hex = await _storage.read(key: 'store_key');
    return hex == null ? null : fromHex(hex);
  }

  Future<Uint8List> ensure() async {
    final existing = await read();
    if (existing != null) return existing;
    final key = generateStoreKey();
    await write(key);
    return key;
  }

  Future<void> write(Uint8List key) =>
      _storage.write(key: 'store_key', value: toHex(key));

  /// Juftlash: boshqa qurilmadagi kalit (64 hex belgi).
  Future<void> importHex(String hex) async {
    final cleaned = hex.trim().toLowerCase();
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(cleaned)) {
      throw ArgumentError("Kalit 64 belgili hex bo'lishi kerak");
    }
    await write(fromHex(cleaned));
  }

  static String toHex(Uint8List bytes) =>
      bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

  static Uint8List fromHex(String hex) {
    final out = Uint8List(hex.length ~/ 2);
    for (var i = 0; i < out.length; i++) {
      out[i] = int.parse(hex.substring(i * 2, i * 2 + 2), radix: 16);
    }
    return out;
  }
}

/// Ilova holati: sessiya, do'kon, smena, MQTT aloqasi va navbat. Barcha amallar MQTT operatsiyasi.
class AppSession extends ChangeNotifier {
  AppSession({
    required this.db,
    required this.keys,
    this.syncInterval = const Duration(seconds: 15),
    this.mqttHost = 'broker.hivemq.com',
    this.mqttPort = 8883,
    this.mqttSecure = true,
  });

  final LocalDb db;
  final StoreKeyStore keys;
  final Duration syncInterval;
  final String mqttHost;
  final int mqttPort;
  final bool mqttSecure;

  MqttSync? _mqtt;
  Timer? _timer;
  bool _snapshotRequested = false;
  bool _flushing = false;
  String? _storeId;
  String? storeName;

  /// Joriy foydalanuvchi (login qilingan). Egasi bo'lsa `role == 'owner'`.
  Map<String, dynamic>? currentUser;

  bool get isOwner => currentUser?['role'] == 'owner';
  String? lastMessage;
  int pending = 0;
  bool connected = false;

  bool get hasStore => _storeId != null;
  String get storeId => _storeId!;

  /// Joriy do'kon smenasi ochiqmi (refreshCounts orqali yangilanadi).
  bool shiftOpen = false;

  /// Ilova ochilganda: do'kon va sessiya lokal holatdan tiklanadi. Sessiya bo'lmasa false
  /// (kirish oynasi). Tarmoq kerak emas.
  Future<bool> restore() async {
    _storeId = await db.getState('store_id');
    storeName = _storeId == null ? null : await db.storeName(_storeId!);
    final userId = await db.getState('session_user');
    if (_storeId == null || userId == null || userId.isEmpty) return false;
    await _startSession();
    return true;
  }

  /// Foydalanuvchi login/parol bilan kiradi. Foydalanuvchi ma'lumoti lokal bazada (MQTT orqali kelgan).
  Future<void> login(String login, String password) async {
    final storeId = _storeId;
    final user = storeId == null ? null : await db.findUser(storeId, login);
    if (user == null) {
      throw const AuthException(
        "Foydalanuvchi topilmadi. Do'kon ma'lumoti hali kelmagan bo'lishi mumkin (internet va MQTT'ni tekshiring).",
      );
    }
    final ok = await verifyPassword(
      password,
      user['salt'] as String,
      user['pw_hash'] as String,
    );
    if (!ok) throw const AuthException("Login yoki parol noto'g'ri");
    await db.setState('session_user', user['id'] as String);
    await _startSession();
  }

  /// Yangi do'kon: kalit, do'kon nomi va egasi hisobi. Hammasi MQTT operatsiyasi sifatida yuboriladi.
  Future<void> createStore({
    required String storeName,
    required String ownerName,
    required String login,
    required String password,
  }) async {
    final storeId = const Uuid().v4();
    await keys.write(generateStoreKey());
    await db.setState('store_id', storeId);
    _storeId = storeId;
    this.storeName = storeName;
    final device = await db.deviceId();
    final hash = await hashPassword(password);
    await _emit(
      ops.newOp(
        type: ops.opStore,
        storeId: storeId,
        deviceId: device,
        payload: {'name': storeName},
      ),
    );
    await _emit(
      ops.newOp(
        type: ops.opUser,
        storeId: storeId,
        deviceId: device,
        payload: {
          'id': const Uuid().v4(),
          'login': normalizeLogin(login),
          'name': ownerName,
          'role': 'owner',
          'salt': hash.salt,
          'pw_hash': hash.hash,
          'active': true,
        },
      ),
    );
    await db.setState('store_name', storeName);
    await db.setState(
      'session_user',
      (await db.findUser(storeId, login))!['id'] as String,
    );
    await _startSession();
  }

  /// Mavjud do'konga qo'shilish: juftlash kodi (store_id:kalit). Ma'lumot snapshot orqali keladi.
  Future<void> joinStore(String code) async {
    final (storeId, keyHex) = parsePairingCode(code);
    await keys.write(StoreKeyStore.fromHex(keyHex));
    await db.setState('store_id', storeId);
    _storeId = storeId;
    await _startMqtt();
    _startTimer();
    notifyListeners();
  }

  /// Boshqa qurilmaga berish uchun juftlash kodi (kalit mavjud bo'lsa).
  Future<String?> pairingCode() async {
    final storeId = _storeId;
    final key = await keys.read();
    if (storeId == null || key == null) return null;
    return makePairingCode(storeId, StoreKeyStore.toHex(key));
  }

  Future<void> _startSession() async {
    final userId = await db.getState('session_user');
    currentUser = userId == null || userId.isEmpty
        ? null
        : await db.getUser(userId);
    await _startMqtt();
    _startTimer();
    await refreshCounts();
    notifyListeners();
  }

  Future<void> _startMqtt() async {
    final key = await keys.read();
    if (key == null) {
      lastMessage = "Do'kon kaliti yo'q: Sozlamalarda juftlang";
      return;
    }
    final deviceId = await db.deviceId();
    final mqtt = MqttSync(
      key: key,
      deviceId: deviceId,
      applyOp: _applyRemote,
      onRequest: (request) {
        if (request['store_id'] == _storeId) unawaited(_sendSnapshot());
      },
      host: mqttHost,
      port: mqttPort,
      secure: mqttSecure,
    );
    _mqtt = mqtt;
    try {
      await mqtt.start();
      connected = true;
      lastMessage = null;
      await flushOutbox();
      await _requestSnapshotIfEmpty();
    } on Object catch (e) {
      connected = false;
      lastMessage = 'MQTT ulanmadi: $e';
    }
    notifyListeners();
  }

  Future<bool> _applyRemote(Map<String, dynamic> op) async {
    final changed = await db.applyOp(op);
    if (changed) notifyListeners();
    return changed;
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(syncInterval, (_) => unawaited(_tick()));
  }

  Future<void> _tick() async {
    if (_mqtt?.connected != true) {
      connected = false;
      notifyListeners();
      return;
    }
    connected = true;
    await flushOutbox();
    await _requestSnapshotIfEmpty();
    await refreshCounts();
    notifyListeners();
  }

  // --- operatsiyalar -------------------------------------------------------

  /// Lokal qo'llash, so'ng yuborish (yoki navbat).
  Future<void> _emit(Map<String, dynamic> op) async {
    await db.applyOp(op);
    await _publishOrQueue(op);
    await refreshCounts();
    notifyListeners();
  }

  Future<void> _publishOrQueue(Map<String, dynamic> op) async {
    final mqtt = _mqtt;
    if (mqtt == null || !mqtt.connected) {
      await db.enqueue(op);
      return;
    }
    try {
      await mqtt.send(op);
    } on Object {
      await db.enqueue(op);
    }
  }

  Future<void> flushOutbox() async {
    final mqtt = _mqtt;
    if (_flushing || mqtt == null || !mqtt.connected) return;
    _flushing = true;
    try {
      for (final op in await db.pendingOps()) {
        await mqtt.send(op);
        await db.dropOutbox(op['op_id'] as String);
      }
    } on Object {
      // qolgan navbat keyingi urinishda yuboriladi
    } finally {
      _flushing = false;
      await refreshCounts();
    }
  }

  Future<void> _requestSnapshotIfEmpty() async {
    if (_snapshotRequested || await db.appliedCount() > 0) return;
    _snapshotRequested = true;
    final mqtt = _mqtt;
    if (mqtt == null || !mqtt.connected) {
      _snapshotRequested = false;
      return;
    }
    await mqtt.send(
      ops.newOp(
        type: ops.opSnapshotRequest,
        storeId: storeId,
        payload: {},
        deviceId: await db.deviceId(),
      ),
    );
    Future<void>.delayed(
      const Duration(seconds: 60),
      () => _snapshotRequested = false,
    );
  }

  Future<void> _sendSnapshot() async {
    final mqtt = _mqtt;
    if (mqtt == null || !mqtt.connected || await db.appliedCount() == 0) return;
    final snapshot = ops.newOp(
      type: ops.opSnapshot,
      storeId: storeId,
      payload: await db.snapshotPayload(storeId),
      deviceId: await db.deviceId(),
    );
    try {
      await mqtt.send(snapshot);
    } on Object {
      // boshqa qurilma javob beradi
    }
  }

  Future<void> openShift(int openingCash) async {
    if ((await db.openShift(storeId)) != null) {
      throw StateError('Smena allaqachon ochiq');
    }
    final shiftId = const Uuid().v4();
    await _emit(
      ops.newOp(
        type: ops.opShiftOpen,
        storeId: storeId,
        payload: {'shift_id': shiftId, 'opening_cash': openingCash},
        deviceId: await db.deviceId(),
        opId: shiftId,
      ),
    );
  }

  /// Smenani yopadi. Hisobot qaytadi.
  Future<Map<String, dynamic>> closeShift(int closingCash) async {
    final shift = await db.openShift(storeId);
    if (shift == null) throw StateError("Ochiq smena yo'q");
    final summary = await db.shiftSummary(shift['id'] as String);
    await _emit(
      ops.newOp(
        type: ops.opShiftClose,
        storeId: storeId,
        payload: {
          'shift_id': shift['id'],
          'closing_cash': closingCash,
          'summary': summary,
        },
        deviceId: await db.deviceId(),
      ),
    );
    return {
      ...summary,
      'opening_cash': shift['opening_cash'],
      'closing_cash': closingCash,
    };
  }

  /// Savdo: qoldiq tekshiriladi, so'ng MQTT orqali (yoki navbatga). Chek payload'ini qaytaradi.
  Future<Map<String, dynamic>> submitSale(Cart cart, String method) async {
    final shift = await db.openShift(storeId);
    if (shift == null) throw StateError('Avval smenani oching');
    for (final line in cart.lines) {
      final available = await db.balance(storeId, line.productId);
      if (line.qty > available) {
        throw StateError(
          '«${line.name}»: qoldiq ${available.toString()} ${line.unit}',
        );
      }
    }
    final payload = cart.toSalePayload(storeId: storeId, method: method);
    payload['shift_id'] = shift['id'];
    payload['number'] = await db.nextReceiptNumber();
    payload['created_at'] = DateTime.now().toUtc().toIso8601String();
    await _emit(
      ops.newOp(
        type: ops.opSale,
        storeId: storeId,
        payload: payload,
        deviceId: await db.deviceId(),
        opId: payload['id'] as String,
      ),
    );
    return payload;
  }

  /// Chekni qaytarish. op_id deterministik: bir chek bir marta qaytariladi.
  Future<void> refund(String saleId) async {
    final sale = await db.getSale(saleId);
    if (sale == null || sale['status'] != 'completed') {
      throw StateError('Bu chekni qaytarib bo\'lmaydi');
    }
    await _emit(
      ops.newOp(
        type: ops.opRefund,
        storeId: storeId,
        payload: {'sale_id': saleId},
        deviceId: await db.deviceId(),
        opId: ops.refundOpId(saleId),
      ),
    );
  }

  Future<void> saveProduct(Map<String, dynamic> product) async {
    await _emit(
      ops.newOp(
        type: ops.opProduct,
        storeId: storeId,
        payload: product,
        deviceId: await db.deviceId(),
      ),
    );
  }

  Future<void> deleteProduct(Map<String, dynamic> product) async {
    await saveProduct({...product, 'deleted': true});
  }

  Future<void> refreshCounts() async {
    pending = await db.pendingCount();
    if (_storeId != null) {
      shiftOpen = (await db.openShift(storeId)) != null;
      storeName = await db.storeName(storeId) ?? storeName;
    }
  }

  /// Kalit juftlangandan keyin MQTT'ni qayta ulaydi.
  Future<void> reconnect() async {
    await _mqtt?.stop();
    _mqtt = null;
    await _startMqtt();
    notifyListeners();
  }

  /// Foydalanuvchilar ro'yxati (faqat egasi ko'radi).
  Future<List<Map<String, dynamic>>> users() async {
    if (!isOwner) throw const AuthException("Faqat do'kon egasi uchun");
    return db.listUsers(storeId);
  }

  /// Yangi kassir. Parol xeshi va tuz qurilmada hisoblanadi, matn hech qayerga yuborilmaydi.
  Future<void> addCashier({
    required String name,
    required String login,
    required String password,
  }) async {
    if (!isOwner) throw const AuthException("Faqat do'kon egasi uchun");
    final cleanName = name.trim();
    final cleanLogin = normalizeLogin(login);
    if (cleanName.isEmpty || cleanLogin.isEmpty) {
      throw const AuthException('Ism va loginni kiriting');
    }
    if (password.length < minPasswordLength) {
      throw AuthException("Parol kamida $minPasswordLength belgi bo'lsin");
    }
    if (await db.loginExists(storeId, cleanLogin)) {
      throw const AuthException('Bu login band');
    }
    final hash = await hashPassword(password);
    await _emit(
      ops.newOp(
        type: ops.opUser,
        storeId: storeId,
        deviceId: await db.deviceId(),
        payload: {
          'id': const Uuid().v4(),
          'login': cleanLogin,
          'name': cleanName,
          'role': 'cashier',
          'salt': hash.salt,
          'pw_hash': hash.hash,
          'active': true,
        },
      ),
    );
  }

  /// Kassirni faollashtirish yoki o'chirish (egasini emas).
  Future<void> setUserActive(String userId, {required bool active}) async {
    if (!isOwner) throw const AuthException("Faqat do'kon egasi uchun");
    final row = await db.getUser(userId);
    if (row == null) throw const AuthException('Foydalanuvchi topilmadi');
    if (row['role'] == 'owner') {
      throw const AuthException("Do'kon egasini o'chirib bo'lmaydi");
    }
    await _emit(
      ops.newOp(
        type: ops.opUser,
        storeId: storeId,
        deviceId: await db.deviceId(),
        payload: {
          'id': row['id'],
          'login': row['login'],
          'name': row['name'],
          'role': row['role'],
          'salt': row['salt'],
          'pw_hash': row['pw_hash'],
          'active': active,
        },
      ),
    );
  }

  /// Sessiyani yopadi. Do'kon, kalit va ma'lumotlar qoladi: qayta kirish uchun login yetarli.
  Future<void> logout() async {
    _timer?.cancel();
    _timer = null;
    await _mqtt?.stop();
    _mqtt = null;
    await db.setState('session_user', '');
    currentUser = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

/// Mahalliy Decimal yordamchisi (ekranlarda ishlatiladi).
Decimal decimalOf(Object? value) => Decimal.parse('${value ?? 0}');
