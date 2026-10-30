import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import '../repo/context.dart';
import '../repo/measurement_repository.dart';
import '../repo/settings_repository.dart';
import '../repo/staff_repository.dart';
import 'importer.dart';

/// Faqat LEAD/ADMIN yoza oladigan audit hodisalari (serverdagi `EDITOR_EVENTS` + oflayn xodim hodisalari).
const editorEvents = {
  'PROTOCOL_REVOKED',
  'SETTINGS_CHANGED',
  'LAB_UPDATED',
  'PLAN_APPROVED',
  'USER_SAVED',
  'INVITE_CREATED',
  'DEVICE_APPROVED',
  'DEVICE_REVOKED',
};

const _planFinal = {'EXECUTED', 'CANCELLED', 'STALE'};
const _planTransitions = {
  'DRAFT': {'DRAFT', 'APPROVED', 'EXECUTED', 'CANCELLED', 'STALE'},
  'APPROVED': {'APPROVED', 'EXECUTED', 'CANCELLED', 'STALE'},
};
const _planFrozen = [
  'site_id',
  'target_node_ids',
  'solver_version',
  'graph_snapshot_hash',
  'steps',
  'warnings',
  'deleted',
];

/// LWW qatorini qo'llashdan oldingi qaror.
enum MutableDecision {
  /// Oddiy LWW.
  lww,

  /// Vaqtidan qat'i nazar qo'llanadi (rejaning yakuniy holati — barcha telefonlar shunga keladi).
  force,

  /// Qo'llanmaydi (yakuniy holatdan chiqib bo'lmaydi).
  skip,
}

/// O'zgarmas maydonlar va holat o'tishlari (serverdagi `_check_mutable`).
MutableDecision checkMutable(String table, Map<String, Object?> old, Map<String, Object?> row) {
  switch (table) {
    case 'measurement_session':
      if (old['closed_at'] != null && row['closed_at'] == null) {
        throw DataRuleException('session_reopen', '${row['id']}');
      }
    case 'isolation_plan':
      for (final k in _planFrozen) {
        if (canonicalJson(old[k]) != canonicalJson(row[k])) throw DataRuleException('plan_immutable', '${row['id']}');
      }
      if (old['approved_by'] != null && old['approved_by'] != row['approved_by']) {
        throw DataRuleException('plan_immutable', '${row['id']}');
      }
      final from = old['status']! as String, to = row['status']! as String;
      if (from == to) return MutableDecision.lww;
      if (_planFinal.contains(from)) return MutableDecision.skip;
      if (!(_planTransitions[from]?.contains(to) ?? false)) throw DataRuleException('plan_immutable', '${row['id']}');
      if (_planFinal.contains(to)) return MutableDecision.force;
  }
  return MutableDecision.lww;
}

/// Birlashtirilgan bazani tekshiradi (importdan keyin, o'sha tranzaksiyada). Tekshiruvlar faqat import qilingan
/// (yangi yoki o'zgargan) qatorlarga — mahalliy yozuvlar o'z repozitoriylarida tekshirilgan.
Future<void> checkMerged(
  DataContext ctx,
  MergeChanges ch, {
  required bool trustAll,
  required String senderDeviceId,
  Set<String> approveDevices = const {},
  Future<void> Function(String deviceId)? approver,
}) async {
  final r = _Rules(ctx, ch, trustAll: trustAll);
  await r.load();
  if (!r.devices.containsKey(senderDeviceId)) throw DataRuleException('unknown_device', senderDeviceId);
  if (!trustAll) {
    final pending = ch.inserted['device'] ?? const <String>{};
    for (final id in pending.intersection(approveDevices)) {
      await approver!(id);
    }
    if (pending.intersection(approveDevices).isNotEmpty) await r.load();
    for (final id in pending) {
      await r.authorizeDevice(id);
    }
  }
  await r.chains();
  await r.newEvents();
  if (!trustAll) {
    await r.users();
    await r.organization();
    await r.orgSettings();
  }
  await r.measurements();
  await r.normSets();
}

class _Rules {
  _Rules(this.ctx, this.ch, {required this.trustAll});
  final DataContext ctx;
  final MergeChanges ch;
  final bool trustAll;
  ZanjirDatabase get db => ctx.db;

