import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/sync/crypto.dart';
import 'package:omborai_mobile/src/sync/mqtt_sync.dart';
import 'package:omborai_mobile/src/sync/ops.dart' as o;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Haqiqiy broker bilan integratsiya sinovi. Ishga tushirish:
///   mosquitto -c conf (listener PORT 127.0.0.1, allow_anonymous true)
///   OMBORAI_TEST_MQTT_PORT=PORT flutter test test/mqtt_sync_test.dart
/// Port berilmasa sinov o'tkazib yuboriladi (HiveMQ'ga sinovda ulanmaydi).
final _port = int.tryParse(
  Platform.environment['OMBORAI_TEST_MQTT_PORT'] ?? '',
);
const _store = 'store-mqtt-test';

Future<void> _until(Future<bool> Function() ok, {String what = 'shart'}) async {
  final deadline = DateTime.now().add(const Duration(seconds: 10));
  while (!await ok()) {
    if (DateTime.now().isAfter(deadline)) {
      fail('Vaqt tugadi: $what');
    }
    await Future<void>.delayed(const Duration(milliseconds: 50));
  }
}

void main() {
  setUpAll(() => sqfliteFfiInit());

  test('bir qurilmadagi tovar boshqasiga MQTT orqali yetib boradi', () async {
    final key = generateStoreKey();
    final a = await LocalDb.open(
      inMemoryDatabasePath,
      factory: databaseFactoryFfi,
    );
    final b = await LocalDb.open(
      inMemoryDatabasePath,
      factory: databaseFactoryFfi,
    );

    final syncA = MqttSync(
      key: key,
      deviceId: 'dev-a',
      applyOp: a.applyOp,
      host: '127.0.0.1',
      port: _port!,
      secure: false,
    );
    final syncB = MqttSync(
      key: key,
      deviceId: 'dev-b',
      applyOp: b.applyOp,
      host: '127.0.0.1',
      port: _port!,
      secure: false,
    );
    addTearDown(() async {
      await syncA.stop();
      await syncB.stop();
      await a.close();
      await b.close();
    });

    await syncB.start();
    await syncA.start();
    await _until(
      () async => syncA.connected && syncB.connected,
      what: 'ulanish',
    );

    final product = o.newOp(
      type: o.opProduct,
      storeId: _store,
      deviceId: 'dev-a',
      payload: {
        'id': 'p-mqtt',
        'name': 'Shakar 1 kg',
        'unit': 'kg',
        'sale_price': 14500,
      },
    );
    await a.applyOp(product);
    await syncA.send(product);

    await _until(
      () async => (await b.getProduct('p-mqtt', _store)) != null,
      what: 'B tovarni olishi',
    );

    final received = await b.getProduct('p-mqtt', _store);
    expect(received?['name'], 'Shakar 1 kg');
  }, skip: _port == null ? 'OMBORAI_TEST_MQTT_PORT berilmagan' : false);
}
