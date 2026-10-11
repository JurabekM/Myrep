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
import 'sync/identity.dart';
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

/// Do'kon kaliti (MQTT shifrlash). Egasi yaratadi; kassa juftlash kodidagi hex matnni kiritadi.
class StoreKeyStore {
  StoreKeyStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<Uint8List?> read() async {
    final hex = await _storage.read(key: 'store_key');
    return hex == null ? null : fromHexBytes(hex);
  }

  Future<void> write(Uint8List key) =>
      _storage.write(key: 'store_key', value: hexOf(key));

  /// Juftlash: boshqa qurilmadagi kalit (64 hex belgi).
  Future<void> importHex(String hex) async {
    final cleaned = hex.trim().toLowerCase();
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(cleaned)) {
      throw ArgumentError("Kalit 64 belgili hex bo'lishi kerak");
    }
    await write(fromHexBytes(cleaned));
  }
}

/// Qurilmaning imzo kaliti (32 baytlik seed): Keystore'da. Birinchi ishga tushirishda yaratiladi.
class DeviceSeedStore {
  DeviceSeedStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<Uint8List> ensure() async {
    final existing = await _storage.read(key: 'device_seed');
    if (existing != null) return fromHexBytes(existing);
    final seed = randomBytes(32);
    await _storage.write(key: 'device_seed', value: hexOf(seed));
    return seed;
  }
}

/// Ilova holati: sessiya, do'kon, smena, MQTT aloqasi, qurilma tasdig'i va navbat.
/// Barcha amallar imzolangan MQTT operatsiyasi (docs/sync-mqtt.md).
class AppSession extends ChangeNotifier {
  AppSession({
    required this.db,
    required this.keys,
    required this.deviceSeeds,
    this.syncInterval = const Duration(seconds: 15),
    this.mqttHost = 'broker.hivemq.com',
    this.mqttPort = 8883,
    this.mqttSecure = true,
  });

  final LocalDb db;
  final StoreKeyStore keys;
  final DeviceSeedStore deviceSeeds;
  final Duration syncInterval;
  final String mqttHost;
  final int mqttPort;
  final bool mqttSecure;

  MqttSync? _mqtt;
  Timer? _timer;
  DeviceIdentity? _identity;
  bool _flushing = false;
  DateTime _lastRequest = DateTime.fromMillisecondsSinceEpoch(0);
  String? _storeId;
  final Set<String> _joinSeen = {};

  String? storeName;

  /// Joriy foydalanuvchi (login qilingan). Egasi bo'lsa `role == 'owner'`.
  Map<String, dynamic>? currentUser;

  /// Egasi tasdig'ini kutayotgan qurilmalar (faqat egasi qurilmasida to'ladi).
  final List<Map<String, dynamic>> joinRequests = [];

  String? lastMessage;
  int pending = 0;
  bool connected = false;

  /// Do'kon holati to'liq (egasi yoki snapshot orqali). Bo'lmasa login mumkin emas.
  bool bootstrapped = false;

  /// Shu qurilma egasi qurilmasimi (roster'da role=owner, faol).
  bool ownerDevice = false;

  bool get isOwner => currentUser?['role'] == ops.roleOwner;

  /// Boshqaruv amallari: egasi hisobi VA egasi qurilmasi (protokol ruxsati bilan bir xil).
  bool get canManage => isOwner && ownerDevice;

  bool get hasStore => _storeId != null;
  String get storeId => _storeId!;

  /// Shu qurilmaning ochiq smenasi bormi.
  bool shiftOpen = false;

  /// Ilova ochilganda: do'kon va sessiya lokal holatdan tiklanadi. Tarmoq kerak emas.
  Future<bool> restore() async {
    _identity = await _loadIdentity();
    _storeId = await db.getState('store_id');
    storeName = _storeId == null ? null : await db.storeName(_storeId!);
    if (_storeId == null) return false;
    await _startMqtt();
    _startTimer();
    final userId = await db.getState('session_user');
    if (userId == null || userId.isEmpty) {
      await refreshCounts();
      notifyListeners();
      return false;
    }
    currentUser = await db.getUser(userId);
    await refreshCounts();
    notifyListeners();
    return currentUser != null && bootstrapped;
  }

