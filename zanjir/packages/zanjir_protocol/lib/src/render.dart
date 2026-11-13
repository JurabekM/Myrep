import 'dart:typed_data';

import 'package:barcode/barcode.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:zanjir_core/zanjir_core.dart';

import 'document_id.dart';
import 'format.dart';
import 'payload.dart';
import 'pdf_strings.g.dart';

/// PDF tillari (`protocol.language`).
final Set<String> pdfLanguages = Set.unmodifiable(pdfStrings.keys);

/// PDF shriftlari (TTF baytlari). `symbols` — asosiy shriftda yo'q belgilar uchun (≤, ≥, √ va h.k.).
class ProtocolFonts {
  const ProtocolFonts({required this.regular, required this.bold, required this.symbols});
  final Uint8List regular;
  final Uint8List bold;
  final Uint8List symbols;
}

/// Payload → PDF. Deterministik: bir xil payload va shriftlar → baytma-bayt bir xil fayl (ADR-0010).
/// Metama'lumot (sarlavha, muallif, `/CreationDate`) yozilmaydi; `/ID` = `payload_sha256`.
Future<Uint8List> renderProtocolPdf(Map<String, Object?> payload, ProtocolFonts fonts) async {
  if (payload['schema'] != protocolPayloadSchema) {
    throw ArgumentError.value(payload['schema'], 'payload.schema', 'kutilgan: $protocolPayloadSchema');
  }
  final p = _Payload(payload);
  final s = ProtocolTexts(p.str('protocol', 'language'));
  final theme = pw.ThemeData.withFont(
    base: pw.Font.ttf(fonts.regular.buffer.asByteData(fonts.regular.offsetInBytes, fonts.regular.lengthInBytes)),
    bold: pw.Font.ttf(fonts.bold.buffer.asByteData(fonts.bold.offsetInBytes, fonts.bold.lengthInBytes)),
    fontFallback: [
      pw.Font.ttf(fonts.symbols.buffer.asByteData(fonts.symbols.offsetInBytes, fonts.symbols.lengthInBytes)),
    ],
  ).copyWith(defaultTextStyle: const pw.TextStyle(fontSize: 9));
  final doc = pw.Document(theme: theme);
  doc.addPage(
    pw.MultiPage(
      pageFormat: PdfPageFormat.a4,
      margin: const pw.EdgeInsets.fromLTRB(36, 36, 36, 30),
      footer: (c) => pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Divider(thickness: 0.5),
          pw.Row(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Expanded(child: pw.Text(s['disclaimer'], style: const pw.TextStyle(fontSize: 7))),
              pw.SizedBox(width: 12),
              pw.Text(
                '${p.str('protocol', 'number')} · ${s['pdf.page']} ${c.pageNumber}/${c.pagesCount}',
                style: const pw.TextStyle(fontSize: 7),
              ),
            ],
          ),
        ],
      ),
      build: (c) => [
        _header(p, s),
        pw.SizedBox(height: 10),
        _facts(p, s),
        pw.SizedBox(height: 10),
        _section(s['pdf.instruments']),
        _instruments(p, s),
        pw.SizedBox(height: 10),
        _section(s['pdf.results']),
        _results(p, s),
        pw.SizedBox(height: 10),
        _summary(p, s),
        pw.SizedBox(height: 12),
        _signature(p, s, theme),
      ],
    ),
  );
  final bytes = await doc.save();
  return patchDocumentId(bytes, protocolPayloadSha256(payload));
}

pw.Widget _header(_Payload p, ProtocolTexts s) => pw.Center(
  child: pw.Column(
    children: [
      pw.Text(s['pdf.title'], style: pw.TextStyle(fontSize: 13, fontWeight: pw.FontWeight.bold)),
      pw.SizedBox(height: 4),
      pw.Text('№ ${p.str('protocol', 'number')}', style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold)),
    ],
  ),
);

pw.Widget _section(String title) => pw.Padding(
  padding: const pw.EdgeInsets.only(bottom: 4),
  child: pw.Text(title, style: pw.TextStyle(fontSize: 10, fontWeight: pw.FontWeight.bold)),
);

