import 'dart:convert';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

import '../repo/context.dart';

/// Shifrlangan fayl qobig'i (zaxira va almashish fayllari uchun umumiy, ADR-0017):
///
///     magic (4 bayt) | versiya (1) | uint32 BE sarlavha uzunligi | sarlavha (JSON) | shifrmatn | MAC (16 bayt)
///
/// Shifr — ChaCha20-Poly1305, AAD = sarlavha bilan butun prefiks (sarlavhani o'zgartirsa ochilmaydi). Kalit — 32 bayt
/// (paroldan [deriveKey] yoki tasodifiy laboratoriya kaliti). Og'ir hisob alohida isolate'da (UI qotmaydi).
typedef SealedFrame = ({Object? header, List<int> prefix, List<int> cipherText, List<int> mac});

const _fixed = 4 + 1 + 4;
const _maxHeader = 4096;

List<int> framePrefix(List<int> magic, int version, Object header) {
  final headerBytes = utf8.encode(jsonEncode(header));
  return [...magic, version, ...(ByteData(4)..setUint32(0, headerBytes.length)).buffer.asUint8List(), ...headerBytes];
}

/// Faqat ramka va sarlavha JSON'i (kalitsiz). Mos bo'lmasa — [invalidCode] bilan [DataRuleException].
SealedFrame parseFrame(List<int> bytes, List<int> magic, int version, String invalidCode) {
  bool startsWithMagic() {
    for (var i = 0; i < magic.length; i++) {
      if (bytes[i] != magic[i]) return false;
    }
    return true;
  }

  if (bytes.length < _fixed + 16 || !startsWithMagic() || bytes[4] != version) {
    throw DataRuleException(invalidCode, 'magic');
  }
  final len = ByteData.sublistView(Uint8List.fromList(bytes.sublist(5, 9))).getUint32(0);
  if (len > _maxHeader || _fixed + len + 16 > bytes.length) throw DataRuleException(invalidCode, 'header');
  final Object? json;
  try {
    json = jsonDecode(utf8.decode(bytes.sublist(_fixed, _fixed + len)));
  } on FormatException {
    throw DataRuleException(invalidCode, 'header');
  }
  return (
    header: json,
    prefix: bytes.sublist(0, _fixed + len),
    cipherText: bytes.sublist(_fixed + len, bytes.length - 16),
    mac: bytes.sublist(bytes.length - 16),
  );
}

/// Argon2id parametrlari (RFC 9106, 2-tavsiya ruhida: 64 MiB, t=3, p=1). Faylda saqlanadi; o'qishda chegaralar
/// tekshiriladi (zararli fayl telefonni xotirasiz qoldirmasin).
class KdfParams {
  const KdfParams({required this.memoryKib, required this.iterations, required this.parallelism});
  final int memoryKib;
  final int iterations;
  final int parallelism;

  static const standard = KdfParams(memoryKib: 64 * 1024, iterations: 3, parallelism: 1);

  Map<String, Object?> toJson() => {
    'alg': 'argon2id',
    'memory_kib': memoryKib,
    'iterations': iterations,
    'parallelism': parallelism,
  };

  static KdfParams fromJson(Object? j, {String invalidCode = 'backup_invalid'}) {
    if (j is! Map || j['alg'] != 'argon2id') throw DataRuleException(invalidCode, 'kdf');
    final m = j['memory_kib'], t = j['iterations'], p = j['parallelism'];
    if (m is! int || t is! int || p is! int || m < 8 * 1024 || m > 256 * 1024 || t < 1 || t > 10 || p < 1 || p > 4) {
      throw DataRuleException(invalidCode, 'kdf');
    }
    return KdfParams(memoryKib: m, iterations: t, parallelism: p);
  }
}

/// Paroldan 32 baytli kalit.
Future<List<int>> deriveKey(String password, KdfParams kdf, List<int> salt) => Isolate.run(() async {
  final key = await Argon2id(
    parallelism: kdf.parallelism,
    memory: kdf.memoryKib,
    iterations: kdf.iterations,
    hashLength: 32,
  ).deriveKeyFromPassword(password: password, nonce: salt);
  return key.extractBytes();
});

/// Shifrmatn + MAC.
Future<List<int>> sealBytes(
  List<int> plain, {
  required List<int> key,
  required List<int> nonce,
  required List<int> aad,
}) => Isolate.run(() async {
  final box = await Chacha20.poly1305Aead().encrypt(plain, secretKey: SecretKey(key), nonce: nonce, aad: aad);
  return [...box.cipherText, ...box.mac.bytes];
});

/// `null` — kalit noto'g'ri yoki fayl o'zgartirilgan (MAC mos emas).
Future<List<int>?> openFrame(SealedFrame f, {required List<int> key, required List<int> nonce}) =>
    Isolate.run(() async {
      try {
        return await Chacha20.poly1305Aead().decrypt(
          SecretBox(f.cipherText, nonce: nonce, mac: Mac(f.mac)),
          secretKey: SecretKey(key),
          aad: f.prefix,
        );
      } on SecretBoxAuthenticationError {
        return null;
      }
    });
