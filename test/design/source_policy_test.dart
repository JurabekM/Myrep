import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Kontent manbasi siyosati (SPEC 1.1, 3-bo'lim): ilova umumiy moliyaviy
/// tamoyillardan ilhomlangan, lekin hech bir kitobning personajlari,
/// iqtiboslari, bob nomlari yoki o'xshatishlarini ishlatmaydi va boshqa
/// nashr yoki kompaniya nomini tilga olmaydi. Eski nom ham qaytmasin.
///
/// Iboralar kichik harfda, `ʻ`/`ʼ` oddiy `'` ga keltirilib qidiriladi.
const _forbidden = <String>[
  // Eski nom.
  'baraka daftari',
  'барака дафтари',
  // Personajlar.
  'sobir',
  'hoji',
  'ходж',
  'хаджи',
  'rustam',
  'рустам',
  'plyus',
  // Kitob bob nomlari va o'xshatishlari.
  'chorsu',
  'чорсу',
  "qal'a devor",
  'крепостн',
  'kishan',
  'бумажные оков',
  'xurjun',
  'хурджун',
  'baliqchi',
  'рыбак',
  'sichqon',
  "ro'molcha",
  'платоч',
  'qizil qopcha',
  'yarador askar',
  'раненого бойца',
  // Manba va homiy nomlari.
  'asaxiy',
  'асахий',
  'mirzayev',
  'мирзаев',
];

String _norm(String s) => s.toLowerCase().replaceAll(RegExp('[ʻʼ‘’`]'), "'");

Iterable<String> _strings(Object? node) sync* {
  if (node is String) {
    yield node;
  } else if (node is Map) {
    for (final v in node.values) {
      yield* _strings(v);
    }
  } else if (node is List) {
    for (final v in node) {
      yield* _strings(v);
    }
  }
}

void main() {
  final sources = {
    for (final f in [
      'lib/app/l10n/arb/app_uz.arb',
      'lib/app/l10n/arb/app_ru.arb',
      'assets/content/chapters.json',
    ])
      f: jsonDecode(File(f).readAsStringSync()),
  };

  for (final MapEntry(key: file, value: json) in sources.entries) {
    test('$file — kitob personajlari, iqtiboslari va manba nomlari yoʻq', () {
      final hits = <String>[];
      for (final s in _strings(json)) {
        final n = _norm(s);
        for (final f in _forbidden) {
          if (n.contains(f)) hits.add('«$f»: $s');
        }
      }
      expect(hits, isEmpty);
    });
  }

  test('Android yorligʻi va Play identifikatori yangi nomda', () {
    final manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();
    expect(manifest, contains('android:label="Baraka Dastur"'));
    final gradle = File('android/app/build.gradle.kts').readAsStringSync();
    expect(gradle, contains('applicationId = "uz.barakadastur.app"'));
  });

  test('darslarda placeholder faqat diniy blokda (ulamo tekshiruvigacha)', () {
    final content =
        jsonDecode(File('assets/content/chapters.json').readAsStringSync())
            as Map<String, dynamic>;
    for (final c in content['chapters'] as List) {
      for (final b in (c as Map)['blocks'] as List) {
        final block = b as Map;
        if (block['type'] == 'religious') continue;
        expect(
          _strings(block).join(' '),
          isNot(contains('Placeholder')),
          reason: '${c['id']} ${block['type']}',
        );
      }
    }
  });
}
