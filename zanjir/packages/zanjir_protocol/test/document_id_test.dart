import 'dart:convert';
import 'dart:typed_data';

import 'package:test/test.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

Uint8List pdfWith(String trailer) => Uint8List.fromList(latin1.encode('%PDF-1.7\n1 0 obj<<>>endobj\n$trailer\n%%EOF'));

void main() {
  final a = 'a' * 64, b = 'b' * 64, id = '0123456789abcdef' * 4;

  test('ikkala qism almashtiriladi, uzunlik o\'zgarmaydi', () {
    final src = pdfWith('<</Size 2/ID[<$a><$b>]>>');
    final out = patchDocumentId(src, id);
    expect(out.length, src.length);
    expect(latin1.decode(out), contains('/ID[<$id><$id>]'));
    expect(pdfDocumentId(out), id);
    expect(latin1.decode(src), contains(a), reason: 'manba o\'zgarmaydi');
  });

  test('bo\'shliqli va katta harfli /ID ham topiladi', () {
    final out = patchDocumentId(pdfWith('/ID [ <${a.toUpperCase()}> <$b> ]'), id);
    expect(pdfDocumentId(out), id);
  });

  test('/ID yo\'q yoki bir nechta — xato', () {
    expect(() => patchDocumentId(pdfWith('<</Size 2>>'), id), throwsStateError);
    expect(() => patchDocumentId(pdfWith('/ID[<$a><$b>] /ID[<$a><$b>]'), id), throwsStateError);
  });

  test('id formati qat\'iy', () {
    final src = pdfWith('/ID[<$a><$b>]');
    for (final bad in ['', 'A' * 64, 'a' * 63, 'g' * 64]) {
      expect(() => patchDocumentId(src, bad), throwsArgumentError, reason: bad);
    }
  });

  test('pdfDocumentId: qismlar teng emas yoki /ID yo\'q → null', () {
    expect(pdfDocumentId(pdfWith('/ID[<$a><$b>]')), isNull);
    expect(pdfDocumentId(pdfWith('<<>>')), isNull);
    expect(pdfDocumentId(pdfWith('/ID[<$a><$a>]')), a);
  });
}
