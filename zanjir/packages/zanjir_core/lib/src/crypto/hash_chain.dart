import 'canonical_json.dart';
import 'hex.dart';
import 'sha256.dart';
import 'signer.dart';

/// Qurilma bo'yicha audit hash-zanjiri (prompt 5.4).
/// event_hash = SHA256(canonical({seq, prev_hash, actor_id, event_type, entity_id, payload_hash, created_at}))
/// device_sig = Ed25519(event_hash baytlari)
const String genesisHash = '0000000000000000000000000000000000000000000000000000000000000000';

final _hex64 = RegExp(r'^[0-9a-f]{64}$');
final _isoMs = RegExp(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$');

/// `audit_event` yozuvi (append-only).
class AuditEvent {
  const AuditEvent({
    required this.deviceId,
    required this.seq,
    required this.prevHash,
    required this.eventHash,
    required this.actorId,
    required this.eventType,
    required this.entityId,
    required this.payloadHash,
    required this.createdAt,
    required this.deviceSig,
    required this.sigAlg,
  });
  final String deviceId;
  final int seq;
  final String prevHash;
  final String eventHash;
  final String actorId;
  final String eventType;
  final String? entityId;
  final String payloadHash;

  /// UTC, millisekund aniqligida: `2026-10-26T07:05:03.120Z`.
  final String createdAt;
  final String deviceSig;
  final String sigAlg;

  AuditEvent withDeviceSig(String deviceSig) => AuditEvent(
    deviceId: deviceId,
    seq: seq,
    prevHash: prevHash,
    eventHash: eventHash,
    actorId: actorId,
    eventType: eventType,
    entityId: entityId,
    payloadHash: payloadHash,
    createdAt: createdAt,
    deviceSig: deviceSig,
    sigAlg: sigAlg,
  );

  Map<String, Object?> toJson() => {
    'device_id': deviceId,
    'seq': seq,
    'prev_hash': prevHash,
    'event_hash': eventHash,
    'actor_id': actorId,
    'event_type': eventType,
    'entity_id': entityId,
    'payload_hash': payloadHash,
    'created_at': createdAt,
    'device_sig': deviceSig,
    'sig_alg': sigAlg,
  };
}

class ChainVerification {
  const ChainVerification.ok() : ok = true, failedIndex = null, reason = null;
  const ChainVerification.failed(int this.failedIndex, String this.reason) : ok = false;
  final bool ok;
  final int? failedIndex;

  /// `invalid_format` | `unsupported_sig_alg` | `seq_gap` | `prev_hash_mismatch` | `event_hash_mismatch` | `bad_signature`.
  final String? reason;
}

String payloadHash(Object? payload) => sha256Hex(canonicalJsonBytes(payload));

String computeEventHash({
  required int seq,
  required String prevHash,
  required String actorId,
  required String eventType,
  required String? entityId,
  required String payloadHash,
  required String createdAt,
}) => sha256Hex(
  canonicalJsonBytes({
    'seq': seq,
    'prev_hash': prevHash,
    'actor_id': actorId,
    'event_type': eventType,
    'entity_id': entityId,
    'payload_hash': payloadHash,
    'created_at': createdAt,
  }),
);

/// Zanjirga keyingi hodisani qo'shadi (`previous == null` — birinchi hodisa).
Future<AuditEvent> appendEvent({
  required AuditEvent? previous,
  required Signer signer,
  required String deviceId,
  required String actorId,
  required String eventType,
  required String? entityId,
  required Object? payload,
  required DateTime createdAt,
}) async {
  final seq = (previous?.seq ?? 0) + 1;
  final prevHash = previous?.eventHash ?? genesisHash;
  final ph = payloadHash(payload);
  final at = isoUtcMillis(createdAt);
  final eh = computeEventHash(
    seq: seq,
    prevHash: prevHash,
    actorId: actorId,
    eventType: eventType,
    entityId: entityId,
    payloadHash: ph,
    createdAt: at,
  );
  return AuditEvent(
    deviceId: deviceId,
    seq: seq,
    prevHash: prevHash,
    eventHash: eh,
    actorId: actorId,
    eventType: eventType,
    entityId: entityId,
    payloadHash: ph,
    createdAt: at,
    deviceSig: hexEncode(await signer.sign(hexDecode(eh))),
    sigAlg: signer.sigAlg,
  );
}

/// Zanjirni tekshiradi; birinchi xato indeksi va sababi. `anchor` — oldin tasdiqlangan oxirgi hodisa.
/// Python (`zanjir_server.crypto.hash_chain.verify_chain`) bilan bir xil tartibda tekshiradi.
Future<ChainVerification> verifyChain(
  List<AuditEvent> events, {
  required String publicKeyHex,
  AuditEvent? anchor,
}) async {
  var prevSeq = anchor?.seq ?? 0;
  var prevHash = anchor?.eventHash ?? genesisHash;
  final deviceId = anchor?.deviceId ?? (events.isEmpty ? null : events.first.deviceId);
  for (var i = 0; i < events.length; i++) {
    final e = events[i];
    if (e.deviceId != deviceId ||
        !_hex64.hasMatch(e.prevHash) ||
        !_hex64.hasMatch(e.eventHash) ||
        !_hex64.hasMatch(e.payloadHash) ||
        !_isoMs.hasMatch(e.createdAt)) {
      return ChainVerification.failed(i, 'invalid_format');
    }
    if (!supportedSigAlgs.contains(e.sigAlg)) return ChainVerification.failed(i, 'unsupported_sig_alg');
    if (e.seq != prevSeq + 1) return ChainVerification.failed(i, 'seq_gap');
    if (e.prevHash != prevHash) return ChainVerification.failed(i, 'prev_hash_mismatch');
    final expected = computeEventHash(
      seq: e.seq,
      prevHash: e.prevHash,
      actorId: e.actorId,
      eventType: e.eventType,
      entityId: e.entityId,
      payloadHash: e.payloadHash,
      createdAt: e.createdAt,
    );
    if (e.eventHash != expected) return ChainVerification.failed(i, 'event_hash_mismatch');
    final valid = await verifySignature(
      sigAlg: e.sigAlg,
      publicKeyHex: publicKeyHex,
      message: hexDecode(e.eventHash),
      signatureHex: e.deviceSig,
    );
    if (!valid) return ChainVerification.failed(i, 'bad_signature');
    prevSeq = e.seq;
    prevHash = e.eventHash;
  }
  return const ChainVerification.ok();
}
