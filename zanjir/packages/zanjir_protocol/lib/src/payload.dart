import 'package:zanjir_core/zanjir_core.dart';

/// Payload sxemasi versiyasi. Maydonlar o'zgarsa — yangi versiya va ADR (ADR-0010).
const protocolPayloadSchema = 'zanjir.protocol/1';

/// `payload_sha256` — kanonik JSON (RFC 8785) ning SHA-256 i. PDF `/ID` ham shu qiymat.
String protocolPayloadSha256(Map<String, Object?> payload) => sha256Hex(canonicalJsonBytes(payload));

/// Natijalar soni: `{total, PASS, FAIL, NEEDS_REVIEW, NOT_APPLICABLE}` — barcha kalitlar har doim bor.
Map<String, int> verdictCounts(Iterable<Verdict> verdicts) {
  final counts = {for (final v in Verdict.values) v.code: 0};
  var total = 0;
  for (final v in verdicts) {
    counts[v.code] = counts[v.code]! + 1;
    total++;
  }
  return {'total': total, ...counts};
}
