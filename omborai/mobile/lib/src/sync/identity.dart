import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

import 'crypto.dart';

/// Qurilmaning Ed25519 kaliti: har bir operatsiyani shu qurilma imzolaydi (docs/sync-mqtt.md, 2-bo'lim).
/// Seed (32 bayt) xavfsiz xotirada (Keystore) saqlanadi; bu yerda faqat kalit juftligi.
class DeviceIdentity {
  DeviceIdentity._(this.keyPair, this.publicKeyHex);

  final SimpleKeyPair keyPair;

  /// Ochiq kalit (hex). Egasi roster'iga shu qiymat yoziladi.
  final String publicKeyHex;

  static Future<DeviceIdentity> fromSeed(Uint8List seed) async {
    final pair = await keyPairFromSeed(seed);
    return DeviceIdentity._(pair, await publicKeyHexOf(pair));
  }
}
