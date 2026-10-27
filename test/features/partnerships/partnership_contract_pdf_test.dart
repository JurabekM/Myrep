import 'dart:convert';
import 'dart:io';

import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_contract_pdf.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const doc = PartnershipContractDoc(
  title: 'Sheriklik shartnomasi',
  subtitle: 'Tikuvchilik sexi · Mudoraba',
  partiesHeading: 'Tomonlar va kapital',
  partyHeaders: ['Ism', 'Rol', 'Kapital', 'Foyda ulushi'],
  partyRows: [
    ['Gʻayrat', 'Kapital egasi', '30 000 000 soʻm', '40 %'],
    ['Dilnoza', 'Mehnat egasi', '0 soʻm', '60 %'],
  ],
  capitalLines: ['Gʻayrat: Tikuv mashinasi (Uskuna) — 30 000 000 soʻm'],
  termsHeading: 'Shartlar',
  terms: [
    ('Turi', 'Mudoraba'),
    ('Versiya', '2'),
    ('Muddat (oy)', '12'),
  ],
  note: 'Sheriklik — sadaqa ham, qarz ham emas.',
  warning: 'Shablon hali tekshirilmagan.',
  signaturesHeading: 'Imzolar',
  signatures: [
    PdfSignature(role: 'Sherik', name: 'Gʻayrat'),
    PdfSignature(role: 'Sherik', name: 'Dilnoza'),
    PdfSignature(role: 'Guvoh', name: 'Shoʼba', signedAt: '10.10.2026'),
  ],
  footer: 'Baraka Dastur · 10.10.2026',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PdfFonts fonts;
  setUpAll(() async => fonts = await PdfFonts.load(rootBundle));

  test('shartnoma PDF yaratiladi, shrift ichida, matn qidiriladi', () async {
    final pdf = await buildPartnershipContractPdf(fonts, doc);
    final text = String.fromCharCodes(pdf);
    expect(text, startsWith('%PDF'));
    expect(text, contains('/ToUnicode'));
    expect(text, contains('/FontFile2'));
  });

  test(
    'sheriklik va daftar matnlarining barcha belgilari shriftda bor (uz, ru)',
    () {
      for (final lang in ['uz', 'ru']) {
        final arb =
            jsonDecode(
                  File('lib/app/l10n/arb/app_$lang.arb').readAsStringSync(),
                )
                as Map<String, dynamic>;
        final all = [
          for (final MapEntry(:key, :value) in arb.entries)
            if (value is String &&
                [
                  'pn',
                  'ledger',
                  'offer',
                  'idea',
                  'scenario',
                  'skill',
                ].any(key.startsWith))
              value,
        ].join();
        expect(all, isNotEmpty);
        expect(fonts.supports(all), isTrue, reason: lang);
      }
    },
  );
}
