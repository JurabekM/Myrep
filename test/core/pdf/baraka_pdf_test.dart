import 'dart:io';

import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Namuna PDF: `PDF_SAMPLE_OUT=fayl.pdf flutter test test/core/pdf` —
/// koʻz bilan tekshirish uchun yozib qoʻyiladi.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PdfFonts fonts;

  setUpAll(() async => fonts = await PdfFonts.load(rootBundle));

  const uzbek =
      'Oʻzbekiston, gʻalla, maʼlumot, taʼlim, qoʻshni — OʻZBEK GʻAYRAT. '
      'Kirill: Ўзбекистон, қарз, ғалла, ҳисоб. '
      '«Qoʻshtirnoq» va −15 000 soʻm, € ₽.';

  test('shrift oʻ, gʻ (U+02BB), tutuq (U+02BC) va kirillni qoʻllaydi', () {
    expect(fonts.supports(uzbek), isTrue);
    expect(fonts.supports('ʻʼ'), isTrue);
    // Nazorat: shriftda yoʻq belgi (CJK) aniqlanadi.
    expect(fonts.supports('漢'), isFalse);
  });

  test('PDF quriladi: sarlavha, matn, jadval, izoh, imzo bloklari', () async {
    final bytes = await BarakaPdf.build(
      fonts: fonts,
      title: 'Qarz tilxati',
      subtitle: 'Shaxsiy hisob uchun yozuv',
      footer: 'Baraka Dastur · 07.10.2026',
      blocks: [
        const PdfHeading('1. Tomonlar'),
        const PdfParagraph(uzbek),
        const PdfKeyValues([
          ('Qarz beruvchi', 'Hamid aka'),
          ('Qarz oluvchi', 'Akmal Toʻxtayev'),
          ('Summa', '1 500 000 soʻm'),
        ]),
        const PdfTable(
          headers: ['Sana', 'Toʻlov', 'Qoldiq'],
          rows: [
            ['01.11.2026', '500 000 soʻm', '1 000 000 soʻm'],
            ['01.12.2026', '500 000 soʻm', '500 000 soʻm'],
          ],
          numericColumns: {1, 2},
        ),
        const PdfNote(
          'Bu hujjat shaxsiy hisob uchun yozuv, yuridik kafolat emas.',
        ),
        const PdfSignatures([
          PdfSignature(role: 'Qarz beruvchi', name: 'Hamid aka'),
          PdfSignature(
            role: 'Guvoh',
            name: 'Gʻayrat Oʻrinov',
            signedAt: '07.10.2026',
          ),
        ]),
      ],
    );
    expect(String.fromCharCodes(bytes.take(5)), '%PDF-');
    final raw = String.fromCharCodes(bytes);
    // Shrift PDF ichiga joylangan (tashqi shriftga tayanmaydi).
    expect(raw, contains('/FontFile2'));
    expect(raw, contains('Baraka Dastur'));

    final out = Platform.environment['PDF_SAMPLE_OUT'];
    if (out != null) File(out).writeAsBytesSync(bytes);
  });
}
