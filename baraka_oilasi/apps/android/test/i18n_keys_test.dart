// Dart kodidagi har bir aniq i18n kaliti (`t('home.title')`) `shared/i18n` da bor.
// Dinamik kalitlar (`'error.$code'`) bu yerda tekshirilmaydi — ular yadro kodlari bilan keladi.
import 'dart:io';

import 'package:baraka/app/i18n.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Dart kodidagi i18n kalitlari mavjud', () {
    final strings = Tr.parseArb(File('lib/l10n/app_uz.arb').readAsStringSync());
    final tr = Tr('uz', strings);
    final call = RegExp(r"""\bt\(\s*'([a-zA-Z0-9_.+\-]+)'""");
    final missing = <String>{};
    for (final f in Directory('lib').listSync(recursive: true).whereType<File>()) {
      if (!f.path.endsWith('.dart') || f.path.contains('/bindings/')) continue;
      for (final m in call.allMatches(f.readAsStringSync())) {
        final key = m.group(1)!;
        if (!tr.has(key)) missing.add('$key (${f.path})');
      }
    }
    expect(missing, isEmpty);
  });
}
