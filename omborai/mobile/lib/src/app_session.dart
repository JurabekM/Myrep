import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api/api_client.dart';
import 'domain/cart.dart';
import 'offline/local_db.dart';
import 'offline/sync_service.dart';

/// Tokenlarni qurilmaning xavfsiz xotirasida saqlaydi (Android Keystore).
class SecureTokenStorage implements TokenStorage {
  SecureTokenStorage([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<Tokens?> read() async {
    final access = await _storage.read(key: 'access');
    final refresh = await _storage.read(key: 'refresh');
    if (access == null || refresh == null) return null;
    return Tokens(access, refresh);
  }

  @override
  Future<void> write(Tokens tokens) async {
    await _storage.write(key: 'access', value: tokens.access);
    await _storage.write(key: 'refresh', value: tokens.refresh);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: 'access');
    await _storage.delete(key: 'refresh');
  }
}

/// Savdo natijasi: serverda saqlangan yoki aloqa yo'qligi sababli navbatga qo'yilgan.
class SaleOutcome {
  const SaleOutcome._(this.saved, this.saleNumber, this.saleId);

  factory SaleOutcome.saved(Map<String, dynamic> sale) =>
      SaleOutcome._(true, sale['number'] as int?, sale['id'] as String);

  factory SaleOutcome.queued(String saleId) =>
      SaleOutcome._(false, null, saleId);

  final bool saved;
  final int? saleNumber;
  final String saleId;
}

/// Ilova holati: sessiya, do'kon, smena, aloqa va navbat.
class AppSession extends ChangeNotifier {
  AppSession({
    required this.api,
    required this.db,
    required this.tokens,
    this.syncInterval = const Duration(seconds: 15),
  }) : sync = SyncService(api, db) {
    api.onTokensChanged = (t) => unawaited(tokens.write(t));
  }

  final ApiClient api;
  final LocalDb db;
  final TokenStorage tokens;
  final SyncService sync;
  final Duration syncInterval;

  Timer? _timer;
  Map<String, dynamic>? store;
  Map<String, dynamic>? shift;
  String? storeName;
  String? _storeId;
  bool online = true;
  bool syncing = false;
  int pending = 0;
  int rejected = 0;
  DateTime? lastSync;
  String? lastMessage;

  bool get hasStore => _storeId != null;
  String get storeId => _storeId!;
  bool get shiftOpen => shift != null;

  /// Saqlangan sessiya bo'lsa, ilovani qayta ochadi. Aloqa bo'lmasa ham keshdan ishlaydi.
  Future<bool> restore() async {
    final saved = await tokens.read();
    if (saved == null) return false;
    api.restoreTokens(saved);
    _storeId = await db.getState('store_id');
    storeName = await db.getState('store_name');
    try {
      await _loadStoreAndShift();
    } on OfflineException {
      online = false;
    } on ApiException catch (e) {
      if (e.status == 401) {
        await logout();
        return false;
      }
    }
    _startTimer();
    await refreshCounts();
    notifyListeners();
    return true;
  }

  Future<void> login(String email, String password) async {
    await api.login(email, password);
    await _loadStoreAndShift();
    _startTimer();
    await refreshCounts();
    notifyListeners();
  }

  Future<void> _loadStoreAndShift() async {
    final stores = await api.stores();
    if (stores.isEmpty) throw ApiException(404, "Do'kon topilmadi");
    final first = stores.first;
    store = first;
    storeName = first['name'] as String;
    _storeId = first['id'] as String;
    await db.setState('store_id', _storeId!);
    await db.setState('store_name', storeName!);
    shift = await api.currentShift(_storeId!);
    online = true;
  }

  Future<void> reloadShift() async {
    if (!hasStore) return;
    shift = await api.currentShift(storeId);
    notifyListeners();
  }

  Future<void> openShift(int cash) async {
    shift = await api.openShift(storeId, cash);
    notifyListeners();
  }

  /// Smenani yopadi va natija hisobotini qaytaradi.
  Future<Map<String, dynamic>> closeShift(int cash) async {
    final current = shift;
    if (current == null) throw StateError('Ochiq smena yo\'q');
    final summary = await api.closeShift(current['id'] as String, cash);
    shift = null;
    notifyListeners();
    return summary;
  }

  /// Savdo: avval serverga; aloqa bo'lmasa navbatga. Server rad etsa, [ApiException] tashlanadi.
  Future<SaleOutcome> submitSale(Cart cart, String method) async {
    final payload = cart.toSalePayload(
      storeId: storeId,
      method: method,
      amount: cart.total,
    );
    try {
      final sale = await api.createSale(payload);
      online = true;
      await refreshCounts();
      return SaleOutcome.saved(sale);
    } on OfflineException {
      await db.enqueueSale(
        storeId,
        payload,
        createdAt: DateTime.now().toIso8601String(),
      );
      online = false;
      await refreshCounts();
      return SaleOutcome.queued(payload['id'] as String);
    }
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(syncInterval, (_) => unawaited(syncNow()));
  }

  Future<void> syncNow() async {
    if (!hasStore || syncing) return;
    syncing = true;
    notifyListeners();
    try {
      final report = await sync.runOnce(storeId);
      online = true;
      lastSync = DateTime.now();
      lastMessage = report.rejected > 0
          ? '${report.rejected} ta offline savdo serverda rad etildi'
          : null;
    } on OfflineException {
      online = false;
    } on ApiException catch (e) {
      lastMessage = e.message;
    } finally {
      syncing = false;
      await refreshCounts();
      notifyListeners();
    }
  }

  Future<void> refreshCounts() async {
    pending = await db.pendingCount();
    rejected = (await db.rejectedOps()).length;
  }

  Future<void> logout() async {
    _timer?.cancel();
    _timer = null;
    api.clearSession();
    await tokens.clear();
    store = null;
    shift = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

/// Lokal baza paroli: birinchi ishga tushirishda tasodifiy 256-bit yaratiladi va Keystore'da saqlanadi.
class DbPasswordStore {
  DbPasswordStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<String> load() async {
    final existing = await _storage.read(key: 'db_password');
    if (existing != null) return existing;
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    final password = base64Url.encode(bytes);
    await _storage.write(key: 'db_password', value: password);
    return password;
  }
}
