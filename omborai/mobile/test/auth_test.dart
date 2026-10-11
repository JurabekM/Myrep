import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/auth.dart';

const _store = '5151ea51-5151-4151-8151-515151515151';
const _owner = '11111111-2222-4333-8444-555555555555';
final _ownerKey = 'cd' * 32;
final _storeKey = 'ab' * 32;

void main() {
  test('parol xeshi: bir xil tuz — bir xil natija; boshqa parol — boshqa natija', () async {
    final first = await hashPassword('parol-12345', saltHex: '00112233445566778899aabbccddeeff');
    expect(first.salt, '00112233445566778899aabbccddeeff');
    expect(first.hash.length, 64);
    expect(await verifyPassword('parol-12345', first.salt, first.hash), isTrue);
    expect(await verifyPassword('parol-12346', first.salt, first.hash), isFalse);
  });

  test('yangi tuz har safar boshqa', () async {
    final a = await hashPassword('parol-12345');
    final b = await hashPassword('parol-12345');
    expect(a.salt == b.salt, isFalse);
  });

  test('juftlash kodi v2: yasash va o\'qish aylanma', () {
    final code = makePairingCode(_store, _owner, _ownerKey, _storeKey);
    expect(code, '$_store:$_owner:$_ownerKey:$_storeKey');
    final parsed = parsePairingCode('  ${code.toUpperCase()}  ');
    expect(parsed, (_store, _owner, _ownerKey, _storeKey));
  });

  test('noto\'g\'ri juftlash kodlari FormatException', () {
    final bad = [
      '',
      '$_store:$_storeKey', // eski 2 maydonli shakl
      '$_store:$_owner:$_ownerKey', // 3 maydon
      'not-a-uuid:$_owner:$_ownerKey:$_storeKey',
      '$_store:$_owner:${'xy' * 32}:$_storeKey',
      '$_store:$_owner:$_ownerKey:${'ab' * 31}',
    ];
    for (final code in bad) {
      expect(() => parsePairingCode(code), throwsA(isA<FormatException>()), reason: code);
    }
  });

  test('login normalizatsiyasi', () {
    expect(normalizeLogin('  ALI  '), 'ali');
  });
}
