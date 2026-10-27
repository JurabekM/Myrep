import 'dart:typed_data';

import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:meta/meta.dart';

/// Sheriklik shartnomasi hujjati (matnlar ARB'dan, summalar formatlangan).
@immutable
final class PartnershipContractDoc {
  const PartnershipContractDoc({
    required this.title,
    required this.subtitle,
    required this.partiesHeading,
    required this.partyHeaders,
    required this.partyRows,
    required this.capitalLines,
    required this.termsHeading,
    required this.terms,
    required this.note,
    required this.signaturesHeading,
    required this.signatures,
    required this.footer,
    this.warning,
  });

  final String title;
  final String subtitle;
  final String partiesHeading;

  /// Ism, rol, kapital, foyda ulushi.
  final List<String> partyHeaders;
  final List<List<String>> partyRows;

  /// «Ism: uskuna — narxi» qatorlari.
  final List<String> capitalLines;
  final String termsHeading;

  /// «Band: matn» qatorlari (tur, muddat, zarar qoidasi, nizolar …).
  final List<(String, String)> terms;
  final String note;

  /// Shablon hali tekshirilmagan bo'lsa — ogohlantirish.
  final String? warning;
  final String signaturesHeading;
  final List<PdfSignature> signatures;
  final String footer;
}

/// Sheriklik shartnomasi PDF'i (`core/pdf`): tomonlar, kapital, shartlar,
/// izoh va imzolar.
Future<Uint8List> buildPartnershipContractPdf(
  PdfFonts fonts,
  PartnershipContractDoc d,
) => BarakaPdf.build(
  fonts: fonts,
  title: d.title,
  subtitle: d.subtitle,
  footer: d.footer,
  blocks: [
    if (d.warning != null) PdfNote(d.warning!),
    PdfHeading(d.partiesHeading),
    PdfTable(
      headers: d.partyHeaders,
      rows: d.partyRows,
      numericColumns: const {2, 3},
    ),
    for (final line in d.capitalLines) PdfParagraph(line),
    PdfHeading(d.termsHeading),
    PdfKeyValues(d.terms),
    PdfNote(d.note),
    PdfHeading(d.signaturesHeading),
    PdfSignatures(d.signatures),
  ],
);
