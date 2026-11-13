import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';

void main() {
  test('assets/norms/v0.yaml norms/v0.yaml bilan baytma-bayt bir xil', () {
    final asset = File('assets/norms/v0.yaml').readAsBytesSync();
    final source = File('../norms/v0.yaml').readAsBytesSync();
    expect(asset, source, reason: 'norms/v0.yaml o\'zgarsa: cp ../norms/v0.yaml assets/norms/v0.yaml');
    expect(NormSet.fromYaml(String.fromCharCodes(asset)).version, isNotEmpty);
  });

  test('Noto Sans shriftlari va litsenziyasi ilova ichida', () {
    for (final f in ['NotoSans-Regular.ttf', 'NotoSans-Bold.ttf', 'OFL.txt']) {
      expect(File('assets/fonts/$f').existsSync(), isTrue, reason: f);
    }
  });
}
