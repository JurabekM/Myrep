import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

/// Kontent manbasi siyosati (SPEC 1.1, 3-bo'lim): ilova umumiy moliyaviy
/// tamoyillardan ilhomlangan, lekin hech bir kitobning personajlari,
/// iqtiboslari, bob nomlari yoki o'xshatishlarini ishlatmaydi va boshqa
/// nashr yoki kompaniya nomini tilga olmaydi. Eski nom ham qaytmasin.
///
/// Taqiqlangan iboralar repoda ochiq matnda saqlanmaydi: har biri
/// `(so'zlar soni, belgilar soni, sha256)` — normallashtirilgan iboradan
/// (kichik harf, `ʻ`/`ʼ` → `'`, so'zlar bitta bo'shliq bilan, UTF-8). Yangi
/// ibora: `python tools/denylist_hash.py "ibora"`.
const _forbidden = <(int, int, String)>[
  // Eski nom.
  (2, 14, '36e2b707c13fd046ad4e348e8dea8067f52989c2054bb5810aa6a1e8b7dfff3a'),
  (2, 14, 'dbba997da93464ab49f6910cde58235f741e4f18a49bf8a976735e61bc5cb20e'),
  // Personajlar.
  (1, 5, '8cbac8124fafefade933e5d4782fe6b9c8f935a38cab36b1f0683bd98fd00c9d'),
  (1, 4, 'b51f5897ebe3cc38461ac3579292e43dadc9c8cdfa9b2f4c9ace30e15716f12d'),
  (1, 4, '96b11bc401cc0891df5d2752391bc108842c8075e3c1c10d438fcadacc5d35d8'),
  (1, 5, '45d5799a1ce83749606bafb4862b3aa1a7fb855c34881d2160b82b0428ba82f9'),
  (1, 6, '176657250f14d05fbe83b68e46342e1af88571745dbf3dc3c27d1a7fb777b648'),
  (1, 6, '8c218fe6d94d2373af2c3f97a36adb78db0b55962c7f80072c8535c673a4b2a2'),
  (1, 5, '776c94684c325892c0c6db31466c03fcf7da697d63daf0d0b6e7ce50a1ae7872'),
  // Kitob bob nomlari va o'xshatishlari.
  (1, 6, 'a65ec91a41d2dd308316faa085f0c34d7b33504423fd42606b81be2b0e62c3ce'),
  (1, 5, '2da65b84f0d26bbdbaa2d77348f0f3ade8925fc911f4f9654bc50fc451e7af56'),
  (2, 11, 'c75f75171311cf2a2cc69812c28f8790cb24ac1a5f98d0d2a039c0781877dd56'),
  (1, 8, 'b17a884873f4199faf5b95f804c3830826165b4bff78c564df79bc1388a6bf81'),
  (1, 6, '421c3b40007cab3849ddd173294c06909652e34f08a789ebde25169fda55cad2'),
  (2, 13, '4af5928462029e3836e800a4b9893c5be5fb2b93eca9273751209000219227bd'),
  (1, 6, '8048079d9f4b6f0a4d7ccd42c46ed25b10a3f27d52d4f61439c9ef6d05293e85'),
  (1, 7, '55049de335d1c111d4d9af8195cc561da5cd74fa97ae242a7a4c79dd008a0f47'),
  (1, 8, '5c9c9d4dd6e3c6b98d3c4a38c712d2bb8b3d6175c1d3aa39d6a47565b4f4bbb0'),
  (1, 5, '406dc3ffb8058295957dbb5786edbd923d1b6beae836347364bd37e116d320af'),
  (1, 7, 'd2f1a57b3d4d52be18eaf300b8b4fe23a295588be67d734736315e103d5ac16d'),
  (1, 9, 'dfd7cedb4835910fd3cf14f1383377ebf0cf95738490b47f6f22dd50853726ab'),
  (1, 6, '592e715d9db2bd0e596b72a702430dc944231e19d305d447902add143d2e47d4'),
  (2, 12, 'a56f2721cd495056a3947d698e7412e83e682fe1320292a2bff03e681e8c206a'),
  (2, 13, '5866a1c345d3dc87de71a2b5716e7f208787c169be656ebe9557f1f0c0302577'),
  (2, 14, '4e5ced6817aa9fe0cfffd5df0e82cc0db73e41f0648bdd6a494706b7df83e4b8'),
  // 8-qonun manbasi: personajlar, joy nomi va o'xshatishlar.
  (1, 5, 'adf38d4e851644d8ba91db71419f579048a6fd7965c3495be1999d6769a11f32'),
  (1, 5, '004c6a67b9c286f95352bb983d8d8ee50e55470e45fb225316961e13267bf627'),
  (1, 7, '972a3cf9612e5a13d01e89f9b1c965f6c29220cfef3a2cbd797addfa0bae7ed6'),
  (1, 7, '951be7db8c23f5b94375c05575073d73e2e0a17dbc4f6ee12d02f978eeb4cfb9'),
  (1, 5, '2556e35217d9acf1f803e1015cca7ddeda6b5464fc56216058816e738afcd288'),
  (1, 5, '35fba0ce5fcb3b266c9d116693a396cf3b41de4dbae6907ea114dbce67db4aa2'),
  (1, 6, 'a4bda2850a83d928ff510cf57439e91d1ce3058a8231c1c280ba4fdbc7f33b95'),
  (1, 6, 'd4914e13d541354e47bbefe3e8e61b54246b31b0c1df738efd15887d68cbee7c'),
  (2, 10, '5a473dbcb05f6535f2c54c54dd6e7fdf1782c5579a92d363e4cef4594fef5cb9'),
  (1, 6, '20487724bdc66c486586e8ef2c50e598da666fbcb84fcc257394393e31659587'),
  (1, 7, '2b979d149d30d705dfbeafb679c1d2c1a05261b50324658d5933f40a0d9ccfea'),
  (1, 6, 'da21ff21f050f19f20a410aea598de27bae29e418cfc7cf2b11ae34f70cece8c'),
  (1, 5, 'eb968eececc5c736e1d5e3adde01ed59d803f01418afadba6b400a59e3d68b0a'),
  (1, 5, '30da382444a1b6fa9e341d47f771571db1a4fd7dcb9f2e227e5f54b5c8580418'),
  (1, 7, '4d7a0fb404d7d7567e282e4d30938831a1f13e904356aaf37c17df321918bbd8'),
  (1, 6, '19732a0e18e85786997300fb6b0ca778fbd6d7ecd72a75ba11dc229abbdc14be'),
  (1, 9, '4f9448b9adf844e1ed0bedf9748290bcd3217a88032a5fbec270ff47fd0fcd35'),
  (1, 7, '675767d1e05cf1cae77c6bf89f3092d0cdeca091e1a15689246f7e7ca840ca1c'),
  (1, 6, 'f240fbe006443575730a9abd0c9fb032fcf7c18c4ac1ae9d76a560afa5f4f301'),
  (1, 7, '535bca66bc41647f4d5cb2e6ee03e968c0c39d89a159f72a0eb95d2807fa65ca'),
  (1, 8, 'e834beb73aa39f82d4a19feb932eae2a09a3ca826015da670b16146bbf2505e8'),
  (1, 6, '8c9ddc94e39463bbda8f072ab2dd0f338a99548150a48721605ec2790c22b205'),
  (1, 7, '74d7adc1cced16377a49dd4cfdbc3ec72845332f58e852b6f03c7f07e5c5428f'),
  (3, 25, '65d289a39c588838071ad275bceb4964679211e4c73d1bb14bf9c7a16122ae8b'),
  (4, 30, '445a459b3ab9626c10547e2a6bc8591db4ab801e269212ff9b0d71549b65646b'),
  // Manba va homiy nomlari.
  (1, 6, '5899dfea33c61d4e323fcffaf01be951fe4102f65f9e08b6765d3bc8f7b797d4'),
  (1, 6, 'fd34dca86e465d9885d9651a5767ffaac15d73c0b4764f3045f9a27e69d526fc'),
  (1, 8, '1431d1e679c1768e3a30e6697b9a521938da5397c8f4f81e75a74fe0c0131841'),
  (1, 7, 'b67a734cb3ce48ac25bfb9a6e8a5072e443e508ce13d467c8a650b344d8c0267'),
];

