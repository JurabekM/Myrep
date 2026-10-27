import 'dart:convert';
import 'dart:typed_data';

import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'secure_blob_store.g.dart';

/// Keystore kaliti bilan shifrlangan kichik blob'lar (PIN yozuvi, lockout
/// holati, xavfsizlik sozlamalari).
abstract interface class SecureBlobStore {
  Future<Uint8List?> read(String name);
  Future<void> write(String name, Uint8List data);
  Future<void> delete(String name);
}

class NativeSecureBlobStore implements SecureBlobStore {
  const NativeSecureBlobStore(this._api);

  final SecurityApi _api;

  @override
  Future<Uint8List?> read(String name) => _api.readSecureBlob(name);

  @override
  Future<void> write(String name, Uint8List data) =>
      _api.writeSecureBlob(name, data);

  @override
  Future<void> delete(String name) => _api.deleteSecureBlob(name);
}

extension SecureBlobStoreJson on SecureBlobStore {
  Future<Map<String, dynamic>?> readJson(String name) async {
    final bytes = await read(name);
    if (bytes == null) return null;
    return jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
  }

  Future<void> writeJson(String name, Map<String, dynamic> json) =>
      write(name, Uint8List.fromList(utf8.encode(jsonEncode(json))));
}

@Riverpod(keepAlive: true)
SecureBlobStore secureBlobStore(Ref ref) =>
    NativeSecureBlobStore(ref.watch(securityApiProvider));
