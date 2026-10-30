import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:drift/native.dart';
import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

/// Testlarda tez KDF (ishlab chiqarishda — [KdfParams.standard]).
const fastKdf = KdfParams(memoryKib: 8 * 1024, iterations: 1, parallelism: 1);
const password = 'zaxira-paroli-123';

class _NewerDb extends ZanjirDatabase {
  _NewerDb() : super(NativeDatabase.memory());
  @override
  int get schemaVersion => super.schemaVersion + 1;
}

Future<Map<String, int>> counts(ZanjirDatabase db) async => {
  for (final t in db.allTables)
    t.actualTableName: (await db.customSelect('SELECT count(*) AS n FROM "${t.actualTableName}"').getSingle())
        .read<int>('n'),
};

void main() {
  late ZanjirDatabase db;
  late Org org;
  late SignableSession s;

  setUp(() async {
    db = memoryDb();
    org = await Org.create(db, 'A');
    s = await SignableSession.create(org);
    final prefs = LocalPrefRepository(db);
    await prefs.set(LocalPrefRepository.orgId, org.ctx.orgId);
    await prefs.set(LocalPrefRepository.userId, org.user.id);
    await prefs.set(LocalPrefRepository.deviceId, org.device.id);
  });
  tearDown(() => db.close());

  Future<Uint8List> backup({String pw = password}) =>
      createBackup(db, password: pw, now: DateTime.utc(2026, 10, 30, 9), kdf: fastKdf, random: Random(1));

  test('yangi telefonga tiklash: hamma ma\'lumot, yangi qurilma, audit zanjirlari butun', () async {
    final bytes = await backup();
    final header = readBackupHeader(bytes);
    expect((header.createdAt, header.schemaVersion), (DateTime.utc(2026, 10, 30, 9), db.schemaVersion));
    // Sarlavhada shaxsiy ma'lumot yo'q, mazmun shifrlangan.
    expect(utf8.decode(bytes, allowMalformed: true), isNot(contains('Muhandis A')));
    expect(utf8.decode(bytes, allowMalformed: true), isNot(contains('XS1')));

    final target = memoryDb();
    addTearDown(target.close);
    final signer = await Ed25519Signer.fromSeed(List.filled(32, 9));
    final ids = await restoreBackup(target, bytes, password: password, signer: signer, clock: steppingClock());
    expect((ids.orgId, ids.userId), (org.ctx.orgId, org.user.id));
    expect(ids.deviceId, isNot(org.device.id));

    final before = await counts(db), after = await counts(target);
    for (final t in before.keys) {
      final extra = switch (t) {
        'device' || 'audit_event' => 1, // yangi qurilma va BACKUP_RESTORED
        _ => 0,
      };
      expect(after[t], before[t]! + extra, reason: t);
    }
    expect(await LocalPrefRepository(target).get(LocalPrefRepository.deviceId), ids.deviceId);
    final chains = await verifyOrgChains(DataContext(db: target, orgId: ids.orgId));
    expect(chains.values.every((c) => c.ok), isTrue);
    expect(chains.keys, containsAll([org.device.id, ids.deviceId]));

    // Tiklangan telefonda ish davom etadi: o'lchov qiymatlari, imzo, append-only.
    final ctx = DataContext(db: target, orgId: ids.orgId, clock: steppingClock(DateTime.utc(2026, 10, 30, 10)));
    final repos = Repositories(ctx, signer: signer, deviceId: ids.deviceId, actorId: ids.userId);
    final m = await repos.measurements.get(s.measurement.id);
    expect(m!.values, s.measurement.values);
    expect(m.verdict, s.measurement.verdict);
    final restored = await repos.audit.forEntity(ids.deviceId, eventType: 'BACKUP_RESTORED');
    expect(restored, hasLength(1));
    expect(
      restored.single.payloadHash,
      payloadHash({
        'backup_created_at': '2026-10-30T09:00:00.000Z',
        'backup_sha256': sha256Hex(bytes),
        'previous_device_id': org.device.id,
      }),
    );
    await repos.sites.create(name: 'Tiklangandan keyin');
    await expectLater(target.customUpdate('DELETE FROM measurement'), throwsA(isA<SqliteException>()));
  });

  test('noto\'g\'ri parol, o\'zgartirilgan bayt, begona fayl — ochilmaydi', () async {
    final bytes = await backup();
    final target = memoryDb();
    addTearDown(target.close);
    final signer = await Ed25519Signer.fromSeed(List.filled(32, 9));
    Future<void> rejects(List<int> b, String code, {String pw = password}) => expectLater(
      restoreBackup(target, b, password: pw, signer: signer, clock: steppingClock()),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', code)),
    );
    await rejects(bytes, 'backup_wrong_password', pw: 'boshqa-parol-123');
    final headerEnd = 9 + ByteData.sublistView(bytes, 5, 9).getUint32(0);
    // Shifrmatn, MAC va sarlavhaning (AEAD bilan himoyalangan) har bir qismi.
    for (final i in [headerEnd, headerEnd + 100, bytes.length - 1, bytes.length - 17]) {
      await rejects(Uint8List.fromList(bytes)..[i] ^= 1, 'backup_wrong_password');
    }
    final createdAt = utf8.encode('2026-10-30T09');
    final at = _indexOf(bytes, createdAt);
    await rejects(Uint8List.fromList(bytes)..[at + 3] = 0x37, 'backup_wrong_password'); // 2026 → 2027
    await rejects(Uint8List.fromList(bytes)..[0] = 0x00, 'backup_invalid');
    await rejects(utf8.encode('%PDF-1.7 bu zaxira emas'), 'backup_invalid');
    expect((await counts(target)).values, everyElement(0), reason: 'muvaffaqiyatsiz tiklash hech narsa yozmaydi');
  });

  test('bo\'sh bo\'lmagan telefonga tiklanmaydi; yangiroq versiya fayli rad', () async {
    final bytes = await backup();
    final signer = await Ed25519Signer.fromSeed(List.filled(32, 9));
    await expectLater(
      restoreBackup(db, bytes, password: password, signer: signer, clock: steppingClock()),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'restore_target_not_empty')),
    );
    final newer = _NewerDb();
    addTearDown(newer.close);
    final o = await Org.create(newer, 'N');
    await LocalPrefRepository(newer).set(LocalPrefRepository.orgId, o.ctx.orgId);
    final future = await createBackup(newer, password: password, now: DateTime.utc(2027), kdf: fastKdf);
    final target = memoryDb();
    addTearDown(target.close);
    await expectLater(
      restoreBackup(target, future, password: password, signer: signer, clock: steppingClock()),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'backup_newer_version')),
    );
  });

  test('zaxiradagi audit zanjiri buzilgan bo\'lsa — tiklanmaydi', () async {
    // Qurilmada (root) audit hodisasi o'zgartirilgan holat: trigger olib tashlanib, hash almashtirilgan.
    await db.customStatement('DROP TRIGGER audit_event_append_only_update');
    await db.customStatement("UPDATE audit_event SET payload_hash = 'ff' WHERE seq = 1");
    final bytes = await backup();
    final target = memoryDb();
    addTearDown(target.close);
    await expectLater(
      restoreBackup(
        target,
        bytes,
        password: password,
        signer: await Ed25519Signer.fromSeed(List.filled(32, 9)),
        clock: steppingClock(),
      ),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'backup_audit_broken')),
    );
  });

  test('parol kamida 10 belgi; zararli KDF parametrlari rad etiladi', () async {
    await expectLater(
      backup(pw: '123456789'),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'backup_password_too_short')),
    );
    for (final bad in [
      {'alg': 'argon2id', 'memory_kib': 4 * 1024 * 1024, 'iterations': 3, 'parallelism': 1},
      {'alg': 'argon2id', 'memory_kib': 65536, 'iterations': 1000, 'parallelism': 1},
      {'alg': 'pbkdf2', 'memory_kib': 65536, 'iterations': 3, 'parallelism': 1},
    ]) {
      expect(
        () => KdfParams.fromJson(bad),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'backup_invalid')),
      );
    }
    expect(KdfParams.fromJson(KdfParams.standard.toJson()).memoryKib, 64 * 1024);
  });
}

int _indexOf(List<int> hay, List<int> needle) {
  for (var i = 0; i + needle.length <= hay.length; i++) {
    var ok = true;
    for (var j = 0; j < needle.length && ok; j++) {
      ok = hay[i + j] == needle[j];
    }
    if (ok) return i;
  }
  throw StateError('topilmadi');
}
