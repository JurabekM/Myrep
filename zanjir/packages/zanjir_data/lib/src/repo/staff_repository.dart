import 'package:drift/drift.dart';

import '../db/database.dart';
import 'audit_repository.dart';
import 'context.dart';
import 'settings_repository.dart';
import 'user_repository.dart';

/// Xodimlar va qurilmalar (oflayn, ADR-0017 8-band). Har bir o'zgarish — imzolangan audit hodisasi; payload'lar
/// qatorlardan qayta tiklanadi, shuning uchun boshqa telefon importda ularni tekshira oladi.
///
/// - `USER_SAVED` (entity = foydalanuvchi) — [userAuditPayload];
/// - `INVITE_CREATED` (entity = taklif ID) — [invitePayload]; taklif [inviteTtl] davomida amal qiladi;
/// - `DEVICE_REGISTERED` (entity = taklif ID) — yangi qurilmaning **birinchi** hodisasi, [devicePayload];
/// - `DEVICE_APPROVED` (entity = qurilma) — zaxiradan tiklangan qurilmani LEAD/ADMIN tasdiqlaydi, [devicePayload];
/// - `DEVICE_REVOKED` (entity = `<qurilma>#<last_seq>`) — shu `seq` dan keyingi hodisalar qabul qilinmaydi.
class StaffRepository {
  StaffRepository(this._ctx, {required this._audit});
  final DataContext _ctx;
  final AuditRepository _audit;
  ZanjirDatabase get _db => _ctx.db;

  static const inviteTtl = Duration(days: 7);
  static const roles = ['ADMIN', 'LEAD', 'ENGINEER', 'VIEWER'];

  /// Yangi xodim — faqat LEAD/ADMIN.
  Future<AppUserRow> addUser({
    required String fullName,
    required String role,
    String phone = '',
    String? safetyGroup,
  }) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
    if (!roles.contains(role)) throw DataRuleException('invalid_role', role);
    final user = await UserRepository(_ctx)
        .create(fullName: fullName.trim(), phone: phone, role: role, safetyGroup: safetyGroup);
    await _audit.append(eventType: 'USER_SAVED', entityId: user.id, payload: userAuditPayload(user));
    return user;
  });

  /// Rol yoki ism o'zgarishi, o'chirish (`deleted`) — faqat LEAD/ADMIN. O'zini o'chirib bo'lmaydi.
  Future<AppUserRow> updateUser(String id, {String? fullName, String? role, bool? deleted}) =>
      _db.transaction(() async {
        await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
        if (role != null && !roles.contains(role)) throw DataRuleException('invalid_role', role);
        if (id == _audit.actorId && (deleted ?? false)) throw const DataRuleException('cannot_delete_self');
        final old = await UserRepository(_ctx).require(id);
        final row = old.copyWith(
          fullName: fullName?.trim() ?? old.fullName,
          role: role ?? old.role,
          deleted: deleted ?? old.deleted,
          updatedAt: _ctx.now(),
          rev: old.rev + 1,
        );
        await _db.update(_db.appUsers).replace(row);
        await _audit.append(eventType: 'USER_SAVED', entityId: id, payload: userAuditPayload(row));
        return row;
      });

  /// Taklif — faqat LEAD/ADMIN; bir taklif bilan bitta qurilma qo'shiladi.
  Future<String> createInvite(String userId) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
    final user = await UserRepository(_ctx).require(userId);
    final inviteId = _ctx.newId();
    await _audit.append(eventType: 'INVITE_CREATED', entityId: inviteId, payload: invitePayload(inviteId, user.id));
    return inviteId;
  });

  /// Zaxiradan tiklangan (yoki boshqa sabab bilan noma'lum) qurilmani tasdiqlash — faqat LEAD/ADMIN.
  Future<void> approveDevice(String deviceId) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
    final d = await DeviceRepository(_ctx).get(deviceId) ?? (throw NotFoundException('device', deviceId));
    await _audit.append(eventType: 'DEVICE_APPROVED', entityId: d.id, payload: devicePayload(d));
  });

  /// Qurilmani bekor qilish (yo'qolgan/o'g'irlangan telefon) — LEAD/ADMIN (oflaynda ADMIN bo'lmasligi mumkin, F-25).
  /// Shu paytgacha ma'lum bo'lgan oxirgi `seq` qayd etiladi — undan keyingi hodisalar hech bir telefonda qabul qilinmaydi.
  Future<void> revokeDevice(String deviceId) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
    if (deviceId == _audit.deviceId) throw const DataRuleException('cannot_revoke_self');
    final d = await DeviceRepository(_ctx).get(deviceId) ?? (throw NotFoundException('device', deviceId));
    final last = await lastSeq(_ctx, d.id);
    await _audit.append(eventType: 'DEVICE_REVOKED', entityId: '${d.id}#$last', payload: revokePayload(d.id, last));
    await applyRevocations(_ctx);
  });

  /// Tashkilot xodimlari (o'chirilganlarsiz), ism bo'yicha.
  Future<List<AppUserRow>> users() =>
      (_db.select(_db.appUsers)
            ..where((u) => u.orgId.equals(_ctx.orgId) & u.deleted.equals(false))
            ..orderBy([(u) => OrderingTerm(expression: u.fullName)]))
          .get();

  Future<List<DeviceRow>> devices() =>
      (_db.select(_db.devices)
            ..where((d) => d.orgId.equals(_ctx.orgId) & d.deleted.equals(false))
            ..orderBy([(d) => OrderingTerm(expression: d.registeredAt)]))
          .get();
}