  /// Foydalanuvchi login/parol bilan kiradi (do'kon bootstrap bo'lgan bo'lishi kerak).
  Future<void> login(String login, String password) async {
    final storeId = _storeId;
    if (storeId == null || !bootstrapped) {
      throw const AuthException(
        "Do'kon ma'lumoti hali kelmagan. Egasi qurilmasi bu qurilmani tasdiqlashi va ma'lumot yuborishi kerak.",
      );
    }
    final user = await db.findUser(storeId, login);
    if (user == null) {
      throw const AuthException("Foydalanuvchi topilmadi. Login yoki do'kon ma'lumotini tekshiring.");
    }
    final ok = await verifyPassword(
      password,
      user['salt'] as String,
      user['pw_hash'] as String,
    );
    if (!ok) throw const AuthException("Login yoki parol noto'g'ri");
    await db.setState('session_user', user['id'] as String);
    currentUser = user;
    await refreshCounts();
    notifyListeners();
  }

  /// Yangi do'kon: shu qurilma egasi bo'ladi. Do'kon va egasi hisobi imzolanadi.
  Future<void> createStore({
    required String storeName,
    required String ownerName,
    required String login,
    required String password,
  }) async {
    final identity = await _loadIdentity();
    final storeId = const Uuid().v4();
    await keys.write(generateStoreKey());
    final deviceId = await db.deviceId();
    await db.initOwner(
      storeId: storeId,
      deviceId: deviceId,
      publicKeyHex: identity.publicKeyHex,
      label: 'egasi',
    );
    _storeId = storeId;
    this.storeName = storeName;
    final hash = await hashPassword(password);
    await _emit(
      await _signed(
        type: ops.opStore,
        payload: {'name': storeName},
      ),
    );
    await _emit(
      await _signed(
        type: ops.opUser,
        payload: {
          'id': const Uuid().v4(),
          'login': normalizeLogin(login),
          'name': ownerName,
          'role': ops.roleOwner,
          'salt': hash.salt,
          'pw_hash': hash.hash,
          'active': true,
        },
      ),
    );
    await db.setState('store_name', storeName);
    await db.setState(
      'session_user',
      (await db.findUser(storeId, normalizeLogin(login)))!['id'] as String,
    );
    await restore();
  }

  /// Juftlash kodi (store_id:owner_device_id:owner_pk:key). Egasi tasdig'i va ma'lumoti keyin keladi.
  Future<void> joinStore(String code) async {
    final (storeId, ownerDeviceId, ownerKey, keyHex) = parsePairingCode(code);
    await keys.importHex(keyHex);
    await db.setPairing(
      storeId: storeId,
      ownerDeviceId: ownerDeviceId,
      ownerPublicKeyHex: ownerKey,
    );
    _storeId = storeId;
    await _startMqtt();
    _startTimer();
    await refreshCounts();
    notifyListeners();
  }

  /// Juftlash kodi: faqat egasi qurilmasi beradi. Boshqalarda null.
  Future<String?> pairingCode() async {
    final storeId = _storeId;
    final identity = _identity;
    final key = await keys.read();
    if (storeId == null || identity == null || key == null) return null;
    if (!await db.isOwnerDevice(await db.deviceId())) return null;
    return makePairingCode(
      storeId,
      await db.deviceId(),
      identity.publicKeyHex,
      hexOf(key),
    );
  }

  // --- MQTT va sinxron ---------------------------------------------------------

  Future<void> _startMqtt() async {
    final key = await keys.read();
    if (key == null) {
      lastMessage = "Do'kon kaliti yo'q: juftlang";
      return;
    }
    await _mqtt?.stop();
    final mqtt = MqttSync(
      key: key,
      deviceId: await db.deviceId(),
      applyOp: _applyRemote,
      onRequest: (request) => unawaited(_onSnapshotRequest(request)),
      onJoinRequest: (request) => unawaited(_onJoinRequest(request)),
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
    } on Object catch (e) {
      connected = false;
      lastMessage = 'MQTT ulanmadi: $e';
    }
    await refreshCounts();
    notifyListeners();
  }

  Future<String> _applyRemote(Map<String, dynamic> op) async {
    final result = await db.applyOp(op);
    if (result == ops.resultApplied) {
      await refreshCounts();
      notifyListeners();
    }
    return result;
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
    await _requestBootstrapIfNeeded();
    await refreshCounts();
    notifyListeners();
  }

  /// Bootstrap bo'lmagan qurilma: tasdiq bo'lmasa join_request, tasdiq bo'lsa snapshot_request yuboradi.
  Future<void> _requestBootstrapIfNeeded() async {
    if (bootstrapped || _mqtt?.connected != true) return;
    if (DateTime.now().difference(_lastRequest) < const Duration(seconds: 15)) return;
    _lastRequest = DateTime.now();
    final approved = await _approved();
    final request = approved
        ? await _signed(type: ops.opSnapshotRequest, payload: {})
        : await _joinRequestOp();
    try {
      await _mqtt!.send(request);
    } on Object {
      // keyingi urinishda yuboriladi
    }
  }

