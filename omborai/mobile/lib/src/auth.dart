import 'dart:convert';
import 'dart:math';

import 'package:cryptography/cryptography.dart';

/// Lokal autentifikatsiya va juftlash kodi (serversiz rejim). Desktop `auth.py` bilan bir xil:
/// PBKDF2-HMAC-SHA256, 100 000 iteratsiya, 16 baytli tuz, 32 baytli natija.
/// Juftlash kodi: `<store_id>:<kalit hex>`.
const pbkdf2Iterations = 100000;
const _saltBytes = 16;

/// Parolning eng kam uzunligi (desktop `users.MIN_PASSWORD` bilan bir xil).
const minPasswordLength = 8;

final _uuidPattern = RegExp(
  r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
);
final _hex64 = RegExp(r'^[0-9a-f]{64}$');

/// Login yoki parol noto'g'ri, yoki foydalanuvchi topilmadi.
class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

class PasswordHash {
  const PasswordHash(this.salt, this.hash);

  /// Tuz (hex).
  final String salt;

  /// PBKDF2 natijasi (hex).
  final String hash;
}

Future<PasswordHash> hashPassword(String password, {String? saltHex}) async {
  final salt = saltHex == null ? _randomBytes(_saltBytes) : _fromHex(saltHex);
  final pbkdf2 = Pbkdf2(
    macAlgorithm: Hmac.sha256(),
    iterations: pbkdf2Iterations,
    bits: 256,
  );
  final key = await pbkdf2.deriveKey(
    secretKey: SecretKey(utf8.encode(password)),
    nonce: salt,
  );
  return PasswordHash(_toHex(salt), _toHex(await key.extractBytes()));
}

Future<bool> verifyPassword(
  String password,
  String saltHex,
  String hashHex,
) async {
  final candidate = await hashPassword(password, saltHex: saltHex);
  return _constantTimeEquals(candidate.hash, hashHex);
}

String normalizeLogin(String login) => login.trim().toLowerCase();

/// Juftlash kodi (v2): `<store_id>:<owner_device_id>:<owner_public_key_hex>:<store_key_hex>`.
/// Faqat egasi qurilmasi ko'rsatadi (docs/sync-mqtt.md, 3-bo'lim).
String makePairingCode(
  String storeId,
  String ownerDeviceId,
  String ownerPublicKeyHex,
  String keyHex,
) => '$storeId:$ownerDeviceId:$ownerPublicKeyHex:$keyHex';

/// Juftlash kodini tekshiradi: (store_id, owner_device_id, owner_public_key_hex, key_hex).
/// Noto'g'ri bo'lsa FormatException.
(String, String, String, String) parsePairingCode(String code) {
  final parts = code.trim().toLowerCase().split(':');
  if (parts.length != 4) {
    throw const FormatException("Juftlash kodi noto'g'ri formatda");
  }
  final storeId = parts[0];
  final ownerDeviceId = parts[1];
  final ownerKey = parts[2];
  final keyHex = parts[3];
  if (!_uuidPattern.hasMatch(storeId) || !_uuidPattern.hasMatch(ownerDeviceId)) {
    throw const FormatException("Juftlash kodida ID noto'g'ri");
  }
  if (!_hex64.hasMatch(ownerKey)) {
    throw const FormatException(
      "Juftlash kodida egasi kaliti noto'g'ri (64 belgi kerak)",
    );
  }
  if (!_hex64.hasMatch(keyHex)) {
    throw const FormatException(
      "Juftlash kodida do'kon kaliti noto'g'ri (64 belgi kerak)",
    );
  }
  return (storeId, ownerDeviceId, ownerKey, keyHex);
}

bool _constantTimeEquals(String a, String b) {
  if (a.length != b.length) return false;
  var diff = 0;
  for (var i = 0; i < a.length; i++) {
    diff |= a.codeUnitAt(i) ^ b.codeUnitAt(i);
  }
  return diff == 0;
}

List<int> _randomBytes(int n) {
  final random = Random.secure();
  return List<int>.generate(n, (_) => random.nextInt(256));
}

String _toHex(List<int> bytes) =>
    bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

List<int> _fromHex(String hex) {
  final out = <int>[];
  for (var i = 0; i < hex.length; i += 2) {
    out.add(int.parse(hex.substring(i, i + 2), radix: 16));
  }
  return out;
}
