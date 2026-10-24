import 'dart:math';

import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'uuid_v7.g.dart';

/// UUIDv7 generatori (RFC 9562). Barcha ID'lar shu formatda (SPEC 4.4).
///
/// Tuzilma: 48 bit Unix vaqti (ms) · versiya `7` · 12 bit hisoblagich ·
/// variant `10` · 62 bit tasodifiy.
///
/// Monotonlik (RFC 9562, 6.2-bo'lim, 1-usul): bir millisekund ichidagi
/// ID'lar 12 bitli hisoblagich bilan o'sib boradi; hisoblagich to'lsa vaqt
/// sun'iy ravishda 1 ms oldinga suriladi. Soat orqaga ketsa ham ID'lar
/// kamaymaydi. Natijada ID'lar matn sifatida ham tartiblanadi.
class UuidV7Generator {
  UuidV7Generator({required Clock clock, Random? random})
    : _clock = clock,
      _random = random ?? Random.secure();

  final Clock _clock;
  final Random _random;

  int _lastMs = -1;
  int _counter = 0;

  static const _counterMax = 0xFFF;

  String next() {
    var ms = _clock.nowUtc().millisecondsSinceEpoch;
    if (ms <= _lastMs) {
      ms = _lastMs;
      _counter++;
      if (_counter > _counterMax) {
        ms++;
        _counter = _randomCounterSeed();
      }
    } else {
      _counter = _randomCounterSeed();
    }
    _lastMs = ms;

    final bytes = List<int>.filled(16, 0);
    for (var i = 0; i < 6; i++) {
      bytes[i] = (ms >> (8 * (5 - i))) & 0xFF;
    }
    bytes[6] = 0x70 | ((_counter >> 8) & 0x0F);
    bytes[7] = _counter & 0xFF;
    bytes[8] = 0x80 | _random.nextInt(0x40);
    for (var i = 9; i < 16; i++) {
      bytes[i] = _random.nextInt(256);
    }
    return _format(bytes);
  }

  /// Hisoblagich past yarmidan boshlanadi — bir ms ichida kamida 2048 ta ID
  /// uchun joy qoladi.
  int _randomCounterSeed() => _random.nextInt(0x800);

  static String _format(List<int> b) {
    final hex = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-${hex.substring(16, 20)}-'
        '${hex.substring(20)}';
  }

  static final RegExp pattern = RegExp(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
  );

  /// ID ichidagi vaqt (ms aniqlik bilan).
  static DateTime timestampOf(String id) {
    final hex = id.replaceAll('-', '').substring(0, 12);
    return DateTime.fromMillisecondsSinceEpoch(
      int.parse(hex, radix: 16),
      isUtc: true,
    );
  }
}

@Riverpod(keepAlive: true)
UuidV7Generator idGenerator(Ref ref) =>
    UuidV7Generator(clock: ref.watch(clockProvider));