String _norm(String s) => s.toLowerCase().replaceAll(RegExp('[ʻʼ‘’`]'), "'");

/// So'z: harf yoki raqamdan boshlanadi, ichida va oxirida apostrof bo'lishi
/// mumkin (`tools/denylist_hash.py` bilan bir xil).
final _word = RegExp(r"[\p{L}\p{N}]+(?:'[\p{L}\p{N}]*)*", unicode: true);

String _digest(String s) => sha256.convert(utf8.encode(s)).toString();

final _digests = <String, String>{};

/// [text] dagi taqiqlangan ibora bilan boshlanadigan bo'laklar. Matn
/// so'zlarga bo'linadi; ketma-ket `k` so'z bitta bo'shliq bilan qo'shilib,
/// boshidagi `n` belgi xeshi solishtiriladi — so'z boshidan moslik
/// («namuna» → «namunaviy»).
List<String> forbiddenHits(String text, List<(int, int, String)> denylist) {
  final tokens = [for (final m in _word.allMatches(_norm(text))) m[0]!];
  final groups = <(int, int), Set<String>>{};
  for (final (words, length, digest) in denylist) {
    (groups[(words, length)] ??= {}).add(digest);
  }
  final hits = <String>[];
  for (final MapEntry(key: (words, length), value: digests) in groups.entries) {
    for (var i = 0; i + words <= tokens.length; i++) {
      final joined = tokens.sublist(i, i + words).join(' ');
      if (joined.length < length) continue;
      final head = joined.substring(0, length);
      if (digests.contains(_digests.putIfAbsent(head, () => _digest(head)))) {
        hits.add(head);
      }
    }
  }
  return hits;
}

