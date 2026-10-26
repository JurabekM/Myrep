import 'package:drift/drift.dart';

import '../db/database.dart';
import 'audit_repository.dart';
import 'context.dart';
import 'session_repository.dart';
import 'user_repository.dart';

enum ProtocolStatus { active, revoked }

/// Protokollar — append-only. Bekor qilish faqat `PROTOCOL_REVOKED` audit hodisasi orqali (prompt 5.4).
/// Imzolash va bloklash shartlari — 6-faza.
class ProtocolRepository {
  ProtocolRepository(this._ctx, {required this._audit});
  final DataContext _ctx;
  final AuditRepository _audit;
  ZanjirDatabase get _db => _ctx.db;

  Future<ProtocolRow> insert({
    required String sessionId,
    required String number,
    required String payloadSha256,
    required String pdfSha256,
    required String signedBy,
    required String signature,
    required String sigAlg,
    required String qrToken,
  }) => _db.transaction(() async {
    await SessionRepository(_ctx).require(sessionId);
    await UserRepository(_ctx).require(signedBy);
    final now = _ctx.now();
    final row = await _db
        .into(_db.protocols)
        .insertReturning(
          ProtocolsCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            sessionId: sessionId,
            number: number,
            payloadSha256: payloadSha256,
            pdfSha256: pdfSha256,
            signedBy: signedBy,
            deviceId: _audit.deviceId,
            signature: signature,
            sigAlg: sigAlg,
            qrToken: qrToken,
            createdAt: now,
            updatedAt: now,
          ),
        );
    await _audit.append(
      eventType: 'PROTOCOL_SIGNED',
      entityId: row.id,
      payload: {
        'id': row.id,
        'session_id': sessionId,
        'number': number,
        'payload_sha256': payloadSha256,
        'pdf_sha256': pdfSha256,
        'signature': signature,
        'sig_alg': sigAlg,
        'qr_token': qrToken,
      },
    );
    return row;
  });

  Future<ProtocolRow?> get(String id) =>
      (_db.select(_db.protocols)..where((p) => p.id.equals(id) & p.orgId.equals(_ctx.orgId))).getSingleOrNull();

  Future<ProtocolStatus> status(String id) async {
    await get(id) ?? (throw NotFoundException('protocol', id));
    final revoked = await _audit.forEntity(id, eventType: 'PROTOCOL_REVOKED');
    return revoked.isEmpty ? ProtocolStatus.active : ProtocolStatus.revoked;
  }

  Future<void> revoke(String id, {required String reason}) => _db.transaction(() async {
    if (await status(id) == ProtocolStatus.revoked) throw DataRuleException('already_revoked', id);
    await _audit.append(eventType: 'PROTOCOL_REVOKED', entityId: id, payload: {'reason': reason});
  });
}
