import 'dart:typed_data';

import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'pin_hasher.g.dart';

/// PIN → kalit hosilasi (PBKDF2-HMAC-SHA256).
// Interfeys: testlarda soxta implementatsiya bilan almashtiriladi.
// ignore: one_member_abstracts
abstract interface class PinHasher {
  Future<Uint8List> derive(String pin, Uint8List salt, int iterations);
}

/// Hosila Kotlin tomonda (`javax.crypto`, fon oqimida) hisoblanadi: 310 000
/// iteratsiya sof Dart'da telefonni bir necha soniya band qilardi.
class NativePinHasher implements PinHasher {
  const NativePinHasher(this._api);

  final SecurityApi _api;

  @override
  Future<Uint8List> derive(String pin, Uint8List salt, int iterations) =>
      _api.derivePinKey(pin, salt, iterations);
}

@Riverpod(keepAlive: true)
PinHasher pinHasher(Ref ref) => NativePinHasher(ref.watch(securityApiProvider));
