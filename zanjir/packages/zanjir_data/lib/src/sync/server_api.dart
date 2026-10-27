import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'transport.dart';

/// Access va refresh tokenlar. Ilovada — `flutter_secure_storage` (Keystore); logga yozilmaydi.
abstract interface class TokenStore {
  Future<ServerTokens?> read();
  Future<void> write(ServerTokens tokens);
  Future<void> clear();
}

class ServerTokens {
  const ServerTokens(this.access, this.refresh);
  final String access;
  final String refresh;
}

class MemoryTokenStore implements TokenStore {
  ServerTokens? _t;

  @override
  Future<ServerTokens?> read() async => _t;

  @override
  Future<void> write(ServerTokens tokens) async => _t = tokens;

  @override
  Future<void> clear() async => _t = null;
}

/// Serverdagi foydalanuvchi (kirish javobi).
class ServerUser {
  const ServerUser({required this.id, required this.orgId, required this.fullName, required this.role});
  final String id;
  final String orgId;
  final String fullName;
  final String role;

  factory ServerUser.fromJson(Map<String, Object?> j) => ServerUser(
    id: j['id']! as String,
    orgId: j['org_id']! as String,
    fullName: j['full_name']! as String,
    role: j['role']! as String,
  );
}

/// ZANJIR server HTTP mijozi (ADR-0011/0012). Access token muddati o'tsa — bir marta refresh va qayta urinish;
/// refresh ham o'tmasa — `ServerException(401, 'session_expired')` (qayta kirish kerak).
class ServerApi implements SyncTransport {
  ServerApi(String baseUrl, {required this.tokens, http.Client? client, this.timeout = const Duration(seconds: 30)})
    : _base = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/'),
      _client = client ?? http.Client();

  final Uri _base;
  final http.Client _client;
  final TokenStore tokens;
  final Duration timeout;

  // --- kirish ---

  Future<ServerUser> register({
    required String orgName,
    required String fullName,
    required String phone,
    required String password,
    String role = 'LEAD',
    String? orgId,
    String? userId,
    String? licenseNo,
    DateTime? licenseValidUntil,
    String? safetyGroup,
  }) => _session('auth/register', {
    'org_name': orgName,
    'full_name': fullName,
    'phone': phone,
    'password': password,
    'role': role,
    'org_id': ?orgId,
    'user_id': ?userId,
    'license_no': ?licenseNo,
    'license_valid_until': ?licenseValidUntil?.toUtc().toIso8601String(),
    'safety_group': ?safetyGroup,
  });

  Future<ServerUser> login({required String phone, required String password}) =>
      _session('auth/login', {'phone': phone, 'password': password});

  Future<ServerUser> acceptInvite({
    required String code,
    required String fullName,
    required String phone,
    required String password,
    String? userId,
    String? safetyGroup,
  }) => _session('auth/accept-invite', {
    'code': code,
    'full_name': fullName,
    'phone': phone,
    'password': password,
    'user_id': ?userId,
    'safety_group': ?safetyGroup,
  });

  Future<void> logout() async {
    final t = await tokens.read();
    if (t != null) {
      try {
        await _send('POST', 'auth/logout', body: {'refresh_token': t.refresh}, auth: false);
      } on ServerException {
        // Server yetib bo'lmasa ham lokal tokenlar o'chiriladi.
      }
    }
    await tokens.clear();
  }

  Future<ServerUser> me() async => ServerUser.fromJson(await _json('GET', 'me'));

  // --- tashkilot ---

  /// Taklif kodi (faqat shu javobda ko'rinadi).
  Future<String> createInvite(String role, {int ttlHours = 72}) async =>
      (await _json('POST', 'invites', body: {'role': role, 'ttl_hours': ttlHours}))['code']! as String;

  Future<void> registerDevice({required String id, required String publicKeyHex, String sigAlg = 'Ed25519'}) =>
      _json('POST', 'devices', body: {'id': id, 'public_key_ed25519': publicKeyHex, 'sig_alg': sigAlg});

  Future<void> revokeDevice(String id) => _json('POST', 'devices/$id/revoke');

  // --- sinxronlash ---

