import 'dart:typed_data';

final _hex = RegExp(r'^(?:[0-9a-fA-F]{2})*$');

String hexEncode(List<int> bytes) => bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

Uint8List hexDecode(String hex) {
  if (!_hex.hasMatch(hex)) throw FormatException('Hex emas', hex);
  return Uint8List.fromList([for (var i = 0; i < hex.length; i += 2) int.parse(hex.substring(i, i + 2), radix: 16)]);
}