Map<String, Object?> userAuditPayload(AppUserRow u) => {
  'id': u.id,
  'full_name': u.fullName,
  'role': u.role,
  'safety_group': u.safetyGroup,
  'deleted': u.deleted,
};

Map<String, Object?> invitePayload(String inviteId, String userId) => {'invite_id': inviteId, 'user_id': userId};

Map<String, Object?> devicePayload(DeviceRow d) => {
  'device_id': d.id,
  'user_id': d.userId,
  'public_key_ed25519': d.publicKeyEd25519,
  'sig_alg': d.sigAlg,
};

Map<String, Object?> revokePayload(String deviceId, int lastSeq) => {'device_id': deviceId, 'last_seq': lastSeq};

/// Qurilmaning oxirgi audit `seq` i (hodisa bo'lmasa 0).
Future<int> lastSeq(DataContext ctx, String deviceId) async {
  final r = await ctx.db
      .customSelect(
        'SELECT coalesce(max(seq), 0) AS s FROM audit_event WHERE org_id = ? AND device_id = ?',
        variables: [Variable(ctx.orgId), Variable(deviceId)],
      )
      .getSingle();
  return r.read<int>('s');
}

/// `DEVICE_REVOKED` hodisalari (LEAD/ADMIN dan) bo'yicha qurilmalarning `revoked_at` i va chegarasi.
/// Qurilma ID → (bekor qilingan vaqt, oxirgi ruxsat etilgan `seq`) — bir nechta bo'lsa eng kichik `seq`.
Future<Map<String, ({DateTime at, int lastSeq})>> revocations(DataContext ctx) async {
  final rows = await ctx.db
      .customSelect(
        'SELECT e.entity_id AS entity, e.event_at AS at, u.role AS role FROM audit_event e '
        "JOIN app_user u ON u.id = e.actor_id WHERE e.org_id = ? AND e.event_type = 'DEVICE_REVOKED'",
        variables: [Variable(ctx.orgId)],
      )
      .get();
  final out = <String, ({DateTime at, int lastSeq})>{};
  for (final r in rows) {
    if (!SettingsRepository.editorRoles.contains(r.read<String>('role'))) continue;
    final entity = r.read<String?>('entity') ?? '';
    final i = entity.lastIndexOf('#');
    final seq = i < 0 ? null : int.tryParse(entity.substring(i + 1));
    if (seq == null) continue;
    final id = entity.substring(0, i);
    final at = DateTime.parse(r.read<String>('at'));
    final prev = out[id];
    if (prev == null || seq < prev.lastSeq)
      out[id] = (at: prev == null || at.isBefore(prev.at) ? at : prev.at, lastSeq: seq);
  }
  return out;
}

/// `revoked_at` ni audit hodisalaridan tiklaydi (qurilma qatoridagi qiymatga ishonilmaydi).
Future<void> applyRevocations(DataContext ctx) async {
  for (final MapEntry(key: id, value: r) in (await revocations(ctx)).entries) {
    await ctx.db.customStatement(
      'UPDATE device SET revoked_at = ?, updated_at = ?, rev = rev + 1 WHERE org_id = ? AND id = ? AND revoked_at IS NULL',
      [r.at.toIso8601String(), ctx.now().toIso8601String(), ctx.orgId, id],
    );
  }
}
