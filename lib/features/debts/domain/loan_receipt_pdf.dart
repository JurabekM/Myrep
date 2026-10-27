import 'dart:typed_data';

import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:meta/meta.dart';

/// Qarz tilxati hujjati (matnlar tayyor — ARB'dan; summalar formatlangan).
@immutable
final class LoanReceiptDoc {
  const LoanReceiptDoc({
    required this.title,
    required this.subtitle,
    required this.partiesHeading,
    required this.details,
    required this.planHeading,
    required this.planHeaders,
    required this.planRows,
    required this.note,
    required this.signaturesHeading,
    required this.signatures,
    required this.footer,
  });

  final String title;
  final String subtitle;
  final String partiesHeading;

  /// «Belgi: qiymat» qatorlari (tomonlar, summa, muddat, sabab).
  final List<(String, String)> details;
  final String planHeading;
  final List<String> planHeaders;
  final List<List<String>> planRows;

  /// «Shaxsiy hisob uchun yozuv, yuridik kafolat emas» (SPEC 2D.5).
  final String note;
  final String signaturesHeading;
  final List<PdfSignature> signatures;
  final String footer;
}

/// Qarz tilxati PDF'i (`core/pdf`): tomonlar, to'lov rejasi, izoh, imzolar.
Future<Uint8List> buildLoanReceiptPdf(PdfFonts fonts, LoanReceiptDoc d) =>
    BarakaPdf.build(
      fonts: fonts,
      title: d.title,
      subtitle: d.subtitle,
      footer: d.footer,
      blocks: [
        PdfHeading(d.partiesHeading),
        PdfKeyValues(d.details),
        PdfHeading(d.planHeading),
        PdfTable(
          headers: d.planHeaders,
          rows: d.planRows,
          numericColumns: {
            for (var i = 1; i < d.planHeaders.length; i++) i,
          },
        ),
        PdfNote(d.note),
        PdfHeading(d.signaturesHeading),
        PdfSignatures(d.signatures),
      ],
    );
