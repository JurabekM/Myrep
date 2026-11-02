import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:rostor2/core/db.dart';
import 'package:rostor2/core/phone.dart';
import 'package:rostor2/core/risk.dart';
import 'package:rostor2/engine/apk_rules.dart';
import 'package:rostor2/engine/audit_rules.dart';
import 'package:rostor2/engine/domain_tools.dart';
import 'package:rostor2/engine/link_rules.dart';
import 'package:rostor2/engine/text_rules.dart';

/// Testlar haqiqiy registry/registry.json (ilovaga imzolanib kiradigan ma'lumot) bilan ishlaydi.
RostorDb loadDb() {
  final raw = File('../registry/registry.json').readAsStringSync();
  return RostorDb.fromPayload(raw, (jsonDecode(raw) as Map)['db_version'] as int);
}

Set<String> codes(Iterable<Finding> f) => {for (final x in f) x.code};

void main() {
  final db = loadDb();

  group('domain_tools', () {
    test('punycode RFC 3492', () {
      expect(punycodeDecode('bcher-kva'), 'bücher');
      expect(decodeIdnHost('xn--lick-k6d.uz'), 'сlick.uz');
    });
    test('skeleton gomogliflarni birlashtiradi', () {
      expect(skeleton('c1ick'), skeleton('click'));
      expect(skeleton('payrne'), skeleton('payme'));
      expect(skeleton('сlick'), skeleton('click'));
    });
    test('registrableDomain', () {
      expect(registrableDomain('pay.click.uz'), 'click.uz');
      expect(registrableDomain('my.gov.uz'), 'my.gov.uz');
    });
  });

  group('Havola Qalqoni', () {
    test('rasmiy domen', () {
      final r = analyzeUrl('https://click.uz/payments', db);
      expect(r.severity, Severity.ok);
      expect(codes(r.findings), contains('link.official'));
      expect(analyzeUrl('https://my.gov.uz/uz', db).severity, Severity.ok);
    });
    test('raqamli gomoglif', () {
      expect(codes(analyzeUrl('https://c1ick.uz/login', db).findings), contains('link.homoglyph'));
    });
    test('kirill harfli IDN gomoglif', () {
      final r = analyzeUrl('http://xn--lick-k6d.uz', db);
      expect(r.severity, Severity.critical);
      expect(codes(r.findings), containsAll(['link.homoglyph', 'link.mixed_script']));
      expect(codes(analyzeUrl('xn--paym-y4d.uz', db).findings), contains('link.homoglyph'));
    });
    test("'@' bilan aldash", () {
      final r = analyzeUrl('http://click.uz@evil.top/login', db);
      expect(r.host, 'evil.top');
      expect(codes(r.findings), containsAll(['link.userinfo', 'link.risky_tld']));
      expect(r.severity, Severity.critical);
    });
    test('brend nomi begona domenda', () {
      expect(codes(analyzeUrl('click-uz.top', db).findings), contains('link.brand_abuse'));
      expect(codes(analyzeUrl('https://olx-uz.delivery-safe.top/pay', db).findings), contains('link.brand_abuse'));
      expect(codes(analyzeUrl('paymebonus.com', db).findings), contains('link.brand_abuse'));
    });
    test("o'xshash nom", () {
      expect(codes(analyzeUrl('paymee.uz', db).findings), contains('link.lookalike'));
    });
    test("brend so'zi bilan boshlanuvchi begona so'z soxta signal bermaydi", () {
      expect(codes(analyzeUrl('https://clickhouse.com', db).findings), isNot(contains('link.brand_abuse')));
    });
    test('qisqartiruvchi va Telegram', () {
      expect(codes(analyzeUrl('bit.ly/abc', db).findings), contains('link.shortener'));
      expect(codes(analyzeUrl('https://t.me/golos_premium_bot?start=1', db).findings), contains('link.telegram_lure'));
    });
    test('notanish oddiy sayt', () {
      expect(codes(analyzeUrl('https://example.com', db).findings), {'link.no_signal'});
    });
    test('matndan havola ajratish', () {
      expect(extractUrls('Mana: https://click.uz/x, va bit.ly/abc.'), ['https://click.uz/x', 'bit.ly/abc']);
    });
  });

  group('Xabar tekshiruvi', () {
    test('rus tilidagi vishing', () {
      final r = analyzeText(
          'Здравствуйте, это служба безопасности банка. Назовите код из СМС, чтобы отменить подозрительную операцию', db);
      expect(codes(r.findings), containsAll(['text.otp_request', 'text.account_blocked']));
      expect(r.severity, Severity.critical);
    });
    test("haqiqiy OTP SMS kritik deb belgilanmaydi", () {
      final r = analyzeText('Kod: 482913. Kodni hech kimga aytmang. CLICK', db);
      expect(r.severity < Severity.high, isTrue, reason: codes(r.findings).toString());
      expect(codes(r.findings), contains('text.benign_otp'));
    });
    test('OLX: pul olish uchun karta muddati', () {
      final r = analyzeText('Pulni olish uchun karta raqami va amal qilish muddatini yuboring olx-uz.delivery.top', db);
      expect(codes(r.findings), containsAll(['text.receive_money_trap', 'text.card_secret']));
      expect(r.links.single.severity, Severity.high);
    });
    test('Telegram ovoz berish', () {
      final r = analyzeText('Iltimos, qizimga ovoz bering: t.me/konkurs_ovoz_bot', db);
      expect(codes(r.findings), contains('text.telegram_takeover'));
      expect(r.severity, Severity.high);
    });
    test("o'zbek kirill: davlat nomidan qo'rqitish", () {
      final r = analyzeText('Сизга қарши жиноий иш очилган, зудлик билан тўлов қилинг', db);
      expect(codes(r.findings), containsAll(['text.authority_threat', 'text.urgency']));
    });
    test('oddiy xabar', () {
      expect(codes(analyzeText('Ertaga soat 10 da uchrashamiz', db).findings), {'text.no_signal'});
    });
  });

  group('APK Qalqon', () {
    Map<String, dynamic> base() => {
          'ok': true,
          'parsed': true,
          'sigVerified': true,
          'sigSchemes': ['v2', 'v3'],
          'signers': [
            {'sha256': 'aa' * 32, 'debug': false}
          ],
          'lineage': <String>[],
          'permissions': <String>[],
          'accessibilityServices': <String>[],
          'notificationListeners': <String>[],
          'deviceAdmins': <String>[],
          'targetSdk': 34,
          'fileName': 'app.apk',
          'fileSha256': '00' * 32,
          'installed': null,
          'sameLabelInstalled': <Map>[],
        };

    test('soxta Click: nom taqlidi + bank troyani belgilari', () {
      final f = base()
        ..['label'] = 'Click'
        ..['packageName'] = 'uz.click.bonus'
        ..['fileName'] = 'Click_yangilanish.apk'
        ..['permissions'] = ['android.permission.RECEIVE_SMS']
        ..['accessibilityServices'] = ['x.A']
        ..['signers'] = [
          {'sha256': 'bb' * 32, 'debug': true}
        ]
        ..['sameLabelInstalled'] = [
          {
            'label': 'Click',
            'packageName': 'air.com.ssdsoftwaresolutions.clickuz',
            'installer': {'installing': 'com.android.vending'}
          }
        ];
      final r = evaluateApk(f, db);
      expect(codes(r.findings),
          containsAll(['apk.label_clone', 'apk.brand_impersonation', 'apk.banker_combo', 'apk.debug_cert', 'apk.lure_name']));
      expect(r.severity, Severity.critical);
      expect(r.findings.first.severity, Severity.critical);
    });

    test("o'rnatilgan ilovaning yangilanishi", () {
      final f = base()
        ..['label'] = 'Paynet'
        ..['packageName'] = 'uz.paynet.app'
        ..['installed'] = {
          'certSha256': ['aa' * 32],
          'historySha256': <String>[],
          'installer': {'installing': 'com.android.vending'}
        };
      final r = evaluateApk(f, db);
      expect(codes(r.findings), contains('apk.same_as_installed'));
      expect(r.severity < Severity.medium, isTrue);
    });

    test("fayldan o'rnatilgan nusxa bilan bir xil imzo ishonch bermaydi (emulyatorda topilgan xato)", () {
      final f = base()
        ..['label'] = 'Click'
        ..['packageName'] = 'uz.click.bonus'
        ..['permissions'] = ['android.permission.RECEIVE_SMS', 'android.permission.REQUEST_INSTALL_PACKAGES']
        ..['accessibilityServices'] = ['x.A']
        ..['installed'] = {
          'certSha256': ['aa' * 32],
          'historySha256': <String>[],
          'installer': {'installing': null, 'initiating': null}
        };
      final r = evaluateApk(f, db);
      expect(codes(r.findings), contains('apk.same_as_sideloaded'));
      expect(codes(r.findings), isNot(contains('apk.same_as_installed')));
      expect(r.findings.firstWhere((x) => x.code == 'apk.banker_combo').severity, Severity.critical);
      expect(r.findings.firstWhere((x) => x.code == 'apk.dropper').severity, Severity.high);
    });

    test("o'rnatilgan ilova boshqa kalit bilan", () {
      final f = base()
        ..['label'] = 'Paynet'
        ..['packageName'] = 'uz.paynet.app'
        ..['installed'] = {
          'certSha256': ['cc' * 32],
          'historySha256': <String>[],
          'installer': {'installing': 'com.android.vending'}
        };
      expect(codes(evaluateApk(f, db).findings), contains('apk.installed_mismatch'));
    });

    test('buzilgan imzo, ikki kengaytma, taqlid paket', () {
      expect(codes(evaluateApk(base()..['sigVerified'] = false, db).findings), contains('apk.sig_invalid'));
      expect(codes(evaluateApk(base()..['fileName'] = 'rasm.jpg.apk', db).findings), contains('apk.double_ext'));
      final iiv = evaluateApk(base()
        ..['packageName'] = 'uz.iiv.portal'
        ..['label'] = 'IIV UZ', db);
      expect(codes(iiv.findings), contains('apk.lookalike'));
    });

    test("o'qib bo'lmagan fayl", () {
      final r = evaluateApk({'ok': false, 'error': "Faylga ruxsat berilmadi"}, db);
      expect(codes(r.findings), {'apk.read_error'});
    });
  });

  group('Qurilma auditi', () {
    Map<String, dynamic> app(String pkg, {Map<String, String?>? installer, bool system = false}) => {
          'packageName': pkg,
          'label': pkg,
          'system': system,
          'installer': installer ?? {'installing': 'com.android.vending', 'initiating': 'com.android.vending'},
          'hasLauncher': true,
          'requested': <String>[],
          'granted': <String>[],
          'certSha256': ['dd' * 32],
        };

    test("Telegram'dan kelgan ilovada Maxsus imkoniyatlar", () {
      final a = evaluateApp(
          app('com.evil.sms', installer: {'installing': 'com.google.android.packageinstaller', 'initiating': 'org.telegram.messenger'})
            ..['accessibilityOn'] = true
            ..['hasLauncher'] = false
            ..['granted'] = ['android.permission.RECEIVE_SMS'],
          db);
      expect(a.source, Source.messenger);
      expect(codes(a.findings), containsAll(['app.accessibility_on', 'app.sms_granted', 'app.hidden_icon']));
      expect(a.severity, Severity.critical);
    });

    test("Play'dagi ilova va tizim ilovasi yumshoqroq baholanadi", () {
      expect(evaluateApp(app('com.example.helper')..['accessibilityOn'] = true, db).severity, Severity.medium);
      expect(evaluateApp(app('com.android.talkback', system: true)..['accessibilityOn'] = true, db).severity, Severity.info);
    });

    test("Telegram'ga APK o'rnatish ruxsati", () {
      final a = evaluateApp(app('org.telegram.messenger')..['installUnknownAllowed'] = true, db);
      final f = a.findings.firstWhere((x) => x.code == 'app.install_unknown');
      expect(f.severity, Severity.medium);
      expect(f.action?.kind, 'openUnknownSources');
    });

    test('rasmiy emas taqlid paket', () {
      expect(codes(evaluateApp(app('uz.meganet.uzmobile'), db).findings), contains('app.lookalike'));
    });

    test('qurilma holati', () {
      final f = evaluateDevice({
        'screenLock': false,
        'adbEnabled': true,
        'securityPatch': '2024-01-05',
        'sdkInt': 34,
        'rootIndicators': <String>[],
      }, now: DateTime(2026, 11, 1));
      expect(codes(f), containsAll(['device.no_lock', 'device.adb', 'device.old_patch']));
    });
  });

  group('Raqamlar (F2)', () {
    final kat = jsonDecode(File('test/fixtures/phone_kat.json').readAsStringSync()) as Map<String, dynamic>;
    List<List<dynamic>> pairs(String k) => [for (final p in kat[k] as List) p as List];

    test('normalizePhone umumiy KAT bilan (Kotlin bilan bir xil)', () {
      for (final p in pairs('normalize')) {
        expect(normalizePhone(p[0] as String), p[1], reason: 'normalize(${p[0]})');
      }
    });
    test('rasmiy raqam qidiruvi umumiy KAT bilan', () {
      for (final p in pairs('lookup')) {
        final o = db.orgsByPhone(p[0] as String);
        expect(o.isEmpty ? null : o.first.id, p[1], reason: 'lookup(${p[0]})');
      }
      for (final p in pairs('display')) {
        expect(displayPhone(p[0] as String), p[1]);
      }
    });
    test('extractPhones: summa va karta raqami raqam emas', () {
      expect(extractPhones("Click: 90 123 45 67 ga qo'ng'iroq qiling"), ['+998901234567']);
      expect(extractPhones("Hisobingizga 500 000 000 so'm tushdi"), isEmpty);
      expect(extractPhones('Karta 8600 1234 5678 9012'), isEmpty);
      expect(extractPhones('Kod: 123456'), isEmpty);
      expect(extractPhones('+7 912 345-67-89 yoki +998 71 231 08 80'), ['+79123456789', '+998712310880']);
    });
    test("bank nomidan rasmiy bo'lmagan raqam — yuqori", () {
      final r = analyzeText("Hurmatli mijoz! Uzcard kartangiz bloklandi. Tiklash uchun 90 123 45 67 raqamiga qo'ng'iroq qiling.", db);
      expect(codes(r.findings), containsAll(['text.phone_not_official', 'text.account_blocked', 'text.combo']));
      expect(r.severity, Severity.critical);
      final f = r.findings.firstWhere((f) => f.code == 'text.phone_not_official');
      expect(f.explain, contains('+998 71 200 28 28'));
    });
    test('kirill va rus tilida ham', () {
      final r = analyzeText('Служба безопасности Humo: позвоните по номеру +7 912 345 67 89', db);
      expect(codes(r.findings), contains('text.phone_not_official'));
    });
    test("rasmiy raqam — ma'lumot, qo'ng'iroqqa undamasa nom yolg'iz signal emas", () {
      final ok = analyzeText("Click qo'llab-quvvatlash: +998 71 231 08 80 ga qo'ng'iroq qiling", db);
      expect(codes(ok.findings), {'text.phone_official'});
      final grape = analyzeText('Uzum sotiladi, arzon. Tel 90 123 45 67', db);
      expect(codes(grape.findings), isNot(contains('text.phone_not_official')));
      final grape2 = analyzeText("Uzum sotiladi, qo'ng'iroq qiling 90 123 45 67", db);
      expect(codes(grape2.findings), isNot(contains('text.phone_not_official')));
    });
    test('bazadagi firibgar raqam — kritik', () {
      final raw = jsonDecode(File('../registry/registry.json').readAsStringSync()) as Map<String, dynamic>;
      (raw['malicious'] as Map)['phones'] = ['+998 90 000 00 01'];
      final bad = RostorDb.fromPayload(jsonEncode(raw), 99);
      final r = analyzeText('Yutuq! Bonusni olish uchun 900000001 ga yozing', bad);
      expect(codes(r.findings), contains('text.phone_malicious'));
      expect(r.severity, Severity.critical);
    });
  });
}
