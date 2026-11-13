import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

import '../db/database.dart';
import 'audit_repository.dart';
import 'context.dart';
import 'instrument_repository.dart';
import 'measurement_repository.dart';
import 'norm_set_repository.dart';
import 'session_repository.dart';
import 'settings_repository.dart';
import 'site_repository.dart';
import 'user_repository.dart';

enum ProtocolStatus { active, revoked }

/// Imzolashni to'xtatuvchi shart. `code` — barqaror inglizcha kalit (UI l10n orqali ko'rsatadi),
/// `ids` — tegishli o'lchov, asbob yoki protokol ID lari.
class ProtocolBlocker {
  const ProtocolBlocker(this.code, [this.ids = const []]);
  final String code;
  final List<String> ids;

  @override
  bool operator ==(Object other) => other is ProtocolBlocker && other.code == code && _listEq(other.ids, ids);

  @override
  int get hashCode => Object.hash(code, Object.hashAll(ids));

  @override
  String toString() => ids.isEmpty ? code : '$code(${ids.join(', ')})';
}

bool _listEq(List<String> a, List<String> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

/// Imzolashga tayyorlangan protokol: payload (`zanjir.protocol/1`) va bloklovchi shartlar.
/// Bloklovchi shart bo'lsa ham payload quriladi — ko'rib chiqish (preview) uchun.
class ProtocolDraft {
  const ProtocolDraft({required this.sessionId, required this.payload, required this.blockers});
  final String sessionId;
  final Map<String, Object?> payload;
  final List<ProtocolBlocker> blockers;

  String get payloadSha256 => protocolPayloadSha256(payload);
  bool get canSign => blockers.isEmpty;
}

/// Imzolangan protokol va uning hujjati.
typedef SignedProtocol = ({ProtocolRow protocol, ProtocolDocumentRow document});

/// Protokollar — append-only (prompt 5.4). Imzolash faqat [prepare] → [sign] orqali, bloklash shartlari bilan
/// (CLAUDE.md, 6-qoida; ADR-0010). Bekor qilish — faqat `PROTOCOL_REVOKED` audit hodisasi.
class ProtocolRepository {
  ProtocolRepository(
    this._ctx, {
    required this._audit,
    required this._signer,
    required this._normSets,
    required this._measurements,
  });

  final DataContext _ctx;
  final AuditRepository _audit;
  final Signer _signer;
  final NormSetRepository _normSets;
  final MeasurementRepository _measurements;
  ZanjirDatabase get _db => _ctx.db;

  /// Imzolay oladigan rollar. ADMIN — tashkilot boshqaruvchisi, VIEWER — faqat ko'radi.
  static const signerRoles = {'LEAD', 'ENGINEER'};

  /// Tayyorlangan, lekin imzolanmagan qoralama shuncha vaqtdan keyin eskiradi (`signed_at` haqiqatga yaqin bo'lsin).
  static const draftTtl = Duration(minutes: 15);

  /// QR tekshiruv havolasining standart asosi (server domeni 2-darvozada belgilanadi).
  static const defaultVerifyBaseUrl = 'zanjir://app/v/';

  /// Joriy foydalanuvchi (audit `actorId`) va qurilma nomidan protokol qoralamasini tayyorlaydi.
  Future<ProtocolDraft> prepare({
    required String sessionId,
    String language = 'uz',
    String? leadComment,
    String verifyBaseUrl = defaultVerifyBaseUrl,
  }) => _db.transaction(() async {
    final now = _ctx.now();
    final number = await _nextNumber(now);
    // QR token — qurilma imzosidan (ADR-0014): oldindan bilinmaydi, server uni shu qurilma kaliti bilan tekshiradi.
    final qrSig = hexEncode(await _signer.sign(qrTokenMessage(_ctx.orgId, number)));
    final token = qrTokenFromSignature(qrSig);
    return _build(
      sessionId: sessionId,
      language: language,
      leadComment: leadComment,
      number: number,
      qrToken: token,
      qrSig: qrSig,
      verifyUrl: '$verifyBaseUrl$token',
      signedAt: now,
    );
  });

  /// Qoralamani imzolaydi: PDF render qilinadi, ma'lumotlar qayta tekshiriladi (qoralamadan keyin hech narsa
  /// o'zgarmagan bo'lishi kerak), `signature = Ed25519(payload_sha256 ‖ pdf_sha256)`, protokol + hujjat + audit —
  /// bitta tranzaksiyada. Bloklovchi shart bo'lsa — `protocol_blocked`, qoralama eskirgan bo'lsa — `draft_stale`.
  Future<SignedProtocol> sign(ProtocolDraft draft, ProtocolFonts fonts) async {
    if (!draft.canSign) throw DataRuleException('protocol_blocked', draft.blockers.join('; '));
    final pdf = await renderProtocolPdf(draft.payload, fonts);
    return _db.transaction(() async {
      final p = draft.payload;
      final protocol = (p['protocol']! as Map).cast<String, Object?>();
      final signedAt = DateTime.parse(p['signed_at']! as String);
      if (_ctx.now().difference(signedAt) > draftTtl) throw DataRuleException('draft_stale', 'expired');
      final fresh = await _build(
        sessionId: draft.sessionId,
        language: protocol['language']! as String,
        leadComment: p['lead_comment'] as String?,
        number: protocol['number']! as String,
        qrToken: protocol['qr_token']! as String,
        qrSig: protocol['qr_sig']! as String,
        verifyUrl: protocol['verify_url']! as String,
        signedAt: signedAt,
      );
      if (!fresh.canSign) throw DataRuleException('protocol_blocked', fresh.blockers.join('; '));
      if (canonicalJson(fresh.payload) != canonicalJson(p)) throw DataRuleException('draft_stale', 'changed');

      final sig = await signProtocol(payload: p, pdfBytes: pdf, signer: _signer);
      final now = _ctx.now();
      final row = await _db
          .into(_db.protocols)
          .insertReturning(
            ProtocolsCompanion.insert(
              id: _ctx.newId(),
              orgId: _ctx.orgId,
              sessionId: draft.sessionId,
              number: protocol['number']! as String,
              payloadSha256: sig.payloadSha256,
              pdfSha256: sig.pdfSha256,
              signedBy: _audit.actorId,
              deviceId: _audit.deviceId,
              signature: sig.signature,
              sigAlg: sig.sigAlg,
              qrToken: protocol['qr_token']! as String,
              createdAt: now,
              updatedAt: now,
            ),
          );
      final document = await _db
          .into(_db.protocolDocuments)
          .insertReturning(
            ProtocolDocumentsCompanion.insert(
              id: _ctx.newId(),
              orgId: _ctx.orgId,
              protocolId: row.id,
              payloadJson: canonicalJson(p),
              pdf: pdf,
              createdAt: now,
              updatedAt: now,
            ),
          );
      await _audit.append(eventType: 'PROTOCOL_SIGNED', entityId: row.id, payload: protocolAuditPayload(row));
      return (protocol: row, document: document);
    });
  }

  Future<ProtocolRow?> get(String id) =>
      (_db.select(_db.protocols)..where((p) => p.id.equals(id) & p.orgId.equals(_ctx.orgId))).getSingleOrNull();

  /// QR havolasidagi token bo'yicha (shu tashkilot ichida).
  Future<ProtocolRow?> byQrToken(String token) =>
      (_db.select(_db.protocols)..where((p) => p.qrToken.equals(token) & p.orgId.equals(_ctx.orgId))).getSingleOrNull();

  Future<ProtocolDocumentRow?> document(String protocolId) => (_db.select(
    _db.protocolDocuments,
  )..where((d) => d.protocolId.equals(protocolId) & d.orgId.equals(_ctx.orgId))).getSingleOrNull();

  /// Sessiya protokollari (eng yangisi birinchi), bekor qilinganlari ham.
  Future<List<ProtocolRow>> forSession(String sessionId) =>
      (_db.select(_db.protocols)
            ..where((p) => p.sessionId.equals(sessionId) & p.orgId.equals(_ctx.orgId))
            ..orderBy([(p) => OrderingTerm.desc(p.createdAt), (p) => OrderingTerm.desc(p.id)]))
          .get();

  Future<ProtocolStatus> status(String id) async {
    await get(id) ?? (throw NotFoundException('protocol', id));
    final revoked = await _audit.forEntity(id, eventType: 'PROTOCOL_REVOKED');
    return revoked.isEmpty ? ProtocolStatus.active : ProtocolStatus.revoked;
  }

  /// Saqlangan hujjat imzoga mosmi: payload hash, PDF hash, imzo (protokolni yaratgan qurilma kaliti bilan).
  /// `null` — hammasi to'g'ri; aks holda sabab kodi (`document_missing`, `pdf_id_mismatch`, `payload_hash_mismatch`, ...).
  Future<String?> verify(String id) async {
    final row = await get(id) ?? (throw NotFoundException('protocol', id));
    final doc = await document(id);
    if (doc == null) return 'document_missing';
    if (pdfDocumentId(doc.pdf) != row.payloadSha256) return 'pdf_id_mismatch';
    final device = await (_db.select(
      _db.devices,
    )..where((d) => d.id.equals(row.deviceId) & d.orgId.equals(_ctx.orgId))).getSingle();
    return verifyProtocol(
      payload: jsonDecode(doc.payloadJson),
      pdfBytes: doc.pdf,
      signature: ProtocolSignature(
        payloadSha256: row.payloadSha256,
        pdfSha256: row.pdfSha256,
        signature: row.signature,
        sigAlg: row.sigAlg,
      ),
      publicKeyHex: device.publicKeyEd25519,
    );
  }

  /// Bekor qilish — faqat LEAD/ADMIN, sabab bilan.
  Future<void> revoke(String id, {required String reason}) => _db.transaction(() async {
    await requireRole(_ctx, _audit.actorId, SettingsRepository.editorRoles);
    if (reason.trim().isEmpty) throw DataRuleException('reason_required', id);
    if (await status(id) == ProtocolStatus.revoked) throw DataRuleException('already_revoked', id);
    await _audit.append(eventType: 'PROTOCOL_REVOKED', entityId: id, payload: {'reason': reason});
  });

  /// `YYYY-XXXXXX-NNN`: yil, qurilma ID sining oxirgi 6 belgisi, shu qurilmaning shu yildagi tartib raqami.
  Future<String> _nextNumber(DateTime now) async {
    final dev = _audit.deviceId.replaceAll('-', '');
    final tag = (dev.length >= 6 ? dev.substring(dev.length - 6) : dev.padLeft(6, '0')).toUpperCase();
    final prefix = '${now.year}-$tag-';
    final existing = await (_db.select(
      _db.protocols,
    )..where((p) => p.orgId.equals(_ctx.orgId) & p.number.like('$prefix%'))).get();
    var max = 0;
    for (final p in existing) {
      final n = int.tryParse(p.number.substring(prefix.length)) ?? 0;
      if (n > max) max = n;
    }
    return '$prefix${(max + 1).toString().padLeft(3, '0')}';
  }

  Future<ProtocolDraft> _build({
    required String sessionId,
    required String language,
    required String? leadComment,
    required String number,
    required String qrToken,
    required String qrSig,
    required String verifyUrl,
    required DateTime signedAt,
  }) async {
    if (!pdfLanguages.contains(language)) throw DataRuleException('unsupported_language', language);
    final blockers = <ProtocolBlocker>[];
    final session = await SessionRepository(_ctx).require(sessionId);
    final sites = SiteRepository(_ctx);
    final site = await sites.require(session.siteId);
    final org = await SettingsRepository(_ctx).organization();
    final users = UserRepository(_ctx);
    final engineer = await users.require(session.engineerId);
    final signer = await users.require(_audit.actorId);
    final device = await (_db.select(
      _db.devices,
    )..where((d) => d.id.equals(_audit.deviceId) & d.orgId.equals(_ctx.orgId))).getSingle();
    final measurements = await _measurements.forSession(sessionId);
    final comment = leadComment?.trim();

    if (session.closedAt == null) blockers.add(const ProtocolBlocker('session_open'));
    if (measurements.isEmpty) blockers.add(const ProtocolBlocker('no_measurements'));
    if (!signerRoles.contains(signer.role)) blockers.add(ProtocolBlocker('forbidden_role', [signer.role]));
    if (device.revokedAt != null || device.publicKeyEd25519 != _signer.publicKeyHex) {
      blockers.add(ProtocolBlocker('device_not_trusted', [device.id]));
    }
    final licenseUntil = org.licenseValidUntil;
    if (org.licenseNo == null || org.licenseNo!.trim().isEmpty || licenseUntil == null) {
      blockers.add(const ProtocolBlocker('license_missing'));
    } else if (_day(signedAt).isAfter(_day(licenseUntil))) {
      blockers.add(const ProtocolBlocker('license_expired'));
    }
    final active = [
      for (final p in await forSession(sessionId))
        if (await status(p.id) == ProtocolStatus.active) p.id,
    ];
    if (active.isNotEmpty) blockers.add(ProtocolBlocker('already_signed', active));

    // Asboblar: o'lchov paytida qiyoslash guvohnomasi amal qilgan bo'lishi shart (o'chirilgan asbob ham hisobga olinadi).
    final instrumentIds = {for (final m in measurements) m.instrumentId}.toList()..sort();
    final instruments = {
      for (final i in await (_db.select(
        _db.instruments,
      )..where((i) => i.id.isIn(instrumentIds) & i.orgId.equals(_ctx.orgId))).get())
        i.id: i,
    };
    final expired = [
      for (final m in measurements)
        if (!instrumentValidFor(instruments[m.instrumentId], m)) m.id,
    ];
    if (expired.isNotEmpty) blockers.add(ProtocolBlocker('instrument_expired', expired));

    // Normalar: bitta to'plam. Muhandis tekshiruvi talab qilinmaydi (1-darvoza olib tashlangan, ADR-0019) — tekshiruv holati
    // payload'da (`reviewed_by`) va PDF'da ochiq ko'rsatiladi ("muhandis tekshiruvidan o'tmagan").
    final versions = {for (final m in measurements) m.normSetVersion}.toList()..sort();
    if (versions.length > 1) blockers.add(ProtocolBlocker('mixed_norm_sets', versions));
    final normRow = versions.isEmpty ? null : await _normSets.row(versions.first);
    if (normRow != null) await _normSets.load(normRow.version); // hash tekshiruvi (`norm_set_tampered`)

    // NEEDS_REVIEW — faqat LEAD, izoh bilan (CLAUDE.md, 6-qoida).
    final needsReview = [
      for (final m in measurements)
        if (m.verdict == Verdict.needsReview) m.id,
    ];
    if (needsReview.isNotEmpty) {
      if (signer.role != 'LEAD') blockers.add(ProtocolBlocker('needs_review_requires_lead', needsReview));
      if (comment == null || comment.isEmpty) blockers.add(ProtocolBlocker('lead_comment_required', needsReview));
    }

    final nodes = {
      for (final n in await (_db.select(
        _db.nodes,
      )..where((n) => n.siteId.equals(site.id) & n.orgId.equals(_ctx.orgId))).get())
        n.id: n,
    };
    final payload = <String, Object?>{
      'schema': protocolPayloadSchema,
      'protocol': {
        'number': number,
        'qr_token': qrToken,
        'qr_sig': qrSig,
        'verify_url': verifyUrl,
        'language': language,
      },
      'lab': {
        'org_id': org.id,
        'name': org.name,
        'license_no': org.licenseNo,
        'license_valid_until': _iso(org.licenseValidUntil),
      },
      'site': {
        'id': site.id,
        'name': site.name,
        'address': site.address,
        'customer': site.customer,
        'earthing_system': site.earthingSystem?.code,
        'u0_volts': site.u0Volts,
      },
      'session': {
        'id': session.id,
        'kind': session.kind.code,
        'started_at': _iso(session.startedAt),
        'closed_at': _iso(session.closedAt),
        'ambient_temp_c': session.ambientTempC,
        'humidity_pct': session.humidityPct,
      },
      'engineer': {'id': engineer.id, 'full_name': engineer.fullName, 'safety_group': engineer.safetyGroup},
      'signer': {
        'id': signer.id,
        'full_name': signer.fullName,
        'role': signer.role,
        'device_id': device.id,
        'public_key': device.publicKeyEd25519,
      },
      'signed_at': _iso(signedAt),
      'lead_comment': comment == null || comment.isEmpty ? null : comment,
      'norm_set': {
        'version': normRow?.version ?? '',
        'sha256': normRow?.sha256 ?? '',
        'reviewed_by': normRow?.reviewedBy,
        'reviewed_at': normRow?.reviewedAt,
      },
      'instruments': [
        for (final id in instrumentIds)
          if (instruments[id] case final i?)
            {
              'id': i.id,
              'kind': i.kind,
              'model': i.model,
              'serial_no': i.serialNo,
              'cert_no': i.verificationCertNo,
              'verified_until': _iso(i.verifiedUntil),
            },
      ],
      'measurements': [for (final m in measurements) _measurementPayload(m, nodes[m.nodeId])],
      'summary': verdictCounts(measurements.map((m) => m.verdict)),
    };
    return ProtocolDraft(sessionId: sessionId, payload: payload, blockers: blockers);
  }
}

Map<String, Object?> _measurementPayload(MeasurementRow m, NodeRow? node) {
  final detail = m.evalDetail;
  final decisive = [
    for (final c in (detail['checks'] as List?) ?? const [])
      if (c is Map && c['norm_id'] == m.normId) c,
  ];
  final check = decisive.where((c) => c['verdict'] == m.verdict.code).firstOrNull ?? decisive.firstOrNull;
  return {
    'id': m.id,
    'node_id': m.nodeId,
    'node_label': node?.label ?? m.nodeId,
    'node_kind': node?.kind.code ?? '',
    'type': m.type.code,
    'instrument_id': m.instrumentId,
    'entered_via': m.enteredVia.code,
    'created_at': _iso(m.createdAt),
    'values': m.values,
    'verdict': m.verdict.code,
    'norm_id': m.normId,
    'reason': detail['reason'],
    'formula': check?['formula'],
    'limit': check?['limit'],
    'margin_pct': detail['margin_pct'],
    'k_corr': detail['k_corr'],
    'supersedes_id': m.supersedesId,
  };
}

/// `PROTOCOL_SIGNED` audit hodisasining payload'i (hash shu xaritadan; import ham shu bilan tekshiradi).
Map<String, Object?> protocolAuditPayload(ProtocolRow row) => {
  'id': row.id,
  'session_id': row.sessionId,
  'number': row.number,
  'payload_sha256': row.payloadSha256,
  'pdf_sha256': row.pdfSha256,
  'signature': row.signature,
  'sig_alg': row.sigAlg,
  'qr_token': row.qrToken,
};

/// Asbob o'lchov kuni amal qilganmi: hozirgi guvohnoma VA o'lchov paytida yozib qo'yilgan muddat bo'yicha (ikkalasi ham
/// amal qilishi shart — keyingi qayta qiyoslash eski o'lchovni "tozalamaydi", 6-qoida).
bool instrumentValidFor(InstrumentRow? i, MeasurementRow m) {
  if (i == null || !instrumentVerificationValid(i, m.createdAt)) return false;
  if (!m.evalDetail.containsKey(instrumentVerifiedUntilKey)) return true; // eski yozuvlar (muddat saqlanmagan)
  final at = m.evalDetail[instrumentVerifiedUntilKey];
  final until = at is String ? DateTime.tryParse(at) : null;
  return until != null && instrumentVerificationValid(i.copyWith(verifiedUntil: Value(until)), m.createdAt);
}

DateTime _day(DateTime t) {
  final u = t.toUtc();
  return DateTime.utc(u.year, u.month, u.day);
}

String? _iso(DateTime? t) => t == null ? null : isoUtcMillis(t);