Iterable<String> _strings(Object? node) sync* {
  if (node is String) {
    yield node;
  } else if (node is Map) {
    for (final v in node.values) {
      yield* _strings(v);
    }
  } else if (node is List) {
    for (final v in node) {
      yield* _strings(v);
    }
  }
}

void main() {
  final sources = {
    for (final f in [
      'lib/app/l10n/arb/app_uz.arb',
      'lib/app/l10n/arb/app_ru.arb',
      'assets/content/chapters.json',
    ])
      f: jsonDecode(File(f).readAsStringSync()),
  };

  test('xeshli roʻyxat haqiqatan ushlaydi (namuna iboralar bilan)', () {
    (int, int, String) entry(String phrase) =>
        (phrase.split(' ').length, phrase.length, _digest(phrase));
    final sample = [entry('namuna'), entry("qo'sh so'z")];
    expect(forbiddenHits('Bu Namunaviy matn', sample), ['namuna']);
    expect(forbiddenHits('«Qoʻsh soʻzlar» ham', sample), ["qo'sh so'z"]);
    expect(forbiddenHits('qoʻsh, soʻz', sample), ["qo'sh so'z"]);
    expect(forbiddenHits('boshqa namunasiz', sample), ['namuna']);
    expect(forbiddenHits('tanamuna misol', sample), isEmpty);
    expect(forbiddenHits('qoʻshimcha soʻz', sample), isEmpty);
  });

  test('roʻyxat yozuvlari toʻgʻri shaklda', () {
    expect(_forbidden, hasLength(54));
    for (final (words, length, digest) in _forbidden) {
      expect(words, inInclusiveRange(1, 6));
      expect(length, greaterThanOrEqualTo(4));
      expect(digest, matches(RegExp(r'^[0-9a-f]{64}$')));
    }
    expect(_forbidden.map((e) => e.$3).toSet(), hasLength(_forbidden.length));
  });

  for (final MapEntry(key: file, value: json) in sources.entries) {
    test('$file — kitob personajlari, iqtiboslari va manba nomlari yoʻq', () {
      final hits = <String>[
        for (final s in _strings(json))
          for (final h in forbiddenHits(s, _forbidden)) '«$h»: $s',
      ];
      expect(hits, isEmpty);
    });
  }

  test('Android yorligʻi va Play identifikatori yangi nomda', () {
    final manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();
    expect(manifest, contains(r'android:label="${appLabel}"'));
    final gradle = File('android/app/build.gradle.kts').readAsStringSync();
    // Asosiy ilova va demo (alohida paket, debug imzo).
    expect(
      gradle,
      contains(
        'applicationId = if (isDemo) "uz.barakadastur.demo" '
        'else "uz.barakadastur.app"',
      ),
    );
    expect(gradle, contains('else "Baraka Dastur"'));
    expect(gradle, contains('if (hasReleaseSigning && !isDemo) "release"'));
  });

  test('darslarda placeholder faqat diniy blokda (ulamo tekshiruvigacha)', () {
    final content =
        jsonDecode(File('assets/content/chapters.json').readAsStringSync())
            as Map<String, dynamic>;
    for (final c in content['chapters'] as List) {
      for (final b in (c as Map)['blocks'] as List) {
        final block = b as Map;
        if (block['type'] == 'religious') continue;
        expect(
          _strings(block).join(' '),
          isNot(contains('Placeholder')),
          reason: '${c['id']} ${block['type']}',
        );
      }
    }
  });
}