  late Map<String, DeviceRow> devices;
  late Map<String, AppUserRow> users_;

  Future<void> load() async {
    devices = {for (final d in await (db.select(db.devices)..where((d) => d.orgId.equals(ctx.orgId))).get()) d.id: d};
    users_ = {for (final u in await (db.select(db.appUsers)..where((u) => u.orgId.equals(ctx.orgId))).get()) u.id: u};
  }

  bool _editor(String userId) => SettingsRepository.editorRoles.contains(users_[userId]?.role);

  Future<List<AuditEventRow>> _events({String? deviceId, String? type, String? entityId}) =>
      (db.select(db.auditEvents)
            ..where(
              (e) =>
                  e.orgId.equals(ctx.orgId) &
                  (deviceId == null ? const Constant(true) : e.deviceId.equals(deviceId)) &
                  (type == null ? const Constant(true) : e.eventType.equals(type)) &
                  (entityId == null ? const Constant(true) : e.entityId.equals(entityId)),
            )
            ..orderBy([(e) => OrderingTerm(expression: e.seq)]))
          .get();

  /// Shu turdagi, shu obyektga, shu payload bilan hodisa bormi (ixtiyoriy: faqat LEAD/ADMIN dan).
  Future<AuditEventRow?> _event(String type, String entityId, Object? payload, {bool editor = false}) async {
    final hash = payloadHash(payload);
    for (final e in await _events(type: type, entityId: entityId)) {
      if (e.payloadHash == hash && (!editor || _editor(e.actorId))) return e;
    }
    return null;
  }

  /// Yangi qurilma: taklif bilan ro'yxatdan o'tgan yoki LEAD/ADMIN tasdiqlagan bo'lishi shart.
  Future<void> authorizeDevice(String id) async {
    final d = devices[id]!;
    if (users_[d.userId] == null) throw DataRuleException('unknown_user', d.userId);
    final first = (await _events(deviceId: id)).firstOrNull;
    if (first != null && first.seq == 1 && first.eventType == 'DEVICE_REGISTERED' && first.entityId != null) {
      final inviteId = first.entityId!;
      final invite = await _event('INVITE_CREATED', inviteId, invitePayload(inviteId, d.userId), editor: true);
      final used = await _events(type: 'DEVICE_REGISTERED', entityId: inviteId);
      if (invite != null &&
          invite.deviceId != id &&
          first.payloadHash == payloadHash(devicePayload(d)) &&
          used.length == 1) {
        final age = DateTime.parse(first.eventAt).difference(DateTime.parse(invite.eventAt));
        if (age >= const Duration(minutes: -10) && age <= StaffRepository.inviteTtl) return;
        throw DataRuleException('invite_expired', id);
      }
    }
    final approved = await _event('DEVICE_APPROVED', id, devicePayload(d), editor: true);
    if (approved != null && approved.deviceId != id) return;
    throw DataRuleException('device_not_approved', id);
  }

  /// Yangi hodisasi bor qurilmalar zanjiri — butunligicha, o'z kaliti bilan.
  Future<void> chains() async {
    for (final id in trustAll ? devices.keys : ch.newEvents.keys) {
      final d = devices[id] ?? (throw DataRuleException('unknown_device', id));
      final events = await _events(deviceId: id);
      final v = await verifyChain([
        for (final e in events)
          AuditEvent(
            deviceId: e.deviceId,
            seq: e.seq,
            prevHash: e.prevHash,
            eventHash: e.eventHash,
            actorId: e.actorId,
            eventType: e.eventType,
            entityId: e.entityId,
            payloadHash: e.payloadHash,
            createdAt: e.eventAt,
            deviceSig: e.deviceSig,
            sigAlg: e.sigAlg,
          ),
      ], publicKeyHex: d.publicKeyEd25519);
      if (!v.ok) throw DataRuleException('audit_chain:${v.reason}', id);
    }
  }

