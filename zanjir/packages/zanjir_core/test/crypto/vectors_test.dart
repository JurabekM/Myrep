import 'dart:convert';
import 'dart:io';

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

/// Umumiy vektorlar (`tools/vectors/*.json`) — Python testlari ham aynan shu fayllarni o'qiydi.
Map<String, Object?> _load(String name) =>
    jsonDecode(File('../../tools/vectors/$name').readAsStringSync()) as Map<String, Object?>;

List<Map<String, Object?>> _list(Map<String, Object?> m, String key) => (m[key]! as List).cast<Map<String, Object?>>();

AuditEvent _event(Map<String, Object?> e) => AuditEvent(
  deviceId: e['device_id']! as String,
  seq: e['seq']! as int,
  prevHash: e['prev_hash']! as String,
  eventHash: e['event_hash']! as String,
  actorId: e['actor_id']! as String,
  eventType: e['event_type']! as String,
  entityId: e['entity_id'] as String?,
  payloadHash: e['payload_hash']! as String,
  createdAt: e['created_at']! as String,
  deviceSig: e['device_sig']! as String,
  sigAlg: e['sig_alg']! as String,
);

void main() {
  final canon = _load('canonical_json.json');
  final ed = _load('ed25519.json');
  final chain = _load('hash_chain.json');
  final proto = _load('protocol_signature.json');

  group('canonical_json.json', () {
    for (final c in _list(canon, 'cases')) {
      test(c['name'], () {
        final got = canonicalJson(jsonDecode(c['input_json']! as String));
        expect(got, c['canonical']);
        expect(sha256Hex(utf8.encode(got)), c['sha256']);
      });
    }
    for (final c in _list(canon, 'errors')) {
      test('xato: ${c['name']}', () {
        expect(() => canonicalJson(jsonDecode(c['input_json']! as String)), throwsArgumentError);
      });
    }
    for (final c in _list(canon, 'datetimes')) {
      test('vaqt: ${c['canonical']}', () {
        final p = (c['utc']! as List).cast<int>();
        final t = DateTime.utc(p[0], p[1], p[2], p[3], p[4], p[5], p[6] ~/ 1000, p[6] % 1000);
        expect(canonicalJson(t), c['canonical']);
      });
    }
  });

  group('ed25519.json', () {
    for (final c in _list(ed, 'cases')) {
      test(c['name'], () async {
        final signer = await Ed25519Signer.fromSeed(hexDecode(c['secret']! as String));
        expect(signer.sigAlg, ed['sig_alg']);
        expect(signer.publicKeyHex, c['public']);
        final message = hexDecode(c['message']! as String);
        expect(hexEncode(await signer.sign(message)), c['signature']);
        Future<bool> verify(List<int> m) => verifySignature(
          sigAlg: ed['sig_alg']! as String,
          publicKeyHex: c['public']! as String,
          message: m,
          signatureHex: c['signature']! as String,
        );
        expect(await verify(message), isTrue);
        expect(await verify([...message, 0]), isFalse);
      });
    }

    for (final c in _list(ed, 'reject')) {
      test('rad etilishi shart: ${c['name']}', () async {
        final ok = await verifySignature(
          sigAlg: ed['sig_alg']! as String,
          publicKeyHex: c['public']! as String,
          message: hexDecode(c['message']! as String),
          signatureHex: c['signature']! as String,
        );
        expect(ok, isFalse);
      });
    }

    test('noto\'g\'ri format — false, noma\'lum algoritm — xato', () async {
      final c = _list(ed, 'cases').first;
      expect(
        await verifySignature(
          sigAlg: 'Ed25519',
          publicKeyHex: 'zz',
          message: const [],
          signatureHex: c['signature']! as String,
        ),
        isFalse,
      );
      expect(
        await verifySignature(
          sigAlg: 'Ed25519',
          publicKeyHex: c['public']! as String,
          message: const [],
          signatureHex: '00',
        ),
        isFalse,
      );
      expect(
        await verifySignature(
          sigAlg: 'Ed25519',
          publicKeyHex: '00',
          message: const [],
          signatureHex: c['signature']! as String,
        ),
        isFalse,
      );
      await expectLater(
        verifySignature(
          sigAlg: 'ML-DSA-65',
          publicKeyHex: c['public']! as String,
          message: const [],
          signatureHex: c['signature']! as String,
        ),
        throwsA(isA<UnsupportedSigAlgException>()),
      );
      await expectLater(Ed25519Signer.fromSeed(const [1, 2, 3]), throwsArgumentError);
      expect(const UnsupportedSigAlgException('ML-DSA-65').toString(), contains('ML-DSA-65'));
    });

    test('yangi kalit generatsiyasi', () async {
      final a = await Ed25519Signer.generate();
      final b = await Ed25519Signer.generate();
      expect(a.publicKeyHex, hasLength(64));
      expect(a.publicKeyHex, isNot(b.publicKeyHex));
      final sig = await a.sign(const [1, 2, 3]);
      expect(
        await verifySignature(
          sigAlg: a.sigAlg,
          publicKeyHex: a.publicKeyHex,
          message: const [1, 2, 3],
          signatureHex: hexEncode(sig),
        ),
        isTrue,
      );
    });
  });

  group('hash_chain.json', () {
    final events = [for (final e in _list(chain, 'events')) _event(e)];
    final publicKey = chain['public_key']! as String;

    test('payload_hash, event_hash va imzo qayta hisoblanadi', () async {
      expect(genesisHash, chain['genesis_hash']);
      for (final e in _list(chain, 'events')) {
        expect(payloadHash(e['payload']), e['payload_hash']);
      }
      expect((await verifyChain(events, publicKeyHex: publicKey)).ok, isTrue);
    });

    test('appendEvent — Dart quradigan zanjir vektor bilan baytma-bayt bir xil', () async {
      final signer = await Ed25519Signer.fromSeed(hexDecode(chain['device_seed']! as String));
      expect(signer.publicKeyHex, publicKey);
      AuditEvent? prev;
      for (final e in _list(chain, 'events')) {
        final built = await appendEvent(
          previous: prev,
          signer: signer,
          deviceId: e['device_id']! as String,
          actorId: e['actor_id']! as String,
          eventType: e['event_type']! as String,
          entityId: e['entity_id'] as String?,
          payload: e['payload'],
          createdAt: DateTime.parse(e['created_at']! as String),
        );
        expect(built.toJson(), {...e}..remove('payload'));
        prev = built;
      }
    });

    test('appendEvent — mahalliy vaqt rad etiladi', () async {
      final signer = await Ed25519Signer.fromSeed(List.filled(32, 7));
      await expectLater(
        appendEvent(
          previous: null,
          signer: signer,
          deviceId: 'd',
          actorId: 'a',
          eventType: 'X',
          entityId: null,
          payload: const {},
          createdAt: DateTime(2026),
        ),
        throwsArgumentError,
      );
    });

    test('anchor bilan davom ettirish', () async {
      final a = chain['anchor_case']! as Map<String, Object?>;
      final from = a['events_from']! as int;
      final r = await verifyChain(
        events.sublist(from),
        publicKeyHex: publicKey,
        anchor: events[a['anchor_index']! as int],
      );
      expect(r.ok, a['ok']);
      expect((await verifyChain(events.sublist(2), publicKeyHex: publicKey)).reason, 'seq_gap');
      expect((await verifyChain(const [], publicKeyHex: publicKey)).ok, isTrue);
    });

    for (final t in _list(chain, 'tamper')) {
      test('buzish: ${t['name']}', () async {
        final raw = [for (final e in _list(chain, 'events')) Map<String, Object?>.of(e)];
        if (t['op'] == 'drop') {
          raw.removeAt(t['index']! as int);
        } else {
          raw[t['index']! as int][t['field']! as String] = t['value'];
        }
        final r = await verifyChain([for (final e in raw) _event(e)], publicKeyHex: publicKey);
        expect((r.ok, r.failedIndex, r.reason), (false, t['failed_index'], t['reason']));
      });
    }

    test('boshqa ochiq kalit — imzo xatosi', () async {
      final other = _list(ed, 'cases')[1]['public']! as String;
      final r = await verifyChain(events, publicKeyHex: other);
      expect((r.ok, r.failedIndex, r.reason), (false, 0, 'bad_signature'));
    });

    test('imzoning har bir bitini o\'zgartirish aniqlanadi', () async {
      final sig = hexDecode(events[3].deviceSig);
      for (var i = 0; i < sig.length; i++) {
        final bad = [...sig]..[i] ^= 0x01;
        final tampered = [...events.take(3), events[3].withDeviceSig(hexEncode(bad)), ...events.skip(4)];
        expect((await verifyChain(tampered, publicKeyHex: publicKey)).reason, 'bad_signature', reason: '$i');
      }
    });
  });

  group('protocol_signature.json', () {
    final payload = proto['payload'];
    final pdf = hexDecode(proto['pdf_hex']! as String);
    Future<String?> verify({Object? p, List<int>? pdfBytes, String? pdfSha, String? sig}) => verifyProtocol(
      payload: p ?? payload,
      pdfBytes: pdfBytes ?? pdf,
      signature: ProtocolSignature(
        payloadSha256: proto['payload_sha256']! as String,
        pdfSha256: pdfSha ?? proto['pdf_sha256']! as String,
        signature: sig ?? proto['signature']! as String,
        sigAlg: proto['sig_alg']! as String,
      ),
      publicKeyHex: proto['public_key']! as String,
    );

    test('Dart imzosi vektor bilan bir xil va tekshiruvdan o\'tadi', () async {
      expect(canonicalJson(payload), proto['payload_canonical']);
      expect(
        hexEncode(protocolMessage(proto['payload_sha256']! as String, proto['pdf_sha256']! as String)),
        proto['message_hex'],
      );
      final signer = await Ed25519Signer.fromSeed(hexDecode(chain['device_seed']! as String));
      final s = await signProtocol(payload: payload, pdfBytes: pdf, signer: signer);
      expect(s.payloadSha256, proto['payload_sha256']);
      expect(s.pdfSha256, proto['pdf_sha256']);
      expect(s.signature, proto['signature']);
      expect(s.sigAlg, proto['sig_alg']);
      expect(s.toJson(), {
        'payload_sha256': proto['payload_sha256'],
        'pdf_sha256': proto['pdf_sha256'],
        'signature': proto['signature'],
        'sig_alg': proto['sig_alg'],
      });
      expect(await verify(), isNull);
    });

    test('PDF ning har bir bayti o\'zgarsa aniqlanadi', () async {
      for (var i = 0; i < pdf.length; i++) {
        final bad = [...pdf]..[i] ^= 0xFF;
        expect(await verify(pdfBytes: bad), 'pdf_hash_mismatch', reason: '$i');
      }
    });

    test('payload o\'zgarsa aniqlanadi', () async {
      final changed = jsonDecode(jsonEncode(payload)) as Map<String, Object?>;
      ((changed['measurements']! as List)[1] as Map<String, Object?>)['verdict'] = 'PASS';
      expect(await verify(p: changed), 'payload_hash_mismatch');
    });

    test('imzo bayti yoki PDF+hash almashtirilsa aniqlanadi', () async {
      final sig = hexDecode(proto['signature']! as String);
      for (var i = 0; i < sig.length; i++) {
        final bad = [...sig]..[i] ^= 0x80;
        expect(await verify(sig: hexEncode(bad)), 'bad_signature', reason: '$i');
      }
      final other = utf8.encode('%PDF-1.7\nboshqa\n%%EOF\n');
      expect(await verify(pdfBytes: other, pdfSha: sha256Hex(other)), 'bad_signature');
    });
  });

  group('hex', () {
    test('kodlash va xatolar', () {
      expect(hexEncode(const [0, 15, 255]), '000fff');
      expect(hexDecode('000fFF'), [0, 15, 255]);
      expect(() => hexDecode('abc'), throwsFormatException);
      expect(() => hexDecode('zz'), throwsFormatException);
    });
  });
}
