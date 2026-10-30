import 'dart:convert';

import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import '../repo/audit_repository.dart';
import '../repo/context.dart';
import '../repo/settings_repository.dart';
import '../repo/staff_repository.dart';
import '../repo/user_repository.dart';
import 'exchange_file.dart';
import 'importer.dart';

/// Taklif fayli orqali laboratoriyaga qo'shilish (yangi, bo'sh telefon). Fayl parol bilan ochiladi, surat to'liq
/// tekshiriladi ([importExchange], `trustAll`), so'ng telefon taklif qilingan xodim nomidan qurilma sifatida ro'yxatdan
/// o'tadi: birinchi audit hodisasi — `DEVICE_REGISTERED` (taklif ID si bilan). Hammasi bitta tranzaksiyada.
///
/// Xatolar: `invite_wrong_password`, `exchange_invalid`, `restore_target_not_empty`, `invite_invalid`, `invite_used`,
/// `invite_expired` va import xatolari.
Future<({String orgId, String userId, String deviceId})> joinWithInvite(
  ZanjirDatabase db,
  List<int> bytes, {
  required String password,
  required Signer signer,
  required DateTime Function() clock,
}) async {
  final body = await openExchangeFile(bytes, password: password);
  final invite = body.invite ?? (throw const DataRuleException('invite_invalid'));
  final orgs = await db.customSelect('SELECT count(*) AS n FROM organization').getSingle();
  if (orgs.read<int>('n') != 0) throw const DataRuleException('restore_target_not_empty');
  final orgId = body.header.orgId;
  final ctx = DataContext(db: db, orgId: orgId, clock: clock);
  return db.transaction(() async {
    await importExchange(db, body, orgId: orgId, clock: clock, trustAll: true);
    final audit = AuditRepository(ctx, signer: signer, deviceId: '', actorId: invite.userId);
    final created = await audit.forEntity(invite.inviteId, eventType: 'INVITE_CREATED');
    final event = created
        .where((e) => e.payloadHash == payloadHash(invitePayload(invite.inviteId, invite.userId)))
        .firstOrNull;
    final issuer = event == null ? null : await UserRepository(ctx).get(event.actorId);
    if (event == null || issuer == null || !SettingsRepository.editorRoles.contains(issuer.role)) {
      throw const DataRuleException('invite_invalid');
    }
    if ((await audit.forEntity(invite.inviteId, eventType: 'DEVICE_REGISTERED')).isNotEmpty) {
      throw const DataRuleException('invite_used');
    }
    if (ctx.now().difference(DateTime.parse(event.eventAt)) > StaffRepository.inviteTtl) {
      throw const DataRuleException('invite_expired');
    }
    final user = await UserRepository(ctx).require(invite.userId);
    final device = await DeviceRepository(ctx)
        .register(userId: user.id, publicKeyHex: signer.publicKeyHex, sigAlg: signer.sigAlg);
    await AuditRepository(
      ctx,
      signer: signer,
      deviceId: device.id,
      actorId: user.id,
    ).append(eventType: 'DEVICE_REGISTERED', entityId: invite.inviteId, payload: devicePayload(device));
    final prefs = LocalPrefRepository(db);
    await prefs.set(LocalPrefRepository.orgId, orgId);
    await prefs.set(LocalPrefRepository.userId, user.id);
    await prefs.set(LocalPrefRepository.deviceId, device.id);
    await prefs.set(labKeyPref, base64Encode(invite.labKey));
    return (orgId: orgId, userId: user.id, deviceId: device.id);
  });
}
