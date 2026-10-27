/// Server bilan aloqa interfeysi (HTTP — [ServerApi]; testlarda soxtasi).
abstract interface class SyncTransport {
  Future<PullPage> pull(int since, {int? limit});

  /// Paket to'liq qabul qilinadi yoki rad etiladi ([ServerException] `push_rejected`).
  Future<Map<String, String>> push(List<Map<String, Object?>> ops);
}

class PullPage {
  const PullPage({required this.changes, required this.serverRev, required this.hasMore});
  final List<PullChange> changes;
  final int serverRev;
  final bool hasMore;
}

class PullChange {
  const PullChange(this.table, this.serverRev, this.row);
  final String table;
  final int serverRev;
  final Map<String, Object?> row;
}

/// Server xatosi: HTTP holati, barqaror `code` (masalan, `push_rejected`, `invalid_credentials`) va `reason`.
class ServerException implements Exception {
  const ServerException(this.status, this.code, {this.reason, this.opId});
  final int status;
  final String code;
  final String? reason;
  final String? opId;

  /// Tarmoq yoki server mavjud emas (0 — javob yo'q).
  bool get unavailable => status == 0 || status >= 500;

  @override
  String toString() => 'ServerException($status, $code${reason == null ? '' : ', $reason'})';
}

/// Server paketni rad etdi (`push_rejected`, ADR-0012/0014): qaysi navbat yozuvi ([table], [rowId]) va nima uchun.
/// Navbat saqlanadi; pull baribir bajariladi — qurilma boshqalarning o'zgarishlarini olishda davom etadi.
class SyncRejected extends ServerException {
  SyncRejected(ServerException e, {this.table, this.rowId}) : super(e.status, e.code, reason: e.reason, opId: e.opId);
  final String? table;
  final String? rowId;

  @override
  String toString() => 'SyncRejected($reason, $table/$rowId)';
}
