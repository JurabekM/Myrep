import 'dart:typed_data';

import 'package:baraka_daftari/core/security/integrity/integrity_service.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:crypto/crypto.dart';

class FakeClock implements Clock {
  FakeClock([DateTime? start])
    : _now = start ?? DateTime.utc(2026, 10, 9, 9); // juma, Toshkent 14:00

  DateTime _now;

  @override
  DateTime nowUtc() => _now;

  void advance(Duration d) => _now = _now.add(d);

  /// Aniq vaqtga o'tkazish (UTC).
  void setNow(DateTime utc) => _now = utc.toUtc();
}

/// Widget testlarida haqiqiy fayl IO oʻrniga (fake-async zonasida IO
/// tugamaydi). Haqiqiy fayl yozuvi alohida unit testda tekshiriladi.
class RecordingIntegrityLog extends IntegrityLog {
  RecordingIntegrityLog(Clock clock)
    : super(() => throw UnsupportedError('fayl yoʻq'), clock);

  final List<Set<IntegrityRisk>> entries = [];

  @override
  Future<void> append(Set<IntegrityRisk> risks) async => entries.add(risks);
}

class InMemorySecureBlobStore implements SecureBlobStore {
  final Map<String, Uint8List> blobs = {};

  @override
  Future<Uint8List?> read(String name) async => blobs[name];

  @override
  Future<void> write(String name, Uint8List data) async =>
      blobs[name] = Uint8List.fromList(data);

  @override
  Future<void> delete(String name) async => blobs.remove(name);
}

/// RFC 8018 PBKDF2-HMAC-SHA256 — Kotlin implementatsiyasi bilan bir xil
/// natija beradigan etalon (KAT testi bilan tasdiqlangan).
Uint8List pbkdf2Sha256(
  List<int> password,
  List<int> salt,
  int iterations,
  int length,
) {
  final hmac = Hmac(sha256, password);
  final out = BytesBuilder(copy: false);
  for (var block = 1; out.length < length; block++) {
    var u = hmac.convert([
      ...salt,
      (block >> 24) & 0xff,
      (block >> 16) & 0xff,
      (block >> 8) & 0xff,
      block & 0xff,
    ]).bytes;
    final t = List<int>.of(u);
    for (var i = 1; i < iterations; i++) {
      u = hmac.convert(u).bytes;
      for (var j = 0; j < t.length; j++) {
        t[j] ^= u[j];
      }
    }
    out.add(t);
  }
  return Uint8List.sublistView(out.toBytes(), 0, length);
}

/// Haqiqiy algoritm, lekin testda iteratsiyalar soni qanday berilsa shunday.
/// [calls] — necha marta hisoblangani (lockout paytida hisoblanmasligini
/// tekshirish uchun).
class ReferencePinHasher implements PinHasher {
  int calls = 0;
  final List<int> iterationsSeen = [];

  @override
  Future<Uint8List> derive(String pin, Uint8List salt, int iterations) async {
    calls++;
    iterationsSeen.add(iterations);
    // Testlar tez boʻlishi uchun hisob 1 000 iteratsiyaga cheklanadi;
    // haqiqiy son yozuvga baribir oʻzgarmasdan tushadi.
    return pbkdf2Sha256(pin.codeUnits, salt, iterations.clamp(1, 1000), 32);
  }
}
