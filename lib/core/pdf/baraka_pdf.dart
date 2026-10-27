import 'package:flutter/services.dart';
import 'package:meta/meta.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

/// PDF uchun shriftlar (Noto Sans — `ʻ`, `ʼ`, kirill). Ilova ichidagi
/// assetlardan yuklanadi, tarmoq ishlatilmaydi.
@immutable
final class PdfFonts {
  const PdfFonts({
    required this.regular,
    required this.medium,
    required this.bold,
    required this.italic,
  });

  final pw.Font regular;
  final pw.Font medium;
  final pw.Font bold;
  final pw.Font italic;

  static const _dir = 'assets/fonts';

  static Future<PdfFonts> load(AssetBundle bundle) async {
    Future<pw.Font> font(String name) async =>
        pw.Font.ttf(await bundle.load('$_dir/NotoSans-$name.ttf'));
    return PdfFonts(
      regular: await font('Regular'),
      medium: await font('Medium'),
      bold: await font('Bold'),
      italic: await font('Italic'),
    );
  }

  /// Berilgan matndagi barcha belgilar shriftda bormi (yo'qlari PDF'da
  /// bo'sh kvadrat bo'lib chiqardi).
  bool supports(String text) {
    final glyphs = TtfParser((regular as pw.TtfFont).data).charToGlyphIndexMap;
    return text.runes.every((r) => r <= 0x20 || glyphs.containsKey(r));
  }
}

/// Hujjat bloklari.
sealed class PdfBlock {
  const PdfBlock();
}

final class PdfHeading extends PdfBlock {
  const PdfHeading(this.text);
  final String text;
}

final class PdfParagraph extends PdfBlock {
  const PdfParagraph(this.text);
  final String text;
}

/// «Belgi: qiymat» qatorlari (masalan, qarz tafsilotlari).
final class PdfKeyValues extends PdfBlock {
  const PdfKeyValues(this.rows);
  final List<(String, String)> rows;
}

final class PdfTable extends PdfBlock {
  const PdfTable({
    required this.headers,
    required this.rows,
    this.numericColumns = const {},
  });
  final List<String> headers;
  final List<List<String>> rows;

  /// O'ngga tekislanadigan ustunlar (summalar).
  final Set<int> numericColumns;
}

/// Ajratilgan izoh (masalan, «yuridik kafolat emas»).
final class PdfNote extends PdfBlock {
  const PdfNote(this.text);
  final String text;
}

@immutable
final class PdfSignature {
  const PdfSignature({
    required this.role,
    required this.name,
    this.image,
    this.signedAt,
  });

  /// «Qarz beruvchi», «Guvoh» …
  final String role;
  final String name;

  /// Ekranda chizilgan imzo (PNG). `null` — bo'sh joy qoldiriladi.
  final Uint8List? image;
  final String? signedAt;
}

final class PdfSignatures extends PdfBlock {
  const PdfSignatures(this.signatures);
  final List<PdfSignature> signatures;
}

/// Barcha hujjatlar (qarz tilxati, sheriklik shartnomasi, ledger hisoboti)
/// uchun umumiy PDF quruvchi (MVP_PLAN, Vazifa 3: `core/pdf`).
abstract final class BarakaPdf {
  static const _ink = PdfColor.fromInt(0xFF2B2A26);
  static const _muted = PdfColor.fromInt(0xFF6B655A);
  static const _rule = PdfColor.fromInt(0xFFD9CFB8);
  static const _paper = PdfColor.fromInt(0xFFF8F3E6);

