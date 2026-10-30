import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'context.dart';

/// Qurilmaning audit hash-zanjiri (append-only, ADR-0007). Faqat qo'shish va o'qish.
class AuditRepository {
  AuditRepository(this._ctx, {required this._signer, required this.deviceId, required this.actorId});
  final DataContext _ctx;
  final Signer _signer;
  final String deviceId;
  final String actorId;
  ZanjirDatabase get _db => _ctx.db;

  /// Zanjirga keyingi hodisani qo'shadi. Qurilma bekor qilingan yoki kaliti mos kelmasa — yozilmaydi.
  Future<AuditEventRow> append({required String eventType, required String? entityId, required Object? payload}) =>
      _db.transaction(() async {
        final device = await _device();
        if (device.revokedAt != null) throw DataRuleException('device_revoked', deviceId);
        if (device.publicKeyEd25519 != _signer.publicKeyHex) throw DataRuleException('device_key_mismatch', deviceId);
        final last =
            await (_db.select(_db.auditEvents)
                  ..where((e) => e.deviceId.equals(deviceId) & e.orgId.equals(_ctx.orgId))
                  ..orderBy([(e) => OrderingTerm.desc(e.seq)])
                  ..limit(1))
                .getSingleOrNull();
        final now = _ctx.now();
        final e = await appendEvent(
          previous: last == null ? null : toCore(last),
          signer: _signer,
          deviceId: deviceId,
          actorId: actorId,
          eventType: eventType,
          entityId: entityId,
          payload: payload,
          createdAt: now,
        );
        return _db
            .into(_db.auditEvents)
            .insertReturning(
              AuditEventsCompanion.insert(
                id: _ctx.newId(),
                orgId: _ctx.orgId,
                deviceId: e.deviceId,
                seq: e.seq,
                prevHash: e.prevHash,
                eventHash: e.eventHash,
                actorId: e.actorId,
                eventType: e.eventType,
                entityId: Value(e.entityId),
                payloadHash: e.payloadHash,
                deviceSig: e.deviceSig,
                sigAlg: e.sigAlg,
                eventAt: e.createdAt,
                createdAt: now,
                updatedAt: now,
              ),
            );
      });

  /// Shu qurilma hodisalari, `seq` bo'yicha.
  Future<List<AuditEventRow>> events() =>
      (_db.select(_db.auditEvents)
            ..where((e) => e.deviceId.equals(deviceId) & e.orgId.equals(_ctx.orgId))
            ..orderBy([(e) => OrderingTerm(expression: e.seq)]))
          .get();

  /// Tashkilotdagi barcha qurilmalardan shu obyektga tegishli hodisalar.
  Future<List<AuditEventRow>> forEntity(String entityId, {String? eventType}) =>
      (_db.select(_db.auditEvents)..where(
            (e) =>
                e.entityId.equals(entityId) &
                e.orgId.equals(_ctx.orgId) &
                (eventType == null ? const Constant(true) : e.eventType.equals(eventType)),
          ))
          .get();

  /// Lokal zanjirni qurilmaning ro'yxatdagi ochiq kaliti bilan tekshiradi.
  Future<ChainVerification> verify() async {
    final device = await _device();
    return verifyChain([for (final e in await events()) toCore(e)], publicKeyHex: device.publicKeyEd25519);
  }

  AuditEvent toCore(AuditEventRow e) => AuditEvent(
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
  );

  Future<DeviceRow> _device() async =>
      await (_db.select(_db.devices)
            ..where((d) => d.id.equals(deviceId) & d.orgId.equals(_ctx.orgId) & d.deleted.equals(false)))
          .getSingleOrNull() ??
      (throw NotFoundException('device', deviceId));
}

/// Tashkilotdagi har bir qurilmaning audit zanjiri (o'z ochiq kaliti bilan) — zaxira tiklash va fayl importida.
/// Qurilma ID → natija; birinchi buzilgan zanjir `ok == false`.
Future<Map<String, ChainVerification>> verifyOrgChains(DataContext ctx) async {
  final db = ctx.db;
  final devices = await (db.select(db.devices)..where((d) => d.orgId.equals(ctx.orgId))).get();
  final out = <String, ChainVerification>{};
  for (final d in devices) {
    final events =
        await (db.select(db.auditEvents)
              ..where((e) => e.deviceId.equals(d.id) & e.orgId.equals(ctx.orgId))
              ..orderBy([(e) => OrderingTerm(expression: e.seq)]))
            .get();
    out[d.id] = await verifyChain([
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
  }
  return out;
}
