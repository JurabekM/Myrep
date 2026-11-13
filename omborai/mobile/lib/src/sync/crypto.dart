import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// Do'kon kaliti bilan shifrlash: AES-256-GCM. Mavzu nomi HKDF-SHA256 orqali. Desktop bilan bir xil format
/// (docs/sync-mqtt.md): `{"v":1,"n":<nonce b64>,"c":<ciphertext+tag b64>}`, AAD = mavzu nomi.
const keyBytes = 32;
const topicPrefix = 'omborai/v1';

class DecryptionException implements Exception {
  DecryptionException([this.message = "Xabarni ochib bo'lmadi"]);

  final String message;

  @override
  String toString() => 'DecryptionException: $message';
}

final _aes = AesGcm.with256bits();

Uint8List generateStoreKey() {
  final random = Random.secure();
  return Uint8List.fromList(
    List<int>.generate(keyBytes, (_) => random.nextInt(256)),
  );
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
  return '$topicPrefix/${_hex(bytes)}/ops';
}

String _hex(List<int> bytes) =>
    bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

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
    'v': 1,
    'n': base64.encode(nonce),
    'c': base64.encode([...box.cipherText, ...box.mac.bytes]),
  };
  return Uint8List.fromList(utf8.encode(jsonEncode(envelope)));
}

Future<Map<String, dynamic>> openEnvelope(
  Uint8List key,
  Uint8List raw,
  String topic,
) async {
  _checkKey(key);
  try {
    final envelope = jsonDecode(utf8.decode(raw)) as Map<String, dynamic>;
    if (envelope['v'] != 1) {
      throw DecryptionException("Noma'lum protokol versiyasi");
    }
    final nonce = base64.decode(envelope['n'] as String);
    final combined = base64.decode(envelope['c'] as String);
    if (combined.length < 16) throw DecryptionException();
    final cipherText = combined.sublist(0, combined.length - 16);
    final mac = combined.sublist(combined.length - 16);
    final plain = await _aes.decrypt(
      SecretBox(cipherText, nonce: nonce, mac: Mac(mac)),
      secretKey: SecretKey(key),
      aad: utf8.encode(topic),
    );
    return jsonDecode(utf8.decode(plain)) as Map<String, dynamic>;
  } on DecryptionException {
    rethrow;
  } catch (_) {
    throw DecryptionException();
  }
}
