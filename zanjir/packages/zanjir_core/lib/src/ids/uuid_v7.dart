import 'dart:math';

final Random _secure = Random.secure();

/// UUIDv7 (RFC 9562): 48 bit Unix millisekund + 74 bit tasodifiy.
String uuidV7({DateTime? now, Random? random}) {
  final rnd = random ?? _secure;
  final ms = (now ?? DateTime.now()).millisecondsSinceEpoch;
  final b = List<int>.generate(16, (_) => rnd.nextInt(256));
  for (var i = 0; i < 6; i++) {
    b[i] = (ms >> (8 * (5 - i))) & 0xff;
  }
  b[6] = 0x70 | (b[6] & 0x0f);
  b[8] = 0x80 | (b[8] & 0x3f);
  final hex = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-'
      '${hex.substring(16, 20)}-${hex.substring(20)}';
}
