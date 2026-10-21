import 'dart:io';
import 'dart:math';

import 'package:baraka/bindings/api/core.dart';
import 'package:baraka/bindings/frb_generated.dart';
import 'package:baraka/bindings/third_party/baraka_app.dart';
import 'package:flutter_rust_bridge/flutter_rust_bridge_for_generated.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  setUpAll(() async {
    await RustLib.init(externalLibrary: ExternalLibrary.open('../../target/debug/libbaraka_bindings_flutter.so'));
  });

  test('setup, income, change stream', () async {
    final dir = Directory.systemTemp.createTempSync('baraka');
    final core = await BarakaCore.newInstance(dataDir: dir.path);
    final secret = Uint8List.fromList(List.generate(32, (_) => Random.secure().nextInt(256)));
    final res = await core.setup(
      platformSecret: secret,
      pin: '135790',
      input: const BootstrapInput(
        debtsDeclared: false,
        householdName: 'Karim',
        deviceName: 'Telefon',
        platform: 'android',
        locale: 'uz',
        baseCurrency: 'UZS',
        monthStartDay: 10,
        spaces: ['UY'],
        members: [NewMemberInput(displayName: 'Karim', role: 'ADULT')],
      ),
    );
    final events = <ChangeEvent>[];
    core.watchChanges().listen(events.add);
    final uy = res.household.spaces.first.id;
    final rec = await core.recordIncome(
      spaceId: uy,
      input: const NewIncomeInput(amount: '3 000 000', source: 'Oylik', channel: 'CARD'),
    );
    expect(rec.suggestedShare.formatted, '150 000 soʻm');
    await Future<void>.delayed(const Duration(milliseconds: 200));
    expect(events, isNotEmpty);
    await core.lock();
    await expectLater(core.household(), throwsA(isA<AppError>().having((e) => e.code, 'code', 'LOCKED')));
  });
}
