import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

import 'hex.dart';

/// `sig_alg` har bir yozuvda saqlanadi — kelajakda ML-DSA gibrid yoki E-IMZO'ga o'tish sxemani buzmaydi.
const String sigAlgEd25519 = 'Ed25519';
const Set<String> supportedSigAlgs = {sigAlgEd25519};

final _ed25519 = Ed25519();

class UnsupportedSigAlgException implements Exception {
  const UnsupportedSigAlgException(this.sigAlg);
  final String sigAlg;

  @override
  String toString() => 'UnsupportedSigAlgException: $sigAlg';
}

/// Qurilma imzolovchisi. Ilovada maxfiy kalit Android Keystore himoyasida saqlanadi (4/6-faza).
abstract interface class Signer {
  String get sigAlg;
  String get publicKeyHex;
  Future<Uint8List> sign(List<int> message);
}

class Ed25519Signer implements Signer {
  Ed25519Signer._(this._keyPair, this.publicKeyHex);

  final SimpleKeyPair _keyPair;

  @override
  final String publicKeyHex;

  @override
  String get sigAlg => sigAlgEd25519;

  static Future<Ed25519Signer> fromSeed(List<int> seed) async {
    if (seed.length != 32) throw ArgumentError.value(seed.length, 'seed', 'Ed25519 seed 32 bayt bo\'lishi kerak');
    return _of(await _ed25519.newKeyPairFromSeed(seed));
  }

  static Future<Ed25519Signer> generate() async => _of(await _ed25519.newKeyPair());

  static Future<Ed25519Signer> _of(SimpleKeyPair kp) async =>
      Ed25519Signer._(kp, hexEncode((await kp.extractPublicKey()).bytes));

  @override
  Future<Uint8List> sign(List<int> message) async =>
      Uint8List.fromList((await _ed25519.sign(message, keyPair: _keyPair)).bytes);
}

/// Imzo to'g'rimi. Noma'lum algoritm — [UnsupportedSigAlgException]; noto'g'ri format — false.
Future<bool> verifySignature({
  required String sigAlg,
  required String publicKeyHex,
  required List<int> message,
  required String signatureHex,
}) async {
  if (!supportedSigAlgs.contains(sigAlg)) throw UnsupportedSigAlgException(sigAlg);
  final List<int> publicKey;
  final List<int> signature;
  try {
    publicKey = hexDecode(publicKeyHex);
    signature = hexDecode(signatureHex);
  } on FormatException {
    return false;
  }
  if (publicKey.length != 32 || signature.length != 64) return false;
  return _ed25519.verify(
    message,
    signature: Signature(signature, publicKey: SimplePublicKey(publicKey, type: KeyPairType.ed25519)),
  );
}
