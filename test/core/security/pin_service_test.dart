import 'dart:convert';
import 'dart:typed_data';

import 'package:baraka_daftari/core/security/pin/lockout_policy.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/pin/pin_models.dart';
import 'package:baraka_daftari/core/security/pin/pin_policy.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/fakes.dart';
import '../../helpers/pump_app.dart';

String _hex(List<int> b) =>
    b.map((e) => e.toRadixString(16).padLeft(2, '0')).join();

void main() {
  group('PBKDF2-HMAC-SHA256 etaloni (RFC 7914 KAT)', () {
    test('c = 1', () {
      final dk = pbkdf2Sha256(
        utf8.encode('passwd'),
        utf8.encode('salt'),
        1,
        64,
      );
      expect(
        _hex(dk),
        '55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc'
        '49ca9cccf179b645991664b39d77ef317c71b845b1e30bd509112041d3a19783',
      );
    });

    test('c = 80 000', () {
      final dk = pbkdf2Sha256(
        utf8.encode('Password'),
        utf8.encode('NaCl'),
        80000,
        64,
      );
      expect(
        _hex(dk),
        '4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56'
        'a1d425a1225833549adb841b51c9b3176a272bdebba1d078478f62b397f33c8d',
      );
    });
  });

  group('PinPolicy', () {
    test('faqat 6 ta raqam', () {
      expect(PinPolicy.validate('25803'), PinIssue.wrongLength);
      expect(PinPolicy.validate('2580367'), PinIssue.wrongLength);
      expect(PinPolicy.validate('25a036'), PinIssue.notDigits);
      expect(PinPolicy.validate('258036'), isNull);
    });

    test('oson topiladigan kodlar rad etiladi', () {
      for (final pin in ['000000', '111111', '123456', '345678', '987654']) {
        expect(PinPolicy.validate(pin), PinIssue.tooSimple, reason: pin);
      }
      expect(PinPolicy.validate('135790'), isNull);
    });
  });

  group('LockoutPolicy', () {
    test('dastlabki 4 xato — kutishsiz, 5-dan boshlab oʻsib boradi', () {
      for (var n = 0; n < 5; n++) {
        expect(LockoutPolicy.delayAfter(n), isNull);
      }
      expect(LockoutPolicy.delayAfter(5), const Duration(seconds: 30));
      expect(LockoutPolicy.delayAfter(6), const Duration(minutes: 1));
      expect(LockoutPolicy.delayAfter(7), const Duration(minutes: 2));
      expect(LockoutPolicy.delayAfter(8), const Duration(minutes: 4));
    });

    test('eng koʻpi 1 soat, katta sonlarda ham toshmaydi', () {
      expect(LockoutPolicy.delayAfter(12), const Duration(hours: 1));
      expect(LockoutPolicy.delayAfter(1000), const Duration(hours: 1));
    });
  });

  group('PinService', () {
    late InMemorySecureBlobStore store;
    late ReferencePinHasher hasher;
    late FakeClock clock;
    late PinService service;

    PinService newService() =>
        PinService(store: store, hasher: hasher, clock: clock);

    setUp(() async {
      store = InMemorySecureBlobStore();
      hasher = ReferencePinHasher();
      clock = FakeClock();
      service = newService();
      await service.setPin(testPin);
    });

    test('PIN oʻzi saqlanmaydi, yozuvda ≥310k iteratsiya va tuz bor', () async {
      expect(await service.isPinSet(), isTrue);
      final raw = utf8.decode(store.blobs[PinService.recordBlob]!);
      expect(raw, isNot(contains(testPin)));
      final record = PinRecord.fromJson(
        jsonDecode(raw) as Map<String, dynamic>,
      );
      expect(record.algorithm, 'PBKDF2-HMAC-SHA256');
      expect(record.iterations, greaterThanOrEqualTo(310000));
      expect(hasher.iterationsSeen.single, greaterThanOrEqualTo(310000));
      expect(base64Decode(record.salt), hasLength(16));
      expect(base64Decode(record.hash), hasLength(32));
    });

    test('har oʻrnatishda tuz yangi', () async {
      final first = (await store.readJson(PinService.recordBlob))!['salt'];
      await service.setPin(testPin);
      final second = (await store.readJson(PinService.recordBlob))!['salt'];
      expect(second, isNot(first));
    });

    test('oddiy PIN oʻrnatilmaydi', () {
      expect(() => service.setPin('123456'), throwsArgumentError);
    });

    test('toʻgʻri PIN qabul qilinadi', () async {
      expect(await service.verify(testPin), isA<PinAccepted>());
    });

    test('notoʻgʻri PIN: qolgan urinishlar kamayadi', () async {
      for (final left in [4, 3, 2, 1]) {
        final r = await service.verify('000001');
        expect(r, isA<PinRejected>());
        expect((r as PinRejected).attemptsBeforeLockout, left);
      }
    });

    test('5-xatoda kutish, kutish paytida PIN hisoblanmaydi', () async {
      for (var i = 0; i < 4; i++) {
        await service.verify('000001');
      }
      final fifth = await service.verify('000001');
      expect(fifth, isA<PinLockedOut>());
      expect(
        (fifth as PinLockedOut).until,
        clock.nowUtc().add(const Duration(seconds: 30)),
      );

      final callsBefore = hasher.calls;
      clock.advance(const Duration(seconds: 29));
      expect(await service.verify(testPin), isA<PinLockedOut>());
      expect(
        hasher.calls,
        callsBefore,
        reason: 'kutishda hosila hisoblanmaydi',
      );
    });

    test('kutish tugagach yana xato — kutish ikki baravar', () async {
      for (var i = 0; i < 5; i++) {
        await service.verify('000001');
      }
      clock.advance(const Duration(seconds: 30));
      final sixth = await service.verify('000001');
      expect(
        (sixth as PinLockedOut).until,
        clock.nowUtc().add(const Duration(minutes: 1)),
      );
    });

    test('kutishdan keyin toʻgʻri PIN hisoblagichni tozalaydi', () async {
      for (var i = 0; i < 5; i++) {
        await service.verify('000001');
      }
      clock.advance(const Duration(seconds: 31));
      expect(await service.verify(testPin), isA<PinAccepted>());
      final r = await service.verify('000001') as PinRejected;
      expect(r.attemptsBeforeLockout, 4);
    });

    test('lockout ilova qayta ishga tushganda ham saqlanadi', () async {
      for (var i = 0; i < 5; i++) {
        await service.verify('000001');
      }
      final restarted = newService();
      expect(await restarted.verify(testPin), isA<PinLockedOut>());
      expect(await restarted.activeLockoutUntil(), isNotNull);
    });

    test('soatni orqaga surish kutishni qisqartirmaydi', () async {
      for (var i = 0; i < 5; i++) {
        await service.verify('000001');
      }
      clock.advance(const Duration(hours: -3));
      final r = await service.verify(testPin);
      expect(r, isA<PinLockedOut>());
      expect(
        (r as PinLockedOut).until,
        clock.nowUtc().add(const Duration(seconds: 30)),
      );
    });

    test('resetFailures biometriyadan keyin hisoblagichni tozalaydi', () async {
      await service.verify('000001');
      await service.verify('000001');
      await service.resetFailures();
      final r = await service.verify('000001') as PinRejected;
      expect(r.attemptsBeforeLockout, 4);
    });

    test('PIN oʻrnatilmagan boʻlsa tekshiruv xato beradi', () async {
      final empty = PinService(
        store: InMemorySecureBlobStore(),
        hasher: hasher,
        clock: clock,
      );
      expect(await empty.isPinSet(), isFalse);
      expect(() => empty.verify(testPin), throwsStateError);
    });
  });

  test('NativePinHasher Kotlin hosilasiga argumentlarni uzatadi', () async {
    registerFallbackValue(Uint8List(0));
    final api = MockSecurityApi();
    final salt = Uint8List(16);
    when(
      () => api.derivePinKey(any(), any(), any()),
    ).thenAnswer((_) async => Uint8List(32));
    await NativePinHasher(api).derive(testPin, salt, 310000);
    verify(() => api.derivePinKey(testPin, salt, 310000)).called(1);
  });
}
