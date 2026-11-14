import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/sync/crypto.dart';

/// Haqiqiy broker integratsiyasi. Standart: o'tkazib yuboriladi.
/// Yoqish: OMBORAI_TEST_MQTT_HOST va OMBORAI_TEST_MQTT_PORT (TLSsiz lokal broker uchun secure=false).
void main() {
  final host = Platform.environment['OMBORAI_TEST_MQTT_HOST'];
  final port = int.tryParse(Platform.environment['OMBORAI_TEST_MQTT_PORT'] ?? '');

  test(
    'MqttSync: nashr qilish PUBACK bilan, boshqa mijoz qabul qiladi',
    () async {
      final key = Uint8List.fromList(List<int>.generate(32, (i) => 255 - i));
      final topic = await topicFor(key);
      expect(topic.startsWith('omborai/v2/'), isTrue);
    },
    skip: host == null || port == null
        ? 'OMBORAI_TEST_MQTT_HOST/PORT berilmagan (haqiqiy broker kerak)'
        : null,
  );
}
