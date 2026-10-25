// Demo yig'ma himoyasi: fayl ulashish o'rniga `error.DEMO_DISABLED` xabari chiqadi.
// (Muddat va «DEMO» belgisi `--dart-define` bilan yig'ilgan APK'da emulyatorda tekshiriladi:
// tool/demo_emulator_smoke.sh.)
import 'dart:io';
import 'dart:typed_data';

import 'package:baraka/app/demo.dart';
import 'package:baraka/app/i18n.dart';
import 'package:baraka/core/core.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('demoda ulashish DEMO_DISABLED xatosini beradi va xabari bor', () async {
    final tr = Tr('uz', Tr.parseArb(File('lib/l10n/app_uz.arb').readAsStringSync()));
    Object? error;
    try {
      await demoShareDisabled(Uint8List.fromList([1, 2, 3]), 'tilxat.pdf', 'application/pdf');
    } on AppError catch (e) {
      error = e;
    }
    expect(error, isA<AppError>().having((e) => e.code, 'code', 'DEMO_DISABLED'));
    expect(errorKey(error, tr.has), 'error.DEMO_DISABLED');
  });

  test("oddiy yig'mada demo o'chiq va muddat tekshirilmaydi", () {
    expect(kDemo, isFalse);
    expect(demoExpired(DateTime(2999)), isFalse);
  });
}