  static Future<Uint8List> build({
    required PdfFonts fonts,
    required String title,
    required List<PdfBlock> blocks,
    String? subtitle,

    /// Har sahifa pastida (masalan, «Baraka Dastur · 07.10.2026»).
    String? footer,

    /// Sahifa raqami formati: (joriy, jami) → matn.
    String Function(int page, int total)? pageLabel,
  }) async {
    final doc =
        pw.Document(
          title: title,
          creator: 'Baraka Dastur',
          producer: 'Baraka Dastur',
          theme: pw.ThemeData.withFont(
            base: fonts.regular,
            bold: fonts.bold,
            italic: fonts.italic,
            boldItalic: fonts.bold,
          ),
        )..addPage(
          pw.MultiPage(
            pageFormat: PdfPageFormat.a4,
            margin: const pw.EdgeInsets.fromLTRB(48, 48, 48, 40),
            header: (context) => context.pageNumber == 1
                ? pw.SizedBox()
                : pw.Text(
                    title,
                    style: const pw.TextStyle(color: _muted, fontSize: 9),
                  ),
            footer: (context) => pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text(
                  footer ?? '',
                  style: const pw.TextStyle(color: _muted, fontSize: 9),
                ),
                pw.Text(
                  pageLabel?.call(context.pageNumber, context.pagesCount) ??
                      '${context.pageNumber} / ${context.pagesCount}',
                  style: const pw.TextStyle(color: _muted, fontSize: 9),
                ),
              ],
            ),
            build: (context) => [
              pw.Text(
                title,
                style: pw.TextStyle(
                  font: fonts.bold,
                  fontSize: 20,
                  color: _ink,
                ),
              ),
              if (subtitle != null) ...[
                pw.SizedBox(height: 4),
                pw.Text(
                  subtitle,
                  style: const pw.TextStyle(color: _muted, fontSize: 11),
                ),
              ],
              pw.SizedBox(height: 8),
              pw.Divider(color: _rule),
              pw.SizedBox(height: 8),
              for (final b in blocks) ...[
                _block(b, fonts),
                pw.SizedBox(height: 10),
              ],
            ],
          ),
        );
    return doc.save();
  }

  static pw.Widget _block(PdfBlock b, PdfFonts fonts) => switch (b) {
    PdfHeading(:final text) => pw.Text(
      text,
      style: pw.TextStyle(font: fonts.medium, fontSize: 14, color: _ink),
    ),
    PdfParagraph(:final text) => pw.Text(
      text,
      style: const pw.TextStyle(fontSize: 11, lineSpacing: 3, color: _ink),
    ),
    PdfKeyValues(:final rows) => pw.Table(
      columnWidths: const {
        0: pw.FlexColumnWidth(2),
        1: pw.FlexColumnWidth(3),
      },
      children: [
        for (final (k, v) in rows)
          pw.TableRow(
            children: [
              pw.Padding(
                padding: const pw.EdgeInsets.symmetric(vertical: 3),
                child: pw.Text(
                  k,
                  style: const pw.TextStyle(color: _muted, fontSize: 10),
                ),
              ),
              pw.Padding(
                padding: const pw.EdgeInsets.symmetric(vertical: 3),
                child: pw.Text(
                  v,
                  style: pw.TextStyle(font: fonts.medium, fontSize: 11),
                ),
              ),
            ],
          ),
      ],
    ),
    PdfTable(:final headers, :final rows, :final numericColumns) =>
      pw.TableHelper.fromTextArray(
        headers: headers,
        data: rows,
        border: pw.TableBorder.all(color: _rule, width: 0.5),
        headerStyle: pw.TextStyle(font: fonts.medium, fontSize: 10),
        headerDecoration: const pw.BoxDecoration(color: _paper),
        cellStyle: const pw.TextStyle(fontSize: 10),
        cellAlignments: {
          for (final c in numericColumns) c: pw.Alignment.centerRight,
        },
      ),
    PdfNote(:final text) => pw.Container(
      padding: const pw.EdgeInsets.all(10),
      decoration: pw.BoxDecoration(
        color: _paper,
        border: pw.Border.all(color: _rule),
        borderRadius: const pw.BorderRadius.all(pw.Radius.circular(4)),
      ),
      child: pw.Text(
        text,
        style: pw.TextStyle(font: fonts.italic, fontSize: 10, color: _muted),
      ),
    ),
    PdfSignatures(:final signatures) => pw.Wrap(
      spacing: 24,
      runSpacing: 16,
      children: [for (final s in signatures) _signature(s, fonts)],
    ),
  };

  static pw.Widget _signature(PdfSignature s, PdfFonts fonts) => pw.SizedBox(
    width: 220,
    child: pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(s.role, style: const pw.TextStyle(color: _muted, fontSize: 9)),
        pw.SizedBox(
          height: 56,
          child: s.image == null
              ? pw.SizedBox()
              : pw.Image(pw.MemoryImage(s.image!)),
        ),
        pw.Container(height: 0.8, color: _ink),
        pw.SizedBox(height: 3),
        pw.Text(s.name, style: pw.TextStyle(font: fonts.medium, fontSize: 11)),
        if (s.signedAt != null)
          pw.Text(
            s.signedAt!,
            style: const pw.TextStyle(color: _muted, fontSize: 9),
          ),
      ],
    ),
  );
}
