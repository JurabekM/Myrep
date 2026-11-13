import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

import 'support/fixture.dart';

/// Render paytidagi `print` larni ushlaydi (`pdf` paketi yetishmagan glif haqida shunday ogohlantiradi).
Future<(Uint8List, List<String>)> renderCapturing(Map<String, Object?> payload, ProtocolFonts fonts) async {
  final printed = <String>[];
  final bytes = await runZoned(
    () => renderProtocolPdf(payload, fonts),
    zoneSpecification: ZoneSpecification(print: (_, _, _, line) => printed.add(line)),
  );
  return (bytes, printed);
}

/// Payload'ni JSON orqali chuqur nusxalaydi va kalitlar tartibini teskari qiladi.
Object? reversedKeys(Object? v) => switch (v) {
  final Map<String, Object?> m => {for (final k in m.keys.toList().reversed) k: reversedKeys(m[k])},
  final List<Object?> l => [for (final x in l) reversedKeys(x)],
  _ => v,
};

String? pdfText(Uint8List pdf) {
  final dir = Directory.systemTemp.createTempSync('zanjir_pdf');
  try {
    final f = File('${dir.path}/p.pdf')..writeAsBytesSync(pdf);
    final r = Process.runSync('pdftotext', ['-raw', f.path, '-'], stdoutEncoding: utf8);
    return r.exitCode == 0 ? r.stdout as String : null;
  } on ProcessException {
    return null;
  } finally {
    dir.deleteSync(recursive: true);
  }
}

final hasPdftotext = () {
  try {
    return Process.runSync('pdftotext', ['-v']).exitCode == 0;
  } on ProcessException {
    return false;
  }
}();