  Future<bool> _approved() async {
    final row = await db.deviceRow(await db.deviceId());
    return row != null && row['active'] == true;
  }

  Future<Map<String, dynamic>> _joinRequestOp() async {
    final identity = await _loadIdentity();
    return ops.signedOp(
      identity,
      type: ops.opJoinRequest,
      storeId: storeId,
      deviceId: await db.deviceId(),
      payload: {
        'device_id': await db.deviceId(),
        'public_key': identity.publicKeyHex,
        'label': 'Telefon',
      },
    );
  }

  /// Egasi qurilmasi: snapshot_request kelganda, so'rovchi faol qurilma bo'lsa, snapshot yuboradi.
  Future<void> _onSnapshotRequest(Map<String, dynamic> request) async {
    final mqtt = _mqtt;
    if (mqtt == null || !mqtt.connected || _storeId == null) return;
    if (request['store_id'] != _storeId) return;
    if (!await db.isOwnerDevice(await db.deviceId())) return;
    if (!await db.isActiveDeviceOp(request)) return;
    final snapshot = await _signed(
      type: ops.opSnapshot,
      payload: await db.snapshotPayload(storeId),
    );
    try {
      await mqtt.send(snapshot);
    } on Object {
      // so'rovchi keyingi so'rovda qayta so'raydi
    }
  }

  /// Egasi qurilmasi: yangi qurilma so'radi. Tasdiqlash ro'yxatiga qo'shiladi (faqat egasi hisobi bilan).
  Future<void> _onJoinRequest(Map<String, dynamic> request) async {
    if (!canManage) return;
    if (!await db.verifyJoinRequest(request)) return;
    final id = (request['payload'] as Map<String, dynamic>)['device_id'] as String;
    if (_joinSeen.contains(id)) return;
    _joinSeen.add(id);
    joinRequests.add(request);
    notifyListeners();
  }

  /// Yangi qurilmani tasdiqlaydi (kassir yoki egasi sifatida) yoki rad etadi (ro'yxatdan olinadi).
  Future<void> approveJoin(Map<String, dynamic> request, {required String role}) async {
    if (!canManage) throw const AuthException("Faqat do'kon egasi uchun");
    final payload = request['payload'] as Map<String, dynamic>;
    joinRequests.remove(request);
    await _emit(
      await _signed(
        type: ops.opDevice,
        payload: {
          'device_id': payload['device_id'],
          'public_key': payload['public_key'],
          'role': role,
          'label': payload['label'] ?? '',
          'active': true,
        },
      ),
    );
    notifyListeners();
  }

  void rejectJoin(Map<String, dynamic> request) {
    joinRequests.remove(request);
    notifyListeners();
  }

  // --- operatsiyalar -------------------------------------------------------------

  /// Imzolangan operatsiya (shu qurilma nomidan).
  Future<Map<String, dynamic>> _signed({
    required String type,
    required Map<String, dynamic> payload,
    String? opId,
  }) async {
    final identity = await _loadIdentity();
    return ops.signedOp(
      identity,
      type: type,
      storeId: storeId,
      deviceId: await db.deviceId(),
      payload: payload,
      opId: opId,
    );
  }

  Future<DeviceIdentity> _loadIdentity() async {
    final existing = _identity;
    if (existing != null) return existing;
    final identity = await DeviceIdentity.fromSeed(await deviceSeeds.ensure());
    _identity = identity;
    return identity;
  }

