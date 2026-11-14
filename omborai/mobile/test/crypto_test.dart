import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/sync/crypto.dart';
import 'package:omborai_mobile/src/sync/identity.dart';
import 'package:omborai_mobile/src/sync/ops.dart';

// Kross-platforma vektorlar (desktop/tests/test_vectors.py bilan bir xil, docs/sync-mqtt.md, 11-bo'lim)
final _key = Uint8List.fromList(List<int>.generate(32, (i) => i));
final _seed = Uint8List.fromList(List<int>.generate(32, (i) => i));
const _topic = 'omborai/v2/b562beb66f2a7f7fe4d0830bfd2f84c4/ops';
const _publicKey = '03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8';
const _canonical =
    '{"device":"11111111-1111-1111-1111-111111111111",'
    '"op_id":"00000000-0000-0000-0000-000000000001","payload":{"name":"Do\'kon"},'
    '"store_id":"22222222-2222-2222-2222-222222222222","ts":"2026-10-11T10:00:00.000000Z",'
    '"type":"store"}';
const _signature =
    'hMu8/t+NEx/0Bld56LCTZeGIcoW9kp7eDEBPyzyeUkcogppx//4i6zf4rv5BqiM/iuquDMhSz6NTcv3p55+kBA==';

Map<String, dynamic> _vectorOp() => {
  'op_id': '00000000-0000-0000-0000-000000000001',
  'type': 'store',
  'device': '11111111-1111-1111-1111-111111111111',
  'ts': '2026-10-11T10:00:00.000000Z',
  'store_id': '22222222-2222-2222-2222-222222222222',
  'payload': {'name': "Do'kon"},
};

void main() {
  test('mavzu nomi kross-platforma vektorga teng (v2)', () async {
    expect(await topicFor(_key), _topic);
  });

  test('ochiq kalit vektori', () async {
    final identity = await DeviceIdentity.fromSeed(_seed);
    expect(identity.publicKeyHex, _publicKey);
  });

  test('canonical JSON: kalitlar saralangan, bo\'shliqsiz, sig siz', () {
    final op = _vectorOp()..['sig'] = 'ignored';
    expect(utf8.decode(canonicalBytes(op)), _canonical);
  });

  test('imzo vektori deterministik, va tekshiruvdan o\'tadi', () async {
    final identity = await DeviceIdentity.fromSeed(_seed);
    final op = _vectorOp();
    await signOp(op, identity.keyPair);
    expect(op['sig'], _signature);
    expect(await verifyOp(op, _publicKey), isTrue);
  });

  test('buzilgan operatsiya imzosi rad etiladi', () async {
    final identity = await DeviceIdentity.fromSeed(_seed);
    final op = _vectorOp();
    await signOp(op, identity.keyPair);
    (op['payload'] as Map<String, dynamic>)['name'] = 'Boshqa';
    expect(await verifyOp(op, _publicKey), isFalse);
  });

  test('konvert: seal/open aylanma, AAD va kalit tekshiruvi', () async {
    final raw = await seal(_key, {'hello': 'dunyo', 'n': 1}, _topic);
    expect(jsonDecode(utf8.decode(raw))['v'], 2);
    expect(await openEnvelope(_key, raw, _topic), {'hello': 'dunyo', 'n': 1});
    expect(
      () => openEnvelope(_key, raw, '${_topic}x'),
      throwsA(isA<DecryptionException>()),
    );
    expect(
      () => openEnvelope(Uint8List(32), raw, _topic),
      throwsA(isA<DecryptionException>()),
    );
  });

  test('v1 konvert rad etiladi', () async {
    final raw = await seal(_key, {'a': 1}, _topic);
    final envelope = jsonDecode(utf8.decode(raw)) as Map<String, dynamic>;
    envelope['v'] = 1;
    expect(
      () => openEnvelope(_key, Uint8List.fromList(utf8.encode(jsonEncode(envelope))), _topic),
      throwsA(isA<DecryptionException>()),
    );
  });

  test('JSON ob\'ekt bo\'lmagan xabar DecryptionException (ilova o\'lmaydi)', () async {
    for (final junk in ['[]', '"x"', '123', 'not json']) {
      expect(
        () => openEnvelope(_key, Uint8List.fromList(utf8.encode(junk)), _topic),
        throwsA(isA<DecryptionException>()),
      );
    }
  });

  test('ts formati: aniq 27 belgi, satr bo\'yicha tartiblanadi', () {
    final a = nowTs(DateTime.utc(2026, 10, 11, 10, 0, 0, 5, 7));
    final b = nowTs(DateTime.utc(2026, 10, 11, 10, 0, 1));
    expect(a, '2026-10-11T10:00:00.005007Z');
    expect(a.length, 27);
    expect(a.compareTo(b) < 0, isTrue);
  });
}
