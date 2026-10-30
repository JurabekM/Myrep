// Ikki telefonli almashish testlari uchun umumiy yordamchilar.
import 'dart:convert';
import 'dart:typed_data';

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'harness.dart';

const fastKdf = KdfParams(memoryKib: 8 * 1024, iterations: 1, parallelism: 1);

/// Laboratoriyadagi bitta telefon. Barcha telefonlar bitta soatni bo'lishadi (haqiqiy vaqt kabi).
class Phone {
  Phone(this.db, this.orgId, this.userId, this.deviceId, this.signer, this.clock);
  final ZanjirDatabase db;
  final String orgId;
  final String userId;
  final String deviceId;
  final Ed25519Signer signer;
  final DateTime Function() clock;

  DataContext get ctx => DataContext(db: db, orgId: orgId, clock: clock);
  Repositories get repos => Repositories(ctx, signer: signer, deviceId: deviceId, actorId: userId);

  /// Laboratoriyani yaratgan LEAD telefoni (ilovadagi `ProfileService.create` kabi).
  static Future<Phone> lead(DateTime Function() clock) async {
    final db = memoryDb();
    final orgId = await OrganizationRepository(db, clock: clock).create(name: 'Elektrolab');
    final ctx = DataContext(db: db, orgId: orgId, clock: clock);
    final user = await UserRepository(ctx).create(fullName: 'Rahbar', phone: '', role: 'LEAD');
    final signer = await Ed25519Signer.fromSeed(List.filled(32, 1));
    final device = await DeviceRepository(ctx)
        .register(userId: user.id, publicKeyHex: signer.publicKeyHex, sigAlg: signer.sigAlg);
    final p = Phone(db, orgId, user.id, device.id, signer, clock);
    final norms = await p.repos.normSets.import(v0Yaml);
    await p.repos.settings.update(byUserId: user.id, activeNormSetVersion: norms.version);
    return p;
  }

  /// Taklif faylini yaratadi (LEAD/ADMIN telefonida).
  Future<(Uint8List, String)> invite(String userId) async {
    final inviteId = await repos.staff.createInvite(userId);
    const password = 'TAKLIF-PAROL';
    final bytes = await createInviteFile(
      ctx,
      signer: signer,
      deviceId: deviceId,
      inviteId: inviteId,
      userId: userId,
      password: password,
      kdf: fastKdf,
    );
    return (bytes, password);
  }

  static Future<Phone> join(Uint8List invite, String password, int seed, DateTime Function() clock) async {
    final db = memoryDb();
    final signer = await Ed25519Signer.fromSeed(List.filled(32, seed));
    final ids = await joinWithInvite(db, invite, password: password, signer: signer, clock: clock);
    return Phone(db, ids.orgId, ids.userId, ids.deviceId, signer, clock);
  }

  Future<Uint8List> export() => createExchangeFile(ctx, signer: signer, deviceId: deviceId);

  Future<ImportResult> import(Uint8List bytes, {Set<String> approve = const {}}) async {
    final body = await openExchangeFile(bytes, labKey: await labKey(db));
    return importExchange(
      db,
      body,
      orgId: orgId,
      clock: clock,
      approveDevices: approve,
      approver: repos.staff.approveDevice,
    );
  }

  Future<int> count(String table) async =>
      (await db.customSelect('SELECT count(*) AS n FROM "$table"').getSingle()).read<int>('n');
}

/// Insayder hujumi: fayl tanasini o'zgartirib, o'z qurilma kaliti bilan qayta imzolash (laboratoriya kaliti unda bor).
Future<Uint8List> tamper(Phone from, Uint8List file, void Function(Map<String, Object?> body) edit) async {
  final opened = await openExchangeFile(file, labKey: await labKey(from.db));
  final body = (jsonDecode(jsonEncode(opened.json)) as Map).cast<String, Object?>();
  edit(body);
  final lab = await labKey(from.db);
  return sealExchangeBody(
    body,
    signer: from.signer,
    kind: ExchangeKind.data,
    createdAt: from.clock(),
    schemaVersion: from.db.schemaVersion,
    key: (_) async => lab,
  );
}

List<Map<String, Object?>> rows(Map<String, Object?> body, String table) =>
    ((body['tables']! as Map)[table]! as List).cast<Map<String, Object?>>();

Matcher rule(String code) => throwsA(isA<DataRuleException>().having((e) => e.code, 'code', code));