  /// Lokal qo'llash; qoidaga zid bo'lsa xato; aks holda yuborish (yoki navbat).
  Future<void> _emit(Map<String, dynamic> op) async {
    final result = await db.applyOp(op);
    if (result == ops.resultRejected || result == ops.resultPending) {
      throw StateError("Amal do'kon qoidalariga zid yoki katalog hali to'liq emas");
    }
    if (result != ops.resultDuplicate) {
      await _publishOrQueue(op);
    }
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

  /// Navbat: PUBACK kelgan operatsiyalargina navbatdan o'chiriladi (K4).
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

  Future<void> openShift(int openingCash) async {
    final deviceId = await db.deviceId();
    if ((await db.openShiftForDevice(deviceId)) != null) {
      throw StateError('Bu qurilmada smena allaqachon ochiq');
    }
    final shiftId = const Uuid().v4();
    await _emit(
      await _signed(
        type: ops.opShiftOpen,
        payload: {'shift_id': shiftId, 'opening_cash': openingCash},
        opId: shiftId,
      ),
    );
  }

  /// Smenani yopadi. Hisobot qaytadi.
  Future<Map<String, dynamic>> closeShift(int closingCash) async {
    final shift = await db.openShiftForDevice(await db.deviceId());
    if (shift == null) throw StateError("Bu qurilmada ochiq smena yo'q");
    final summary = await db.shiftSummary(shift['id'] as String);
    await _emit(
      await _signed(
        type: ops.opShiftClose,
        payload: {
          'shift_id': shift['id'],
          'closing_cash': closingCash,
          'summary': summary,
        },
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
    final shift = await db.openShiftForDevice(await db.deviceId());
    if (shift == null) throw StateError('Avval bu qurilmada smenani oching');
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
    payload['created_at'] = ops.nowTs();
    await _emit(
      await _signed(
        type: ops.opSale,
        payload: payload,
        opId: payload['id'] as String,
      ),
    );
    return payload;
  }

  /// Chekni qaytarish (faqat egasi). Qaytarish o'z mahsulotlarini olib yuradi.
  Future<void> refund(String saleId) async {
    if (!canManage) throw const AuthException("Qaytarish faqat do'kon egasi uchun");
    final sale = await db.getSale(saleId);
    if (sale == null || sale['status'] != 'completed') {
      throw StateError('Bu chekni qaytarib bo\'lmaydi');
    }
    final items = [
      for (final i in (sale['payload'] as Map<String, dynamic>)['items'] as List)
        {
          'product_id': (i as Map<String, dynamic>)['product_id'],
          'qty': i['qty'],
        },
    ];
    await _emit(
      await _signed(
        type: ops.opRefund,
        payload: {'sale_id': saleId, 'items': items},
        opId: ops.refundOpId(saleId),
      ),
    );
  }

  Future<void> saveProduct(Map<String, dynamic> product) async {
    if (!canManage) throw const AuthException("Tovarni faqat do'kon egasi o'zgartiradi");
    await _emit(await _signed(type: ops.opProduct, payload: product));
  }

  Future<void> deleteProduct(Map<String, dynamic> product) async {
    await saveProduct({...product, 'deleted': true});
  }

  Future<void> refreshCounts() async {
    pending = await db.pendingCount();
    final id = _storeId;
    if (id != null) {
      final deviceId = await db.deviceId();
      shiftOpen = (await db.openShiftForDevice(deviceId)) != null;
      storeName = await db.storeName(id) ?? storeName;
      bootstrapped = await db.isBootstrapped();
      ownerDevice = await db.isOwnerDevice(deviceId);
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
    if (!canManage) throw const AuthException("Faqat do'kon egasi uchun");
    return db.listUsers(storeId);
  }

  /// Qurilmalar ro'yxati (egasi ko'radi).
  Future<List<Map<String, dynamic>>> devices() async {
    if (!canManage) throw const AuthException("Faqat do'kon egasi uchun");
    return db.listDevices(storeId);
  }

  /// Qurilmani bloklash/faollashtirish yoki rolini o'zgartirish (egasi qurilmasini emas).
  Future<void> setDeviceState(
    String deviceId, {
    bool? active,
    String? role,
  }) async {
    if (!canManage) throw const AuthException("Faqat do'kon egasi uchun");
    final row = await db.deviceRow(deviceId);
    if (row == null) throw const AuthException('Qurilma topilmadi');
    if (row['role'] == ops.roleOwner) {
      throw const AuthException("Egasi qurilmasini o'zgartirib bo'lmaydi");
    }
    await _emit(
      await _signed(
        type: ops.opDevice,
        payload: {
          'device_id': row['device_id'],
          'public_key': row['public_key'],
          'role': role ?? row['role'],
          'label': row['label'],
          'active': active ?? row['active'],
        },
      ),
    );
  }

  /// Yangi kassir. Parol xeshi va tuz qurilmada hisoblanadi, matn hech qayerga yuborilmaydi.
  Future<void> addCashier({
    required String name,
    required String login,
    required String password,
  }) async {
    if (!canManage) throw const AuthException("Faqat do'kon egasi uchun");
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
      await _signed(
        type: ops.opUser,
        payload: {
          'id': const Uuid().v4(),
          'login': cleanLogin,
          'name': cleanName,
          'role': ops.roleCashier,
          'salt': hash.salt,
          'pw_hash': hash.hash,
          'active': true,
        },
      ),
    );
  }

  /// Kassirni faollashtirish yoki o'chirish (egasini emas).
  Future<void> setUserActive(String userId, {required bool active}) async {
    if (!canManage) throw const AuthException("Faqat do'kon egasi uchun");
    final row = await db.getUser(userId);
    if (row == null) throw const AuthException('Foydalanuvchi topilmadi');
    if (row['role'] == ops.roleOwner) {
      throw const AuthException("Do'kon egasini o'chirib bo'lmaydi");
    }
    await _emit(
      await _signed(
        type: ops.opUser,
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
