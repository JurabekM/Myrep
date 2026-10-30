import 'dart:convert';

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

void main() {
  group('canonicalJson (RFC 8785 / JCS)', () {
    test('kalitlar saralanadi, bo\'sh joy yo\'q', () {
      expect(
        canonicalJson({
          'b': 1,
          'a': [true, false, null],
          'c': {'z': 's', 'y': 2},
        }),
        '{"a":[true,false,null],"b":1,"c":{"y":2,"z":"s"}}',
      );
    });

    test('kalitlar UTF-16 kod birliklari bo\'yicha saralanadi', () {
      expect(
        canonicalJson({'é': 1, 'z': 2, 'A': 3, '\u{1F600}': 4, 'דּ': 5}),
        '{"A":3,"z":2,"é":1,"\u{1F600}":4,"דּ":5}',
      );
    });

    test('satrlarni ekranlash', () {
      expect(canonicalJson('a"b\\c/\b\f\n\r\t\u0001\u001f'), r'"a\"b\\c/\b\f\n\r\t\u0001\u001f"');
      expect(canonicalJson('Ўзбек — ПУЭ €'), '"Ўзбек — ПУЭ €"');
      expect(canonicalJson('\u{1F600}'), '"\u{1F600}"');
    });

    test('yolg\'iz surrogat rad etiladi', () {
      expect(() => canonicalJson('\uD800'), throwsArgumentError);
      expect(() => canonicalJson('a\uDC00'), throwsArgumentError);
    });

    test('sonlar — ECMAScript formati', () {
      final cases = <(num, String)>[
        (0, '0'),
        (-0.0, '0'),
        (1, '1'),
        (-1, '-1'),
        (16.0, '16'),
        (2.5, '2.5'),
        (0.1, '0.1'),
        (-0.000001, '-0.000001'),
        (0.0000001, '1e-7'),
        (1e21, '1e+21'),
        (1e20, '100000000000000000000'),
        (123e-20, '1.23e-18'),
        (1.5e300, '1.5e+300'),
        (333333333.3333333, '333333333.3333333'),
        (4.000000000000001, '4.000000000000001'),
        (9007199254740991, '9007199254740991'),
        (5e-324, '5e-324'),
        (1.7976931348623157e308, '1.7976931348623157e+308'),
      ];
      for (final (v, s) in cases) {
        expect(canonicalJson(v), s, reason: '$v');
      }
    });

    test('cheksiz, NaN va xavfsiz bo\'lmagan butun son rad etiladi', () {
      expect(() => canonicalJson(double.nan), throwsArgumentError);
      expect(() => canonicalJson(double.infinity), throwsArgumentError);
      expect(() => canonicalJson(9007199254740992), throwsArgumentError);
    });

    test('vaqt — UTC ISO-8601, millisekund aniqligida', () {
      expect(canonicalJson(DateTime.utc(2026, 10, 26, 7, 5, 3, 120, 999)), '"2026-10-26T07:05:03.120Z"');
      expect(canonicalJson(DateTime.utc(-1, 1, 1)), '"-000001-01-01T00:00:00.000Z"');
      expect(canonicalJson(DateTime.utc(12345, 1, 1)), '"+012345-01-01T00:00:00.000Z"');
      expect(() => canonicalJson(DateTime(2026)), throwsArgumentError, reason: 'mahalliy vaqt');
    });

    test('noma\'lum tur va satr bo\'lmagan kalit rad etiladi', () {
      expect(() => canonicalJson(Object()), throwsArgumentError);
      expect(() => canonicalJson({1: 'a'}), throwsArgumentError);
    });

    test('UTF-8 baytlar', () {
      expect(canonicalJsonBytes({'a': 'ў'}), utf8.encode('{"a":"ў"}'));
    });

    test('sha256Hex', () {
      expect(sha256Hex(utf8.encode('abc')), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
      expect(sha256Hex(const []), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
    });
  });
}
