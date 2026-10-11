import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// Protokol v2 kriptografiyasi (docs/sync-mqtt.md, 2, 4, 5-bo'lim). Desktop `crypto.py` bilan bir xil baytlar.
///
/// Konvert: `{"v":2,"n":<nonce b64>,"c":<ciphertext+tag b64>}`, AES-256-GCM, kalit = do'kon kaliti,
/// AAD = mavzu nomi. Imzo: Ed25519 (qurilma kaliti) canonical JSON ustida.
const keyBytes = 32;
const protocolVersion = 2;
const topicPrefix = 'omborai/v2';

class DecryptionException implements Exception {
  DecryptionException([this.message = "Xabarni ochib bo'lmadi"]);

  final String message;

  @override
  String toString() => 'DecryptionException: $message';
}

final _aes = AesGcm.with256bits();
final _ed25519 = Ed25519();

Uint8List generateStoreKey() => randomBytes(keyBytes);

Uint8List randomBytes(int n) {
  final random = Random.secure();
  return Uint8List.fromList(List<int>.generate(n, (_) => random.nextInt(256)));
}

void _checkKey(Uint8List key) {
  if (key.length != keyBytes) {
    throw ArgumentError("Do'kon kaliti 32 bayt bo'lishi kerak");
  }
}

Future<String> topicFor(Uint8List key) async {
  _checkKey(key);
  final hkdf = Hkdf(hmac: Hmac.sha256(), outputLength: 16);
  final derived = await hkdf.deriveKey(
    secretKey: SecretKey(key),
    nonce: Uint8List(32), // RFC 5869: salt berilmasa, HashLen nollari
    info: utf8.encode('topic'),
  );
  final bytes = await derived.extractBytes();
  return '$topicPrefix/${hexOf(bytes)}/ops';
}

String hexOf(List<int> bytes) =>
    bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

Uint8List fromHexBytes(String hex) {
  final out = Uint8List(hex.length ~/ 2);
  for (var i = 0; i < out.length; i++) {
    out[i] = int.parse(hex.substring(i * 2, i * 2 + 2), radix: 16);
  }
  return out;
}

// --- canonical JSON va imzo ---------------------------------------------------

Object? _sortDeep(Object? value) {
  if (value is Map) {
    final keys = value.keys.map((k) => k.toString()).toList()..sort();
    return {for (final k in keys) k: _sortDeep(value[k])};
  }
  if (value is List) return value.map(_sortDeep).toList();
  return value;
}

/// Imzo uchun baytlar: `sig` maydonisiz, kalitlari saralangan, bo'shliqsiz JSON (UTF-8).
Uint8List canonicalBytes(Map<String, dynamic> op) {
  final body = Map<String, dynamic>.from(op)..remove('sig');
  return Uint8List.fromList(utf8.encode(jsonEncode(_sortDeep(body))));
}

/// Qurilma kalitidan (32 bayt seed) imzolash kaliti.
Future<SimpleKeyPair> keyPairFromSeed(Uint8List seed) async {
  if (seed.length != 32) {
    throw ArgumentError('Qurilma kaliti 32 bayt bo\'lishi kerak');
  }
  return _ed25519.newKeyPairFromSeed(seed);
}

/// Ochiq kalit (hex, 32 bayt) — roster'da saqlanadi.
Future<String> publicKeyHexOf(SimpleKeyPair pair) async {
  final pub = await pair.extractPublicKey();
  return hexOf(pub.bytes);
}

/// Operatsiyaga imzo qo'yadi (`sig` maydoni, base64).
Future<void> signOp(Map<String, dynamic> op, SimpleKeyPair pair) async {
  final signature = await _ed25519.sign(canonicalBytes(op), keyPair: pair);
  op['sig'] = base64.encode(signature.bytes);
}

/// Imzo shu ochiq kalit bilan to'g'rimi.
Future<bool> verifyOp(Map<String, dynamic> op, String publicKeyHexValue) async {
  try {
    final sig = base64.decode(op['sig'] as String);
    final publicKey = SimplePublicKey(
      fromHexBytes(publicKeyHexValue),
      type: KeyPairType.ed25519,
    );
    return await _ed25519.verify(
      canonicalBytes(op),
      signature: Signature(sig, publicKey: publicKey),
    );
  } on Object {
    return false;
  }
}

// --- konvert -------------------------------------------------------------------

Future<Uint8List> seal(
  Uint8List key,
  Map<String, dynamic> message,
  String topic,
) async {
  _checkKey(key);
  final nonce = _aes.newNonce();
  final plain = utf8.encode(jsonEncode(message));
  final box = await _aes.encrypt(
    plain,
    secretKey: SecretKey(key),
    nonce: nonce,
    aad: utf8.encode(topic),
  );
  final envelope = {
    'v': protocolVersion,
    'n': base64.encode(nonce),
    'c': base64.encode([...box.cipherText, ...box.mac.bytes]),
  };
  return Uint8List.fromList(utf8.encode(jsonEncode(envelope)));
}

/// Konvertni ochadi. Har qanday xato (JSON, versiya, GCM, tur) DecryptionException bo'ladi.
Future<Map<String, dynamic>> openEnvelope(
  Uint8List key,
  Uint8List raw,
  String topic,
) async {
  _checkKey(key);
  try {
    final decoded = jsonDecode(utf8.decode(raw));
    if (decoded is! Map<String, dynamic> || decoded['v'] != protocolVersion) {
      throw DecryptionException("Noma'lum protokol versiyasi");
    }
    final nonce = base64.decode(decoded['n'] as String);
    final combined = base64.decode(decoded['c'] as String);
    if (combined.length < 16) throw DecryptionException();
    final cipherText = combined.sublist(0, combined.length - 16);
    final mac = combined.sublist(combined.length - 16);
    final plain = await _aes.decrypt(
      SecretBox(cipherText, nonce: nonce, mac: Mac(mac)),
      secretKey: SecretKey(key),
      aad: utf8.encode(topic),
    );
    final message = jsonDecode(utf8.decode(plain));
    if (message is! Map<String, dynamic>) throw DecryptionException();
    return message;
  } on DecryptionException {
    rethrow;
  } catch (_) {
    throw DecryptionException();
  }
}