  @override
  Future<PullPage> pull(int since, {int? limit}) async {
    final j = await _json('GET', 'sync/pull?since=$since${limit == null ? '' : '&limit=$limit'}');
    return PullPage(
      changes: [
        for (final c in j['changes']! as List)
          PullChange(
            (c as Map)['table']! as String,
            (c['server_rev']! as num).toInt(),
            (c['row']! as Map).cast<String, Object?>(),
          ),
      ],
      serverRev: (j['server_rev']! as num).toInt(),
      hasMore: j['has_more']! as bool,
    );
  }

  @override
  Future<Map<String, String>> push(List<Map<String, Object?>> ops) async {
    final j = await _json('POST', 'sync/push', body: {'ops': ops});
    return {for (final r in j['results']! as List) (r as Map)['client_op_id']! as String: r['status']! as String};
  }

  /// Ochiq sahifa / PDF (E2E testlar uchun).
  Future<http.Response> getPublic(String path) => _client.get(_base.resolve(path)).timeout(timeout);

  void close() => _client.close();

  // --- ichki ---

  Future<ServerUser> _session(String path, Map<String, Object?> body) async {
    final j = await _json('POST', path, body: body, auth: false);
    await tokens.write(ServerTokens(j['access_token']! as String, j['refresh_token']! as String));
    return ServerUser.fromJson((j['user']! as Map).cast<String, Object?>());
  }

  Future<Map<String, Object?>> _json(String method, String path, {Object? body, bool auth = true}) async {
    final r = await _send(method, path, body: body, auth: auth);
    if (r.body.isEmpty) return const {};
    final decoded = jsonDecode(utf8.decode(r.bodyBytes));
    return decoded is Map ? decoded.cast<String, Object?>() : {'items': decoded};
  }

  Future<http.Response> _send(
    String method,
    String path, {
    Object? body,
    bool auth = true,
    bool retried = false,
  }) async {
    final headers = {'content-type': 'application/json'};
    String? access;
    if (auth) {
      final t = await tokens.read();
      if (t == null) throw const ServerException(401, 'not_authenticated');
      access = t.access;
      headers['authorization'] = 'Bearer $access';
    }
    final req = http.Request(method, _base.resolve(path))..headers.addAll(headers);
    if (body != null) req.body = jsonEncode(body);
    late http.Response r;
    try {
      r = await http.Response.fromStream(await _client.send(req).timeout(timeout));
    } on SocketException {
      throw const ServerException(0, 'unavailable');
    } on TimeoutException {
      throw const ServerException(0, 'timeout');
    } on http.ClientException {
      throw const ServerException(0, 'unavailable');
    }
    if (r.statusCode < 400) return r;
    final err = _error(r);
    if (auth && !retried && r.statusCode == 401 && err.code == 'invalid_token' && await _refresh(access!)) {
      return _send(method, path, body: body, auth: auth, retried: true);
    }
    throw err;
  }

  Future<bool>? _refreshing;

  /// Bir vaqtda bitta refresh (ADR-0014): parallel so'rovlar bir xil refresh tokenni ikki marta yuborsa, server buni
  /// o'g'irlik deb biladi (reuse detection) va sessiyani yopadi. Token boshqa so'rov tomonidan allaqachon yangilangan
  /// bo'lsa — refresh'siz qayta urinish.
  Future<bool> _refresh(String staleAccess) async {
    final current = await tokens.read();
    if (current != null && current.access != staleAccess) return true;
    return _refreshing ??= _rotate().whenComplete(() => _refreshing = null);
  }

  Future<bool> _rotate() async {
    final t = await tokens.read();
    if (t == null) return false;
    try {
      final j = await _json('POST', 'auth/refresh', body: {'refresh_token': t.refresh}, auth: false);
      await tokens.write(ServerTokens(j['access_token']! as String, j['refresh_token']! as String));
      return true;
    } on ServerException catch (e) {
      if (e.status == 401) {
        await tokens.clear();
        throw const ServerException(401, 'session_expired');
      }
      rethrow;
    }
  }

  static ServerException _error(http.Response r) {
    try {
      final d = (jsonDecode(utf8.decode(r.bodyBytes)) as Map)['detail'];
      if (d is Map) {
        return ServerException(
          r.statusCode,
          d['code'] as String? ?? 'error',
          reason: d['reason'] as String?,
          opId: d['op_id'] as String?,
        );
      }
    } on FormatException {
      // JSON emas.
    }
    return ServerException(r.statusCode, 'http_${r.statusCode}');
  }
}
