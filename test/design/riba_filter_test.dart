import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Ribo filtri (SPEC 2C.5, MVP_PLAN Vazifa 9): ilovaning hech bir joyida
/// foizli omonat, «kafolatlangan foiz» yoki foiz stavkasi muqobil daromad
/// sifatida tavsiya qilinmaydi. Foizli daromadni **belgilash** («Foiz
/// (ribo)», «Foizli daromad (alohida)») ruxsat — u tavsiya emas.
///
/// Iboralar kichik harfda, `ʻ`/`ʼ` oddiy `'` ga keltirilib qidiriladi.
const _forbidden = <String>[
  // O'zbekcha.
  'depozitga qo',
  'omonatga qo',
  'omonat foizi',
  'depozit foizi',
  'yillik foiz',
  'foiz stavka',
  'foiz olib',
  'foizga qo',
  'kafolatlangan foiz',
  'kafolatlangan daromad',
  'kafolatlangan foyda',
  'muqobil daromad',
  'passiv foiz',
  '% yillik',
  'yiliga % ',
  // Ruscha.
  'годовых',
  'процентная ставка',
  'ставка по вкладу',
  'вклад под',
  'депозит под',
  'положите на депозит',
  'положите на вклад',
  'гарантированный доход',
  'гарантированная прибыль',
  'гарантированный процент',
  'доход по вкладу',
  'пассивный доход',
];

String _normalize(String s) => s
    .toLowerCase()
    .replaceAll('ʻ', "'")
    .replaceAll('ʼ', "'")
    .replaceAll('‘', "'");

List<String> _violations(Map<String, String> texts) => [
  for (final MapEntry(:key, :value) in texts.entries)
    for (final phrase in _forbidden)
      if (_normalize(value).contains(phrase)) '$key: «$phrase»',
];

Map<String, String> _arb(String path) {
  final json =
      jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;
  return {
    for (final MapEntry(:key, :value) in json.entries)
      if (!key.startsWith('@') && value is String) key: value,
  };
}

Map<String, String> _strings(Object? node, [String path = r'$']) {
  final out = <String, String>{};
  if (node is String) {
    out[path] = node;
  } else if (node is Map<String, dynamic>) {
    for (final MapEntry(:key, :value) in node.entries) {
      out.addAll(_strings(value, '$path.$key'));
    }
  } else if (node is List) {
    for (final (i, v) in node.indexed) {
      out.addAll(_strings(v, '$path[$i]'));
    }
  }
  return out;
}

void main() {
  for (final lang in ['uz', 'ru']) {
    test(
      'ARB ($lang): foizni daromad sifatida tavsiya qiluvchi ibora yoʻq',
      () {
        expect(_violations(_arb('lib/app/l10n/arb/app_$lang.arb')), isEmpty);
      },
    );
  }

  test('kontent JSON: foizni daromad sifatida tavsiya qiluvchi ibora yoʻq', () {
    final json = jsonDecode(
      File('assets/content/chapters.json').readAsStringSync(),
    );
    expect(_violations(_strings(json)), isEmpty);
  });

  test('filtr haqiqatan ushlaydi', () {
    expect(
      _violations({
        'a': 'Pulni depozitga qoʻying — yillik foiz 20 %!',
        'b': 'Вклад под 18% годовых',
        'c': 'Foiz (ribo)',
        'd': 'Foizli daromad (alohida): 5 000 soʻm',
      }),
      hasLength(4),
      reason: 'a: 2 ta, b: 2 ta; c va d — belgilash, tavsiya emas',
    );
  });
}
