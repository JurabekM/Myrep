import 'dart:convert';
import 'dart:typed_data';

import 'canonical_json.dart';
import 'hex.dart';
import 'sha256.dart';
import 'signer.dart';

/// Protokol imzosi (prompt 5.4): signature = Ed25519(payload_sha256 ‖ pdf_sha256), 32 + 32 xom bayt.
class ProtocolSignature {
  const ProtocolSignature({
    required this.payloadSha256,
    required this.pdfSha256,
    required this.signature,
    required this.sigAlg,
  });
  final String payloadSha256;
  final String pdfSha256;
  final String signature;
  final String sigAlg;

  Map<String, Object?> toJson() => {
    'payload_sha256': payloadSha256,
    'pdf_sha256': pdfSha256,
    'signature': signature,
    'sig_alg': sigAlg,
  };
}

Uint8List protocolMessage(String payloadSha256, String pdfSha256) =>
    Uint8List.fromList([...hexDecode(payloadSha256), ...hexDecode(pdfSha256)]);

/// QR token (ADR-0014): `qr_sig = Ed25519("zanjir.qr/1\n<org_id>\n<raqam>")`, `qr_token = sha256(qr_sig)[:32]`.
/// Token qurilma kalitisiz yasalmaydi va oldindan bilinmaydi — boshqa tashkilot uni "band qila" olmaydi.
Uint8List qrTokenMessage(String orgId, String number) => utf8.encode('zanjir.qr/1\n$orgId\n$number');

String qrTokenFromSignature(String qrSigHex) => sha256Hex(hexDecode(qrSigHex)).substring(0, 32);

Future<ProtocolSignature> signProtocol({
  required Object? payload,
  required List<int> pdfBytes,
  required Signer signer,
}) async {
  final payloadSha = sha256Hex(canonicalJsonBytes(payload));
  final pdfSha = sha256Hex(pdfBytes);
  final sig = await signer.sign(protocolMessage(payloadSha, pdfSha));
  return ProtocolSignature(
    payloadSha256: payloadSha,
    pdfSha256: pdfSha,
    signature: hexEncode(sig),
    sigAlg: signer.sigAlg,
  );
}

/// Xato sababi (`payload_hash_mismatch` | `pdf_hash_mismatch` | `bad_signature`) yoki null — hammasi to'g'ri.
Future<String?> verifyProtocol({
  required Object? payload,
  required List<int> pdfBytes,
  required ProtocolSignature signature,
  required String publicKeyHex,
}) async {
  if (sha256Hex(canonicalJsonBytes(payload)) != signature.payloadSha256) return 'payload_hash_mismatch';
  if (sha256Hex(pdfBytes) != signature.pdfSha256) return 'pdf_hash_mismatch';
  final valid = await verifySignature(
    sigAlg: signature.sigAlg,
    publicKeyHex: publicKeyHex,
    message: protocolMessage(signature.payloadSha256, signature.pdfSha256),
    signatureHex: signature.signature,
  );
  return valid ? null : 'bad_signature';
}
