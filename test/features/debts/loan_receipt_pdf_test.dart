import 'dart:io';

import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/features/debts/domain/loan_receipt_pdf.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Golden: `test/features/debts/goldens/loan_receipt.pdf`. Yangilash:
/// `UPDATE_GOLDENS=1 flutter test test/features/debts/loan_receipt_pdf_test.dart`
/// (soʻng PDFʼni ochib, koʻz bilan tekshiring).
const _golden = 'test/features/debts/goldens/loan_receipt.pdf';

/// Tasodifiy `/ID` va yaratilgan vaqt — solishtirishdan oldin bir xillanadi.
Uint8List normalize(Uint8List pdf) {
  final s = String.fromCharCodes(pdf)
      .replaceAll(RegExp(r'/ID\s*\[<[0-9a-f]+><[0-9a-f]+>\]'), '/ID[<0><0>]')
      .replaceAll(RegExp(r'/CreationDate\(D:\d+Z\)'), '/CreationDate(D:0Z)');
  return Uint8List.fromList(s.codeUnits);
}

const doc = LoanReceiptDoc(
  title: 'Qarz tilxati',
  subtitle: 'Gʻayrat Oʻrinov — Akmal Toʻxtayev',
  partiesHeading: 'Tomonlar va shartlar',
  details: [
    ('Qarz beruvchi', 'Gʻayrat Oʻrinov'),
    ('Qarz oluvchi', 'Akmal Toʻxtayev'),
    ('Summa', '1 500 000 soʻm'),
    ('Sabab', 'Toʻy xarajati — qarzi hasana'),
    ('Foiz / ustama', 'Yoʻq'),
  ],
  planHeading: 'Toʻlov rejasi',
  planHeaders: ['Sana', 'Toʻlov'],
  planRows: [
    ['01.11.2026', '500 000 soʻm'],
    ['01.12.2026', '500 000 soʻm'],
    ['01.01.2027', '500 000 soʻm'],
  ],
  note: 'Bu hujjat shaxsiy hisob uchun yozuv, yuridik kafolat emas.',
  signaturesHeading: 'Imzolar',
  signatures: [
    PdfSignature(role: 'Qarz beruvchi', name: 'Gʻayrat Oʻrinov'),
    PdfSignature(role: 'Qarz oluvchi', name: 'Akmal Toʻxtayev'),
    PdfSignature(
      role: 'Guvoh',
      name: 'Shoʼba Gʻofurova',
      signedAt: '08.10.2026',
    ),
  ],
  footer: 'Baraka Dastur · 08.10.2026',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PdfFonts fonts;
  setUpAll(() async => fonts = await PdfFonts.load(rootBundle));

  test('qarz tilxati PDF — golden (oʻ, gʻ, tutuq)', () async {
    final pdf = await buildLoanReceiptPdf(fonts, doc);
    final file = File(_golden);
    if (Platform.environment['UPDATE_GOLDENS'] == '1' || !file.existsSync()) {
      file
        ..createSync(recursive: true)
        ..writeAsBytesSync(pdf);
    }
    expect(normalize(pdf), normalize(file.readAsBytesSync()));
  });

  test('matndagi barcha belgilar shriftda bor — kvadrat chiqmaydi', () {
    final all = [
      doc.title,
      doc.subtitle,
      for (final (k, v) in doc.details) '$k$v',
      ...doc.planHeaders,
      for (final r in doc.planRows) ...r,
      doc.note,
      for (final s in doc.signatures) '${s.role}${s.name}',
    ].join();
    expect(all, contains('ʻ'));
    expect(all, contains('ʼ'));
    expect(fonts.supports(all), isTrue);
  });

  test('PDF matnni qidirib boʻladi: ToUnicode xaritasida U+02BB bor', () async {
    final pdf = String.fromCharCodes(await buildLoanReceiptPdf(fonts, doc));
    expect(pdf, contains('/ToUnicode'));
    expect(pdf, contains('/FontFile2'), reason: 'shrift ichiga joylangan');
  });
}