  /// Yangi hodisalar: aktor — qurilma egasi, muharrir hodisalari — LEAD/ADMIN, bekor qilingan qurilmadan keyingilari yo'q.
  Future<void> newEvents() async {
    final revoked = await revocations(ctx);
    for (final MapEntry(key: deviceId, value: seqs) in ch.newEvents.entries) {
      final d = devices[deviceId]!;
      for (final e in await _events(deviceId: deviceId)) {
        if (!seqs.contains(e.seq)) continue;
        if (e.actorId != d.userId) throw DataRuleException('actor_mismatch', '$deviceId#${e.seq}');
        if (!trustAll && editorEvents.contains(e.eventType) && !_editor(e.actorId)) {
          throw DataRuleException('forbidden_role', '${e.eventType} $deviceId#${e.seq}');
        }
        final rv = revoked[deviceId];
        if (rv != null && e.seq > rv.lastSeq) throw DataRuleException('device_revoked', '$deviceId#${e.seq}');
        if (e.eventType == 'DEVICE_REVOKED') {
          final entity = e.entityId ?? '';
          final i = entity.lastIndexOf('#');
          final last = i < 0 ? null : int.tryParse(entity.substring(i + 1));
          if (last == null || e.payloadHash != payloadHash(revokePayload(entity.substring(0, i), last))) {
            throw DataRuleException('invalid_payload', '$deviceId#${e.seq}');
          }
        }
      }
    }
  }

  /// Yangi yoki o'zgargan foydalanuvchi — aynan shu mazmunli `USER_SAVED` (LEAD/ADMIN).
  Future<void> users() async {
    for (final id in ch.touched('app_user')) {
      final u = users_[id]!;
      if (await _event('USER_SAVED', id, userAuditPayload(u), editor: true) == null) {
        throw DataRuleException('missing_audit_event', 'app_user:$id');
      }
    }
  }

  Future<void> organization() async {
    if (ch.touched('organization').isEmpty) return;
    final o = await (db.select(db.organizations)..where((o) => o.id.equals(ctx.orgId))).getSingle();
    final payload = {'name': o.name, 'license_no': o.licenseNo, 'license_valid_until': o.licenseValidUntil};
    if (await _event('LAB_UPDATED', o.id, payload, editor: true) == null) {
      throw const DataRuleException('missing_audit_event', 'organization');
    }
  }

  Future<void> orgSettings() async {
    if (ch.touched('org_setting').isEmpty) return;
    final s = await (db.select(db.orgSettings)..where((s) => s.orgId.equals(ctx.orgId))).getSingle();
    final payload = {'k_corr': s.kCorr, 'margin_pct': s.marginPct, 'active_norm_set_version': s.activeNormSetVersion};
    if (await _event('SETTINGS_CHANGED', ctx.orgId, payload, editor: true) == null) {
      throw const DataRuleException('missing_audit_event', 'org_setting');
    }
  }

  /// Yangi o'lchov — `MEASUREMENT_ADDED` (aynan shu mazmun bilan).
  Future<void> measurements() async {
    final ids = ch.inserted['measurement'] ?? const <String>{};
    if (ids.isEmpty) return;
    final rows = await (db.select(db.measurements)..where((m) => m.id.isIn(ids))).get();
    for (final m in rows) {
      if (await _event('MEASUREMENT_ADDED', m.id, measurementAuditPayload(m)) == null) {
        throw DataRuleException('missing_audit_event', 'measurement:${m.id}');
      }
    }
  }

  /// Yangi normalar to'plami: hash, versiya va tekshiruvchi YAML bilan mos.
  Future<void> normSets() async {
    final ids = ch.inserted['norm_set'] ?? const <String>{};
    if (ids.isEmpty) return;
    for (final n in await (db.select(db.normSets)..where((n) => n.id.isIn(ids))).get()) {
      if (sha256Hex(utf8.encode(n.yaml)) != n.sha256) throw DataRuleException('norm_set_hash_mismatch', n.version);
      final NormSet set;
      try {
        set = NormSet.fromYaml(n.yaml);
      } on Object {
        throw DataRuleException('norm_set_invalid', n.version);
      }
      if (set.version != n.version) throw DataRuleException('norm_set_invalid', n.version);
      String? blank(String s) => s.trim().isEmpty ? null : s;
      if (blank(set.reviewedBy) != n.reviewedBy || blank(set.reviewedAt) != n.reviewedAt) {
        throw DataRuleException('norm_set_review_mismatch', n.version);
      }
    }
  }
}
