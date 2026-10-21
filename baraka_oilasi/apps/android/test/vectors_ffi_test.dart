// 12.1: barcha oltin vektorlar Dart'dan ham — FFI (FRB) orqali yadro chaqiriladi, natija `expected`
// bilan to'liq solishtiriladi. Host yadrosi `--features vectors` bilan yig'iladi.
import 'dart:convert';
import 'dart:io';

import 'package:baraka/bindings/api/core.dart';
import 'package:collection/collection.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/harness.dart';

void main() {
  setUpAll(initRust);

  final files =
      Directory('../../spec/test-vectors').listSync().whereType<File>().where((f) => f.path.endsWith('.json')).toList()
        ..sort((a, b) => a.path.compareTo(b.path));

  test('vektor fayllari topildi', () => expect(files, isNotEmpty));

  for (final file in files) {
    final doc = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
    final suite = doc['suite'] as String;
    test(suite, () async {
      final failures = <String>[];
      for (final c in (doc['cases'] as List).cast<Map<String, dynamic>>()) {
        final actual = jsonDecode(await runVector(suite: suite, inputJson: jsonEncode(c['input'])));
        if (!const DeepCollectionEquality().equals(actual, c['expected'])) {
          failures.add('${c['id']}: kutilgan ${jsonEncode(c['expected'])}, chiqdi ${jsonEncode(actual)}');
        }
      }
      expect(failures, isEmpty);
    });
  }
}