void main() {
  final fonts = loadFonts();

  group('deterministik PDF (ADR-0010)', () {
    test('bir xil payload → baytma-bayt bir xil PDF', () async {
      final a = await renderProtocolPdf(samplePayload(), fonts);
      final b = await renderProtocolPdf(samplePayload(), fonts);
      expect(a, equals(b));
      expect(sha256Hex(a), sha256Hex(b));
    });

    test('boshqa isolate\'da ham bir xil baytlar', () async {
      final here = await renderProtocolPdf(samplePayload(), fonts);
      final there = await Isolate.run(() => renderProtocolPdf(samplePayload(), loadFonts()));
      expect(there, equals(here));
    });

    test('payload kalitlari tartibi natijaga ta\'sir qilmaydi', () async {
      final a = await renderProtocolPdf(samplePayload(), fonts);
      final shuffled = (reversedKeys(samplePayload())! as Map).cast<String, Object?>();
      expect(protocolPayloadSha256(shuffled), protocolPayloadSha256(samplePayload()));
      expect(await renderProtocolPdf(shuffled, fonts), equals(a));
    });

    test('/ID = payload_sha256; vaqt va muallif metama\'lumoti yo\'q', () async {
      final pdf = await renderProtocolPdf(samplePayload(), fonts);
      expect(pdfDocumentId(pdf), protocolPayloadSha256(samplePayload()));
      final text = latin1.decode(pdf);
      for (final key in ['/CreationDate', '/ModDate', '/Author', '/Title', '/Creator', '/Courier']) {
        expect(text, isNot(contains(key)), reason: key);
      }
      expect(text, startsWith('%PDF-'));
    });

    test('bitta qiymat o\'zgarsa — boshqa PDF va boshqa /ID', () async {
      final a = await renderProtocolPdf(samplePayload(), fonts);
      final changed = samplePayload();
      ((changed['measurements']! as List)[0] as Map)['values'] = {
        'test_voltage_v': 1000,
        'pairs': [
          {'pair': 'L1-N', 'mohm': 520},
          {'pair': 'L1-PE', 'mohm': 0.85},
        ],
      };
      final b = await renderProtocolPdf(changed, fonts);
      expect(b, isNot(equals(a)));
      expect(pdfDocumentId(b), protocolPayloadSha256(changed));
      expect(pdfDocumentId(b), isNot(pdfDocumentId(a)));
    });

    test('ko\'p sahifali protokol (250 o\'lchov) ham deterministik', () async {
      final payload = samplePayload(extraMeasurements: 250);
      final watch = Stopwatch()..start();
      final a = await renderProtocolPdf(payload, fonts);
      watch.stop();
      final b = await renderProtocolPdf(samplePayload(extraMeasurements: 250), fonts);
      expect(a, equals(b));
      expect(RegExp(r'/Type\s*/Page[^s]').allMatches(latin1.decode(a)).length, greaterThan(3));
      expect(watch.elapsedMilliseconds, lessThan(10000));
    });
  });

  group('matn va shriftlar', () {
    test('barcha belgilar shriftlarda bor (≤ ≥ Ω ψ Δ № — kirill) — ogohlantirishsiz', () async {
      for (final lang in ['uz', 'ru']) {
        final (_, printed) = await renderCapturing(samplePayload(language: lang), fonts);
        expect(printed, isEmpty, reason: lang);
      }
    });

    test('PDF matni: sarlavha, ogohlantirish, natijalar, hash; "xavfsiz" degan da\'vo yo\'q', () async {
      final text = pdfText(await renderProtocolPdf(samplePayload(), fonts))!;
      final flat = text.replaceAll(RegExp(r'\s+'), ' ');
      expect(flat, contains('ELEKTR QURILMALARINI SINASH PROTOKOLI'));
      expect(flat, contains('2026-3F9A1C-001'));
      expect(flat, contains('Ilova faqat tavsiya beradi'));
      expect(flat, contains('Normadan tashqari'));
      expect(flat, contains('≤ 300 ms'));
      expect(flat, contains('≥ 0,5 MΩ'));
      expect(flat, contains('Mavsumiy koeffitsient kiritilmagan'));
      expect(flat, contains(protocolPayloadSha256(samplePayload())));
      expect(flat, contains('Karimova Dilnoza'));
      expect(flat.toLowerCase(), isNot(contains('ishlash xavfsiz')));
    }, skip: hasPdftotext ? false : 'pdftotext o\'rnatilmagan');

    test('ruscha protokol', () async {
      final text = pdfText(await renderProtocolPdf(samplePayload(language: 'ru'), fonts))!;
      final flat = text.replaceAll(RegExp(r'\s+'), ' ');
      expect(flat, contains('ПРОТОКОЛ ИСПЫТАНИЙ ЭЛЕКТРОУСТАНОВОК'));
      expect(flat, contains('Не норма'));
      expect(flat, contains('Не указан сезонный коэффициент'));
    }, skip: hasPdftotext ? false : 'pdftotext o\'rnatilmagan');

    test('o\'lchovsiz qoralama ham chiziladi (bo\'sh normalar to\'plami)', () async {
      final empty = samplePayload()
        ..['measurements'] = <Object?>[]
        ..['instruments'] = <Object?>[]
        ..['summary'] = verdictCounts([])
        ..['norm_set'] = {'version': '', 'sha256': '', 'reviewed_by': null, 'reviewed_at': null};
      expect(pdfDocumentId(await renderProtocolPdf(empty, fonts)), protocolPayloadSha256(empty));
    });

    test('noma\'lum til yoki sxema — xato', () async {
      expect(() => renderProtocolPdf(samplePayload(language: 'en'), fonts), throwsArgumentError);
      expect(() => renderProtocolPdf({...samplePayload(), 'schema': 'zanjir.protocol/0'}, fonts), throwsArgumentError);
    });

    test('domen kodlari → matn (uz/ru), noma\'lum kod o\'zgarishsiz', () {
      for (final lang in ['uz', 'ru']) {
        final t = ProtocolTexts(lang);
        for (final k in NodeKind.values) {
          expect(t.kind(k.code), isNot(k.code), reason: k.code);
        }
        for (final v in Verdict.values) {
          expect(t.verdict(v.code), isNotEmpty);
        }
        for (final m in MeasurementType.values) {
          expect(t.type(m), isNotEmpty);
        }
        for (final r in ['ADMIN', 'LEAD', 'ENGINEER', 'VIEWER']) {
          expect(t.role(r), isNot(r));
        }
        for (final code in reasonCodes) {
          expect(t.reason(code), isNot(code), reason: '$lang $code');
        }
        expect(t.reason('brand_new_reason'), 'brand_new_reason');
        expect(() => t.verdict('MAYBE'), throwsArgumentError);
        expect(() => t.sessionKind('X'), throwsArgumentError);
        for (final k in ['QABUL_TOPSHIRISH', 'DAVRIY', 'NAVBATDAN_TASHQARI']) {
          expect(t.sessionKind(k), isNotEmpty);
        }
        expect(() => t['pdf.nope'], throwsStateError);
      }
    });
  });
}

/// `app/lib/l10n/labels.dart` dagi `reasonText` kodlari (ADR-0005).
const reasonCodes = [
  'out_of_limit',
  'zs_exceeded',
  'value_missing',
  'invalid_value',
  'missing_ambient_temp',
  'test_voltage_below_norm',
  'no_pairs',
  'no_matching_norm',
  'norm_applicability_unknown',
  'loop_pair_not_pe',
  'unprotected_path',
  'no_protective_device',
  'fuse_protection',
  'device_attrs_missing',
  'curve_unknown',
  'zs_exceeded_rcd_present',
  'zs_ambiguous_multiple_feeds',
  'rcd_multiplier_below_1',
  'rcd_not_tripped',
  'season_coeff_missing',
  'season_coeff_below_1',
  'no_upstream_rcd',
  'rcd_idn_missing',
  'factor_unavailable',
  'marked_not_applicable',
];
