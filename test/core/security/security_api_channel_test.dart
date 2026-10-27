import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Generatsiya qilingan Pigeon kodini kanal darajasida tekshiradi: Kotlin
/// tomoni qaytaradigan formatdagi javob Dart obyektiga toʻgʻri aylanadi.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const prefix = 'dev.flutter.pigeon.baraka_daftari.SecurityApi';
  const codec = SecurityApi.pigeonChannelCodec;
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

  tearDown(() {
    for (final m in ['ping', 'getOrCreateDatabaseKey']) {
      messenger.setMockMessageHandler('$prefix.$m', null);
    }
  });

  test('ping native javobni NativeInfo ga aylantiradi', () async {
    messenger.setMockMessageHandler(
      '$prefix.ping',
      (message) async => codec.encodeMessage(<Object?>[
        NativeInfo(apiVersion: 1, androidSdkInt: 36),
      ]),
    );
    final info = await SecurityApi().ping();
    expect(info.apiVersion, 1);
    expect(info.androidSdkInt, 36);
  });

  test('UNIMPLEMENTED stub PlatformException sifatida keladi', () async {
    messenger.setMockMessageHandler(
      '$prefix.getOrCreateDatabaseKey',
      (message) async => codec.encodeMessage(<Object?>[
        'UNIMPLEMENTED',
        'getOrCreateDatabaseKey hali amalga oshirilmagan (Vazifa 2)',
        null,
      ]),
    );
    await expectLater(
      SecurityApi().getOrCreateDatabaseKey(),
      throwsA(
        isA<PlatformException>().having((e) => e.code, 'code', 'UNIMPLEMENTED'),
      ),
    );
  });

  test('native tomon ulanmagan boʻlsa channel-error beradi', () async {
    await expectLater(
      SecurityApi().ping(),
      throwsA(isA<PlatformException>()),
    );
  });
}
