import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/auth.dart';

void main() {
  // Desktop (Python hashlib) bilan bir xil natija: tuz 16 nol bayt, parol "parol-12345", 100 000 iteratsiya.
  const zeroSalt = '00000000000000000000000000000000';
  const pythonHash =
      'ee416d3b8c2fdcf3fe058e0a88632210910bd558e427ded086686ae4e5d8011c';

  test('PBKDF2 natijasi desktop (Python) bilan mos', () async {
    final h = await hashPassword('parol-12345', saltHex: zeroSalt);
    expect(h.hash, pythonHash);
    expect(await verifyPassword('parol-12345', zeroSalt, pythonHash), isTrue);
    expect(await verifyPassword('parol-12346', zeroSalt, pythonHash), isFalse);
  });

  test("har safar yangi tuz beriladi", () async {
    final a = await hashPassword('parol-12345');
    final b = await hashPassword('parol-12345');
    expect(a.salt, isNot(b.salt));
    expect(a.salt.length, 32);
  });

  test('login katta-kichik harfga bog\'liq emas', () {
    expect(normalizeLogin('  Kassir1 '), 'kassir1');
  });

  test('juftlash kodi: to\'g\'ri qabul, noto\'g\'risi FormatException', () {
    const id = '11111111-2222-3333-4444-555555555555';
    final key = 'ab' * 32;
    final code = makePairingCode(id, key);
    expect(parsePairingCode(code), (id, key));
    expect(parsePairingCode('  ${code.toUpperCase()} '), (id, key));
    for (final bad in [
      '',
      'nocolon',
      'x:$key',
      '$id:xyz',
      '$id:${'ab' * 31}',
    ]) {
      expect(() => parsePairingCode(bad), throwsFormatException, reason: bad);
    }
  });
}
