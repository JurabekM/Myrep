import 'dart:convert';
import 'dart:typed_data';

final _hexId = RegExp(r'^[0-9a-f]{64}$');

/// `/ID[<a><b>]` — trailer'dagi fayl identifikatori (ISO 32000-1, 14.4). `pdf` paketi uni tasodifiy yozadi.
final _idPattern = RegExp(r'/ID\s*\[\s*<([0-9a-fA-F]{64})>\s*<([0-9a-fA-F]{64})>\s*\]');

/// Tasodifiy `/ID` ni `<id><id>` bilan almashtiradi (uzunlik bir xil — xref ofsetlari buzilmaydi).
/// `/ID` aynan bitta bo'lishi shart: aks holda PDF tuzilishi kutilganidan farq qiladi va xato beriladi.
Uint8List patchDocumentId(Uint8List pdf, String id) {
  if (!_hexId.hasMatch(id)) throw ArgumentError.value(id, 'id', '64 belgili kichik hex bo\'lishi kerak');
  final text = latin1.decode(pdf);
  final matches = _idPattern.allMatches(text).toList();
  if (matches.length != 1) throw StateError('PDF da /ID ${matches.length} marta uchradi (1 kutilgan)');
  final m = matches.single;
  final out = Uint8List.fromList(pdf);
  final ascii = latin1.encode(id);
  final first = text.indexOf('<', m.start) + 1;
  final second = text.indexOf('<', first + 64) + 1;
  out
    ..setRange(first, first + 64, ascii)
    ..setRange(second, second + 64, ascii);
  return out;
}

/// PDF dagi `/ID` (ikkala qismi teng bo'lsa) yoki `null`.
String? pdfDocumentId(Uint8List pdf) {
  final ms = _idPattern.allMatches(latin1.decode(pdf)).toList();
  if (ms.length != 1 || ms.single[1] != ms.single[2]) return null;
  return ms.single[1]!.toLowerCase();
}
