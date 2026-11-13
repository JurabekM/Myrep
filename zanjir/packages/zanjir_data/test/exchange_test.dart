import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/exchange_support.dart';
import 'support/harness.dart';

void main() {
  late DateTime Function() clock;
  late Phone lead;
  late AppUserRow engineerUser;
  late Phone engineer;

  setUp(() async {
    clock = steppingClock();
    lead = await Phone.lead(clock);
    engineerUser = await lead.repos.staff.addUser(fullName: 'Muhandis', role: 'ENGINEER');
    final (bytes, password) = await lead.invite(engineerUser.id);
    engineer = await Phone.join(bytes, password, 2, clock);
  });

  /// Muhandis telefonida obyekt, sessiya va o'lchov.
  Future<MeasurementRow> measure(Phone p) async {
    final s = await SmallSite.createWith(p.repos);
    final session = await p.repos.sessions.start(
      siteId: s.site.id,
      kind: SessionKind.davriy,
      engineerId: p.userId,
      ambientTempC: 20,
    );
    return p.repos.measurements.record(
      sessionId: session.id,
      nodeId: s.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: s.instrument.id,
      values: const {'pair': 'L1-PE', 'zs_ohm': 0.5},
      enteredVia: EnteredVia.manual,
      normSetVersion: '0.3.0',
    );
  }

  group('taklif orqali qo\'shilish', () {
    test('yangi telefon laboratoriya suratini, kalitini va o\'z qurilmasini oladi', () async {
      expect(engineer.orgId, lead.orgId);
      expect(engineer.userId, engineerUser.id);
      expect(await labKey(engineer.db), await labKey(lead.db));
      final events = await engineer.repos.audit.events();
      expect(events.single.eventType, 'DEVICE_REGISTERED');
      final chains = await verifyOrgChains(engineer.ctx);
      expect(chains, hasLength(2));
      expect(chains.values.every((c) => c.ok), isTrue);
      expect((await engineer.repos.settings.current()).activeNormSetVersion, '0.3.0');
    });

    test('noto\'g\'ri parol; bo\'sh bo\'lmagan telefon; taklif ikkinchi qurilmaga ishlatilmaydi', () async {
      final user = await lead.repos.staff.addUser(fullName: 'Ikkinchi', role: 'ENGINEER');
      final (bytes, password) = await lead.invite(user.id);
      final signer = await Ed25519Signer.fromSeed(List.filled(32, 9));
      await expectLater(
        joinWithInvite(memoryDb(), bytes, password: 'NOTOGRI', signer: signer, clock: clock),
        rule('invite_wrong_password'),
      );
      await expectLater(
        joinWithInvite(lead.db, bytes, password: password, signer: signer, clock: clock),
        rule('restore_target_not_empty'),
      );
      // Bir taklif bilan ikki telefon: ikkinchisi LEAD telefonida qabul qilinmaydi.
      final first = await Phone.join(bytes, password, 3, clock);
      final second = await Phone.join(bytes, password, 4, clock);
      await lead.import(await first.export());
      await expectLater(lead.import(await second.export()), rule('device_not_approved'));
    });

    test('muddati o\'tgan taklif', () async {
      final user = await lead.repos.staff.addUser(fullName: 'Kech', role: 'ENGINEER');
      final (bytes, password) = await lead.invite(user.id);
      final signer = await Ed25519Signer.fromSeed(List.filled(32, 5));
      final later = steppingClock(clock().add(const Duration(days: 8)));
      await expectLater(
        joinWithInvite(memoryDb(), bytes, password: password, signer: signer, clock: later),
        rule('invite_expired'),
      );
    });
  });

  group('almashish', () {
    test('muhandis o\'lchovi LEAD telefoniga o\'tadi; qayta import hech narsa o\'zgartirmaydi', () async {
      final m = await measure(engineer);
      final file = await engineer.export();
      expect(readExchangeHeader(file).kind, ExchangeKind.data);
      final r = await lead.import(file);
      expect(r.inserted['measurement'], 1);
      expect(r.inserted['device'], 1);
      expect((await lead.repos.measurements.get(m.id))!.values, m.values);
      expect((await verifyOrgChains(lead.ctx)).values.every((c) => c.ok), isTrue);
      expect((await lead.import(file)).total, 0);
      // Qaytib: LEAD fayli muhandisda ham hech narsani buzmaydi.
      await engineer.import(await lead.export());
    });

    test('LWW: yangiroq tahrir ikkala telefonda ham yutadi', () async {
      final s = await SmallSite.createWith(engineer.repos);
      await lead.import(await engineer.export());
      await engineer.repos.sites.update((await engineer.repos.sites.get(s.site.id))!.copyWith(name: 'Eski nom'));
      await lead.repos.sites.update((await lead.repos.sites.get(s.site.id))!.copyWith(name: 'Yangi nom'));
      await lead.import(await engineer.export());
      await engineer.import(await lead.export());
      expect((await lead.repos.sites.get(s.site.id))!.name, 'Yangi nom');
      expect((await engineer.repos.sites.get(s.site.id))!.name, 'Yangi nom');
    });

    test('boshqa laboratoriya kaliti — ochilmaydi', () async {
      final other = await Phone.lead(clock);
      final body = await openExchangeFile(await other.export(), labKey: await labKey(other.db));
      expect(body.header.orgId, other.orgId);
      await expectLater(
        openExchangeFile(await other.export(), labKey: await labKey(lead.db)),
        rule('exchange_wrong_key'),
      );
    });
  });

  group('soxtalashtirish (insayder o\'z kaliti bilan qayta imzolaydi)', () {
    test('o\'lchov qiymati o\'zgartirildi — audit hodisasiga mos emas', () async {
      await measure(engineer);
      final file = await tamper(engineer, await engineer.export(), (b) {
        rows(b, 'measurement').single['values'] = {'pair': 'L1-PE', 'zs_ohm': 0.1};
      });
      await expectLater(lead.import(file), rule('missing_audit_event'));
      expect(await lead.count('measurement'), 0, reason: 'hammasi yoki hech narsa');
    });

    test('LEAD da bor o\'lchovni o\'zgartirish — append_only_conflict', () async {
      await measure(engineer);
      await lead.import(await engineer.export());
      final file = await tamper(engineer, await engineer.export(), (b) {
        rows(b, 'measurement').single['verdict'] = 'FAIL';
      });
      await expectLater(lead.import(file), rule('append_only_conflict'));
    });

    test('audit hodisasi o\'zgartirildi — zanjir buziladi', () async {
      await measure(engineer);
      final file = await tamper(engineer, await engineer.export(), (b) {
        final e = rows(b, 'audit_event').lastWhere((e) => e['device_id'] == engineer.deviceId);
        e['payload_hash'] = '0' * 64;
      });
      await expectLater(lead.import(file), rule('audit_chain:event_hash_mismatch'));
    });

    test('muhandis laboratoriya nomini o\'zgartiradi — LAB_UPDATED yo\'q', () async {
      final file = await tamper(engineer, await engineer.export(), (b) {
        final o = rows(b, 'organization').single;
        o['name'] = 'Soxta lab';
        o['updated_at'] = isoUtcMillis(clock());
        o['rev'] = 99;
      });
      await expectLater(lead.import(file), rule('missing_audit_event'));
    });

    test('muhandis sozlamani o\'zgartirib, SETTINGS_CHANGED ni o\'zi imzolaydi — forbidden_role', () async {
      // Ilova bunga yo'l qo'ymaydi; to'g'ridan-to'g'ri audit yozuvi bilan.
      await engineer.repos.audit.append(
        eventType: 'SETTINGS_CHANGED',
        entityId: engineer.orgId,
        payload: {'k_corr': 0.5, 'margin_pct': 0.0, 'active_norm_set_version': '0.3.0'},
      );
      await expectLater(lead.import(await engineer.export()), rule('forbidden_role'));
    });

    test('muhandis LEAD nomidan yangi qurilma qo\'shadi — tasdiqlanmagan', () async {
      final fake = await Ed25519Signer.fromSeed(List.filled(32, 7));
      final file = await tamper(engineer, await engineer.export(), (b) {
        rows(b, 'device').add({
          ...rows(b, 'device').firstWhere((d) => d['id'] == lead.deviceId),
          'id': '01900000-0000-7000-8000-000000000999',
          'public_key_ed25519': fake.publicKeyHex,
        });
      });
      await expectLater(lead.import(file), rule('device_not_approved'));
    });

    test('muhandis o\'z rolini LEAD ga ko\'taradi — USER_SAVED yo\'q', () async {
      final file = await tamper(engineer, await engineer.export(), (b) {
        final u = rows(b, 'app_user').singleWhere((u) => u['id'] == engineer.userId);
        u['role'] = 'LEAD';
        u['updated_at'] = isoUtcMillis(clock());
        u['rev'] = 50;
      });
      await expectLater(lead.import(file), rule('missing_audit_event'));
      expect((await lead.repos.users.get(engineer.userId))!.role, 'ENGINEER');
    });

    test('LEAD rolini o\'zgartiradi — muhandis telefonida qabul qilinadi', () async {
      await lead.repos.staff.updateUser(engineer.userId, role: 'LEAD');
      await engineer.import(await lead.export());
      expect((await engineer.repos.users.get(engineer.userId))!.role, 'LEAD');
    });

    test('VIEWER obyekt/asbobni o\'zgartirgan fayl — forbidden_role', () async {
      final viewerUser = await lead.repos.staff.addUser(fullName: 'Kuzatuvchi', role: 'VIEWER');
      final (bytes, password) = await lead.invite(viewerUser.id);
      final viewer = await Phone.join(bytes, password, 8, clock);
      // O'zgarishsiz fayli (faqat qurilmasi va DEVICE_REGISTERED) — qabul qilinadi.
      expect((await lead.import(await viewer.export())).inserted['device'], 1);
      await viewer.repos.sites.create(name: 'Soxta obyekt');
      await expectLater(lead.import(await viewer.export()), rule('forbidden_role'));
    });

    test('yopilgan sessiyani qayta ochib bo\'lmaydi', () async {
      final m = await measure(engineer);
      await engineer.repos.sessions.close(m.sessionId);
      await lead.import(await engineer.export());
      final file = await tamper(engineer, await engineer.export(), (b) {
        final s = rows(b, 'measurement_session').single;
        s['closed_at'] = null;
        s['updated_at'] = isoUtcMillis(clock());
      });
      await expectLater(lead.import(file), rule('session_reopen'));
    });

    test('kelajak vaqti (soat siljishi > 10 daqiqa) — clock_skew', () async {
      final s = await SmallSite.createWith(engineer.repos);
      final file = await tamper(engineer, await engineer.export(), (b) {
        rows(b, 'site').singleWhere((r) => r['id'] == s.site.id)['updated_at'] = isoUtcMillis(
          clock().add(const Duration(hours: 1)),
        );
      });
      await expectLater(lead.import(file), rule('clock_skew'));
    });

    test('noma\'lum ustun va noto\'g\'ri tur rad etiladi', () async {
      final a = await tamper(engineer, await engineer.export(), (b) => rows(b, 'app_user').first['x'] = 1);
      await expectLater(lead.import(a), rule('exchange_invalid'));
      final b2 = await tamper(engineer, await engineer.export(), (b) => rows(b, 'app_user').first['rev'] = 'bir');
      await expectLater(lead.import(b2), rule('exchange_invalid'));
    });
  });

  group('qurilmani bekor qilish va tasdiqlash', () {
    test('bekor qilingan qurilmaning keyingi yozuvlari qabul qilinmaydi', () async {
      await lead.import(await engineer.export());
      await lead.repos.staff.revokeDevice(engineer.deviceId);
      expect((await lead.repos.devices.get(engineer.deviceId))!.revokedAt, isNotNull);
      await measure(engineer); // telefon hali bekor qilinganini bilmaydi
      await expectLater(lead.import(await engineer.export()), rule('device_revoked'));
      // Bekor qilish xabari muhandis telefoniga yetgach, u yozolmaydi.
      await engineer.import(await lead.export());
      expect((await engineer.repos.devices.get(engineer.deviceId))!.revokedAt, isNotNull);
      await expectLater(measure(engineer), rule('device_revoked'));
    });

    test('ENGINEER qurilmani bekor qila olmaydi; o\'zini bekor qilib bo\'lmaydi', () async {
      await expectLater(engineer.repos.staff.revokeDevice(lead.deviceId), rule('forbidden_role'));
      await expectLater(lead.repos.staff.revokeDevice(lead.deviceId), rule('cannot_revoke_self'));
    });

    test('zaxiradan tiklangan telefon — LEAD tasdiqlagach qabul qilinadi', () async {
      await measure(engineer);
      await LocalPrefRepository(engineer.db).set(LocalPrefRepository.orgId, engineer.orgId);
      await LocalPrefRepository(engineer.db).set(LocalPrefRepository.userId, engineer.userId);
      await LocalPrefRepository(engineer.db).set(LocalPrefRepository.deviceId, engineer.deviceId);
      final backup = await createBackup(engineer.db, password: 'zaxira-paroli-1', now: clock(), kdf: fastKdf);
      final restoredDb = memoryDb();
      final signer = await Ed25519Signer.fromSeed(List.filled(32, 6));
      final ids = await restoreBackup(restoredDb, backup, password: 'zaxira-paroli-1', signer: signer, clock: clock);
      final restored = Phone(restoredDb, ids.orgId, ids.userId, ids.deviceId, signer, clock);
      expect(await labKey(restoredDb), await labKey(engineer.db), reason: 'laboratoriya kaliti zaxirada');

      final file = await restored.export();
      await expectLater(lead.import(file), rule('device_not_approved'));
      await lead.import(file, approve: {restored.deviceId});
      expect(await lead.count('measurement'), 1);
      // Tasdiq boshqa telefonlarga ham o'tadi.
      await engineer.import(await lead.export());
      await engineer.import(file);
    });
  });
}
