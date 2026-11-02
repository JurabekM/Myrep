import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Ikonka siyosati: jonzot yuzi, cho'chqa-qutisi, qimor, alkogol, boshqa din ramzlari va bank binosi
/// ishlatilmaydi (foydalanuvchi qoidasi). Play do'kon grafikasi ham shu qoidaga bo'ysunadi.
const forbidden = [
  'savings', 'casino', 'wine_bar', 'liquor', 'sports_bar', 'local_bar', 'church', 'account_balance',
  'pets', 'cruelty_free', 'face', 'mood', 'sentiment_', 'emoji_people', 'child_', 'face_retouching',
  'nightlife', 'smoking', 'temple_', 'synagogue', 'mosque', 'attach_money', 'percent',
];

void main() {
  test('lib/ ichida taqiqlangan Material ikonkalari yo\'q', () {
    final hits = <String>[];
    for (final f in Directory('lib').listSync(recursive: true).whereType<File>().where((f) => f.path.endsWith('.dart'))) {
      final src = f.readAsStringSync();
      for (final m in RegExp(r'Icons\.(\w+)').allMatches(src)) {
        final name = m.group(1)!;
        if (forbidden.any((x) => x.endsWith('_') ? name.startsWith(x) : name == x || name.startsWith('${x}_'))) {
          hits.add('${f.path}: Icons.$name');
        }
      }
    }
    expect(hits, isEmpty);
  });
}