pw.Widget _facts(_Payload p, ProtocolTexts s) {
  String join(Iterable<String?> parts) => parts.whereType<String>().where((x) => x.isNotEmpty).join(', ');
  final licenseNo = p.opt('lab', 'license_no');
  final licenseUntil = p.opt('lab', 'license_valid_until');
  final temp = p.optNum('session', 'ambient_temp_c');
  final humidity = p.optNum('session', 'humidity_pct');
  final safety = p.opt('engineer', 'safety_group');
  final reviewedBy = p.opt('norm_set', 'reviewed_by');
  final rows = <(String, String)>[
    (s['pdf.lab'], p.str('lab', 'name')),
    if (licenseNo != null)
      (s['pdf.license'], join([licenseNo, if (licenseUntil != null) '${s['pdf.validUntil']} ${_date(licenseUntil)}'])),
    (s['pdf.site'], p.str('site', 'name')),
    if (p.opt('site', 'address') != null) (s['pdf.address'], p.opt('site', 'address')!),
    if (p.opt('site', 'customer') != null) (s['pdf.customer'], p.opt('site', 'customer')!),
    (
      s['pdf.earthing'],
      join([
        p.opt('site', 'earthing_system') ?? '—',
        if (p.optNum('site', 'u0_volts') case final u?) 'U0 = ${formatDecimal(u)} V',
      ]),
    ),
    (s['pdf.session'], s.sessionKind(p.str('session', 'kind'))),
    (s['pdf.period'], '${_time(p.str('session', 'started_at'))} — ${_time(p.str('session', 'closed_at'))}'),
    (
      s['pdf.conditions'],
      join([
        '${s['pdf.temp']} ${temp == null ? '—' : '${formatDecimal(temp)} °C'}',
        '${s['pdf.humidity']} ${humidity == null ? '—' : '${formatDecimal(humidity)} %'}',
      ]),
    ),
    (s['pdf.engineer'], join([p.str('engineer', 'full_name'), if (safety != null) '${s['pdf.safetyGroup']}: $safety'])),
    (
      s['pdf.norms'],
      join([
        p.str('norm_set', 'version'),
        if (p.str('norm_set', 'sha256') case final sha when sha.length >= 16) 'SHA-256 ${sha.substring(0, 16)}…',
        reviewedBy == null || reviewedBy.trim().isEmpty
            ? s['pdf.notReviewed']
            : '${s['pdf.reviewedBy']}: $reviewedBy ${p.opt('norm_set', 'reviewed_at') ?? ''}'.trim(),
      ]),
    ),
  ];
  return pw.Table(
    columnWidths: const {0: pw.FixedColumnWidth(130), 1: pw.FlexColumnWidth()},
    children: [
      for (final (k, v) in rows)
        pw.TableRow(
          children: [
            pw.Padding(
              padding: const pw.EdgeInsets.symmetric(vertical: 1.5),
              child: pw.Text(k, style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
            ),
            pw.Padding(padding: const pw.EdgeInsets.symmetric(vertical: 1.5), child: pw.Text(v)),
          ],
        ),
    ],
  );
}

pw.Widget _instruments(_Payload p, ProtocolTexts s) => _table(
  headers: [s['pdf.model'], s['pdf.serial'], s['pdf.cert'], s['pdf.certValid']],
  widths: const [pw.FlexColumnWidth(3), pw.FlexColumnWidth(2), pw.FlexColumnWidth(2), pw.FlexColumnWidth(1.4)],
  rows: [
    for (final i in p.list('instruments'))
      [
        '${i['model']}',
        '${i['serial_no']}',
        '${i['cert_no'] ?? '—'}',
        i['verified_until'] is String ? _date(i['verified_until']! as String) : '—',
      ],
  ],
);

pw.Widget _results(_Payload p, ProtocolTexts s) {
  final rows = <List<String>>[];
  var n = 0;
  for (final m in p.list('measurements')) {
    n++;
    final type = MeasurementType.parse(m['type']! as String);
    final verdict = m['verdict']! as String;
    final reason = m['reason'] as String?;
    rows.add([
      '$n',
      '${m['node_label']}\n${s.kind(m['node_kind']! as String)}',
      s.type(type),
      summarizeValues(type, (m['values']! as Map).cast<String, Object?>()),
      _norm(m, type, s),
      s.verdict(verdict),
      verdict == Verdict.pass.code || reason == null ? '' : s.reason(reason),
    ]);
  }
  return _table(
    headers: [
      s['pdf.colNo'],
      s['pdf.colPoint'],
      s['pdf.colType'],
      s['pdf.colValues'],
      s['pdf.colNorm'],
      s['pdf.colVerdict'],
      s['pdf.colNote'],
    ],
    widths: const [
      pw.FixedColumnWidth(18),
      pw.FlexColumnWidth(2.2),
      pw.FlexColumnWidth(1.6),
      pw.FlexColumnWidth(3),
      pw.FlexColumnWidth(2.2),
      pw.FlexColumnWidth(1.5),
      pw.FlexColumnWidth(2.4),
    ],
    rows: rows,
  );
}

/// Hal qiluvchi norma: `ID` + hisoblangan chegara (zaxira bilan) va birligi.
String _norm(Map<String, Object?> m, MeasurementType type, ProtocolTexts s) {
  final id = m['norm_id'] as String?;
  if (id == null) return '—';
  final formula = (m['formula'] as String?) ?? '';
  final limit = m['limit'];
  final unit = switch (type) {
    MeasurementType.insulation => s['pdf.unitMohm'],
    MeasurementType.rcdTrip => formula.startsWith('t ') ? s['pdf.unitMs'] : s['pdf.unitMa'],
    _ when formula.contains('Ia') => s['pdf.unitV'],
    _ => s['pdf.unitOhm'],
  };
  final text = switch (limit) {
    final num x when formula.contains('≥') => '≥ ${formatDecimal(x)} $unit',
    final num x => '≤ ${formatDecimal(x)} $unit',
    {'min': final num lo, 'max': final num hi} => '${formatDecimal(lo)}…${formatDecimal(hi)} $unit',
    _ => '',
  };
  return text.isEmpty ? id : '$id\n$text';
}

pw.Widget _summary(_Payload p, ProtocolTexts s) {
  final c = p.map('summary');
  final parts = [
    for (final v in Verdict.values)
      if ((c[v.code] as num? ?? 0) > 0) '${s.verdict(v.code)}: ${c[v.code]}',
  ];
  final comment = payloadString(p.raw['lead_comment']);
  return pw.Column(
    crossAxisAlignment: pw.CrossAxisAlignment.start,
    children: [
      _section(s['pdf.summary']),
      pw.Text(["${s['pdf.total']}: ${c['total']}", ...parts].join(' · ')),
      if (comment != null) ...[
        pw.SizedBox(height: 6),
        pw.Text(s['pdf.leadComment'], style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
        pw.Text(comment),
      ],
    ],
  );
}

pw.Widget _signature(_Payload p, ProtocolTexts s, pw.ThemeData theme) => pw.Row(
  crossAxisAlignment: pw.CrossAxisAlignment.start,
  children: [
    pw.Expanded(
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(
            '${s['pdf.signed']}: ${p.str('signer', 'full_name')} (${s.role(p.str('signer', 'role'))})',
            style: pw.TextStyle(fontWeight: pw.FontWeight.bold),
          ),
          pw.Text('${s['pdf.signedAt']}: ${_time(p.raw['signed_at']! as String)}'),
          pw.SizedBox(height: 4),
          pw.Text(s['pdf.payloadHash'], style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
          pw.Text(protocolPayloadSha256(p.raw), style: const pw.TextStyle(fontSize: 7)),
          pw.SizedBox(height: 4),
          pw.Text('${s['pdf.verify']}: ${p.str('protocol', 'verify_url')}', style: const pw.TextStyle(fontSize: 8)),
        ],
      ),
    ),
    pw.SizedBox(width: 12),
    // Matnsiz QR: `BarcodeWidget` standart matn shrifti (Courier) faylga qo'shilmasin.
    pw.BarcodeWidget(
      barcode: Barcode.qrCode(),
      data: p.str('protocol', 'verify_url'),
      width: 84,
      height: 84,
      drawText: false,
      textStyle: pw.TextStyle(font: theme.defaultTextStyle.font, fontNormal: theme.defaultTextStyle.font),
    ),
  ],
);

pw.Widget _table({
  required List<String> headers,
  required List<pw.TableColumnWidth> widths,
  required List<List<String>> rows,
}) {
  pw.Widget cell(String text, {bool bold = false}) => pw.Padding(
    padding: const pw.EdgeInsets.symmetric(horizontal: 3, vertical: 2),
    child: pw.Text(text, style: pw.TextStyle(fontSize: 8, fontWeight: bold ? pw.FontWeight.bold : null)),
  );
  return pw.Table(
    border: pw.TableBorder.all(width: 0.5),
    columnWidths: {for (var i = 0; i < widths.length; i++) i: widths[i]},
    children: [
      pw.TableRow(repeat: true, children: [for (final h in headers) cell(h, bold: true)]),
      for (final r in rows) pw.TableRow(children: [for (final x in r) cell(x)]),
    ],
  );
}

/// ISO vaqt (UTC) → `YYYY-MM-DD HH:MM`.
String _time(String iso) => iso.length >= 16 ? '${iso.substring(0, 10)} ${iso.substring(11, 16)}' : iso;
String _date(String iso) => iso.length >= 10 ? iso.substring(0, 10) : iso;

/// Bo'sh bo'lmagan satr yoki `null`.
String? payloadString(Object? v) => v is String && v.trim().isNotEmpty ? v : null;

class _Payload {
  _Payload(this.raw);
  final Map<String, Object?> raw;

  Map<String, Object?> map(String key) => (raw[key]! as Map).cast<String, Object?>();
  List<Map<String, Object?>> list(String key) => [
    for (final x in raw[key]! as List) (x as Map).cast<String, Object?>(),
  ];
  String str(String section, String key) => map(section)[key]! as String;
  String? opt(String section, String key) => payloadString(map(section)[key]);
  num? optNum(String section, String key) => map(section)[key] as num?;
}

/// PDF matnlari tanlangan tilda (`uz` | `ru`); domen kodlari → matn.
class ProtocolTexts {
  ProtocolTexts(String language) : _m = pdfStrings[language] ?? (throw ArgumentError.value(language, 'language'));
  final Map<String, String> _m;

  String operator [](String key) => _m[key] ?? (throw StateError('PDF matni yo\'q: $key'));

  String verdict(String code) =>
      this[switch (code) {
        'PASS' => 'verdictPass',
        'FAIL' => 'verdictFail',
        'NEEDS_REVIEW' => 'verdictNeedsReview',
        'NOT_APPLICABLE' => 'verdictNotApplicable',
        // Noma'lum natija hech qachon boshqa natija sifatida ko'rsatilmaydi.
        _ => throw ArgumentError.value(code, 'verdict'),
      }];

  String type(MeasurementType t) =>
      this[switch (t) {
        MeasurementType.insulation => 'typeInsulation',
        MeasurementType.loopImpedance => 'typeLoop',
        MeasurementType.rcdTrip => 'typeRcd',
        MeasurementType.earthResistance => 'typeEarth',
        MeasurementType.continuityBonding => 'typeBonding',
      }];

  String sessionKind(String code) =>
      this[switch (code) {
        'QABUL_TOPSHIRISH' => 'sessionKindQabul',
        'DAVRIY' => 'sessionKindDavriy',
        'NAVBATDAN_TASHQARI' => 'sessionKindNavbatdan',
        _ => throw ArgumentError.value(code, 'session.kind'),
      }];

  String role(String code) => _m['role${_pascal(code)}'] ?? code;

  /// `SRC_PV_INVERTER` → `kindSrcPvInverter`.
  String kind(String code) => _m['kind${_pascal(code)}'] ?? code;

  /// Sabab kodi (`out_of_limit`) → matn; noma'lum kod o'zgarishsiz ko'rsatiladi.
  String reason(String code) =>
      _m[code == 'zs_ambiguous_multiple_feeds' ? 'reasonZsAmbiguous' : 'reason${_pascal(code)}'] ?? code;

  static String _pascal(String code) =>
      code.toLowerCase().split('_').map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1)).join();
}
