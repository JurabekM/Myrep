import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/sync/crypto.dart';

// Desktop (Python) bilan kross-platforma vektori: kalit 00..1f
final _key = Uint8List.fromList(List<int>.generate(32, (i) => i));
const _topic = 'omborai/v1/b562beb66f2a7f7fe4d0830bfd2f84c4/ops';
const _pythonEnvelope =
    '{"v": 1, "n": "VHd/YGJnKvfXuNkC", "c": "hqgeCKIhB8Rzp8FnaqbdoVtEueF1vJaZ9AaAjm5GCWPB5/notg3B"}';

void main() {
  test('mavzu nomi desktop bilan bir xil', () async {
    expect(await topicFor(_key), _topic);
  });

  test("desktop shifrlagan xabarni ochadi", () async {
    final opened = await openEnvelope(
      _key,
      Uint8List.fromList(_pythonEnvelope.codeUnits),
      _topic,
    );
    expect(opened, {'hello': 'dunyo', 'n': 1});
  });

  test(
    'shifrlash-ochish aylanma, noto\'g\'ri kalit va AAD rad etiladi',
    () async {
      final raw = await seal(_key, {'a': 1}, _topic);
      expect(await openEnvelope(_key, raw, _topic), {'a': 1});
      await expectLater(
        openEnvelope(generateStoreKey(), raw, _topic),
        throwsA(isA<DecryptionException>()),
      );
      await expectLater(
        openEnvelope(_key, raw, '${_topic}x'),
        throwsA(isA<DecryptionException>()),
      );
    },
  );

  test('kalit uzunligi tekshiriladi', () async {
    await expectLater(topicFor(Uint8List(5)), throwsArgumentError);
  });
}
