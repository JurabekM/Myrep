import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:zanjir_data/zanjir_data.dart' show ServerTokens, TokenStore;

/// Qurilmaning Ed25519 maxfiy kaliti (seed) uchun xotira. Kalit qurilmadan chiqmaydi va logga yozilmaydi.
abstract interface class DeviceKeyStore {
  Future<List<int>?> readSeed();
  Future<void> writeSeed(List<int> seed);
}

/// Android Keystore bilan himoyalangan xotira (`flutter_secure_storage`).
class SecureDeviceKeyStore implements DeviceKeyStore {
  SecureDeviceKeyStore([FlutterSecureStorage? storage]) : _storage = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _storage;
  static const _key = 'zanjir.device_seed.v1';

  @override
  Future<List<int>?> readSeed() async {
    final v = await _storage.read(key: _key);
    return v == null ? null : base64Decode(v);
  }

  @override
  Future<void> writeSeed(List<int> seed) => _storage.write(key: _key, value: base64Encode(seed));
}

/// Testlar uchun.
class MemoryDeviceKeyStore implements DeviceKeyStore {
  List<int>? _seed;

  @override
  Future<List<int>?> readSeed() async => _seed;

  @override
  Future<void> writeSeed(List<int> seed) async => _seed = List.unmodifiable(seed);
}

/// Server tokenlari Keystore bilan himoyalangan xotirada (`flutter_secure_storage`).
class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage]) : _storage = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _storage;
  static const _key = 'zanjir.server_tokens.v1';

  @override
  Future<ServerTokens?> read() async {
    final v = await _storage.read(key: _key);
    if (v == null) return null;
    final m = jsonDecode(v) as Map<String, Object?>;
    return ServerTokens(m['access']! as String, m['refresh']! as String);
  }

  @override
  Future<void> write(ServerTokens tokens) =>
      _storage.write(key: _key, value: jsonEncode({'access': tokens.access, 'refresh': tokens.refresh}));

  @override
  Future<void> clear() => _storage.delete(key: _key);
}
