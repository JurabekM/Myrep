import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Grafika islom tamoyillariga mos boʻlishi shart (docs/DESIGN_GUIDELINES.md).
///
/// Material ikonkasining nomi uning koʻrinishini doim aytmaydi: masalan,
/// `Icons.savings` — choʻchqa-tanga qutisi. Shu sababli taqiqlangan
/// koʻrinishlar nom qismlari boʻyicha ushlanadi.
final _forbidden = <String, String>{
  'savings': 'choʻchqa-tanga qutisi (piggy bank)',
  'pets': 'hayvon tasviri',
  'cruelty': 'hayvon tasviri',
  'face': 'yuz tasviri',
  'emoji': 'yuz tasviri',
  'mood': 'yuz tasviri',
  'sentiment': 'yuz tasviri',
  'person': 'odam tasviri',
  'record_voice_over': 'odam tasviri',
  'people': 'odam tasviri',
  'group': 'odam tasviri',
  'child': 'odam tasviri',
  'baby': 'odam tasviri',
  'woman': 'odam tasviri',
  'man_': 'odam tasviri',
  'pregnant': 'odam tasviri',
  'accessibility': 'odam tasviri',
  'diversity': 'odam tasviri',
  'family': 'odam tasviri',
  'groups': 'odam tasviri',
  'handshake': 'qoʻl tasviri',
  'volunteer_activism': 'qoʻl tasviri',
  'back_hand': 'qoʻl tasviri',
  'front_hand': 'qoʻl tasviri',
  'waving_hand': 'qoʻl tasviri',
  'pan_tool': 'qoʻl tasviri',
  'thumb_': 'qoʻl tasviri',
  'elderly': 'odam tasviri',
  'boy': 'odam tasviri',
  'girl': 'odam tasviri',
  'hiking': 'odam tasviri',
  'directions_walk': 'odam tasviri',
  'self_improvement': 'odam tasviri',
  'wine': 'alkogol',
  'liquor': 'alkogol',
  'local_bar': 'alkogol',
  'sports_bar': 'alkogol',
  'nightlife': 'alkogol',
  'casino': 'qimor',
  'church': 'boshqa din ramzi',
  'synagogue': 'boshqa din ramzi',
  'temple': 'boshqa din ramzi',
  'percent': 'foizni daromad sifatida koʻrsatish xavfi',
};

/// `account_balance` — bank binosi (foizli bank assotsiatsiyasi); hamyon
/// (`account_balance_wallet`) esa ruxsat etilgan.
final _bankBuilding = RegExp(r'^account_balance(_(outlined|rounded|sharp))?$');

String? _reasonFor(String iconName) {
  if (_bankBuilding.hasMatch(iconName)) return 'bank binosi';
  final padded = '${iconName.toLowerCase()}_';
  for (final MapEntry(key: part, value: why) in _forbidden.entries) {
    if (padded.contains(part)) return why;
  }
  return null;
}

void main() {
  test('denylist haqiqatan ushlaydi', () {
    expect(_reasonFor('savings_outlined'), isNotNull);
    expect(_reasonFor('account_balance'), isNotNull);
    expect(_reasonFor('person_outline'), isNotNull);
    expect(_reasonFor('diversity_3_outlined'), isNotNull);
    expect(_reasonFor('account_balance_wallet_outlined'), isNull);
    expect(_reasonFor('menu_book_outlined'), isNull);
  });

  test('lib/ da islom tamoyillariga zid ikonka yoʻq', () {
    final iconRef = RegExp(r'(?:Icons|CupertinoIcons)\.([a-zA-Z0-9_]+)');
    final violations = <String>[];
    final files = Directory('lib')
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) => f.path.endsWith('.dart'));
    for (final file in files) {
      final lines = file.readAsLinesSync();
      for (var i = 0; i < lines.length; i++) {
        for (final match in iconRef.allMatches(lines[i])) {
          final name = match.group(1)!;
          final why = _reasonFor(name);
          if (why != null) violations.add('${file.path}:${i + 1} $name — $why');
        }
      }
    }
    expect(violations, isEmpty, reason: violations.join('\n'));
  });
}
