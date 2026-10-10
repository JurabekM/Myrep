import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// Server xato javobi (RFC 7807 problem+json).
class ApiException implements Exception {
  ApiException(this.status, this.title, [this.detail]);

  final int status;
  final String title;
  final String? detail;

  String get message =>
      (detail == null || detail!.isEmpty) ? title : '$title: $detail';

  @override
  String toString() => 'ApiException($status, $title)';
}

/// Server bilan aloqa yo'q (tarmoq uzilgan yoki vaqt tugagan).
class OfflineException implements Exception {
  OfflineException(this.cause);

  final Object cause;

  @override
  String toString() => 'OfflineException($cause)';
}

class Tokens {
  const Tokens(this.access, this.refresh);

  final String access;
  final String refresh;
}

/// Tokenlarni saqlash (Android Keystore; testda xotira).
abstract class TokenStorage {
  Future<Tokens?> read();
  Future<void> write(Tokens tokens);
  Future<void> clear();
}

/// REST klient: faqat autentifikatsiya (login) va do'kon ro'yxati. Ma'lumot almashinuvi MQTT orqali.
class ApiClient {
  ApiClient({
    required this.baseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 10),
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final Duration timeout;
  final http.Client _client;

  String? _access;
  String? _refresh;
  Future<bool>? _refreshing;

  void Function(Tokens tokens)? onTokensChanged;

  bool get hasSession => _access != null;

  void restoreTokens(Tokens tokens) {
    _access = tokens.access;
    _refresh = tokens.refresh;
  }

  void clearSession() {
    _access = null;
    _refresh = null;
  }

  void close() => _client.close();

  static const _json = {'Content-Type': 'application/json; charset=utf-8'};

  Future<void> login(String email, String password) async {
    final data = await _send(
      'POST',
      '/v1/auth/login',
      body: {'email': email, 'password': password},
      auth: false,
    );
    _storeTokens(data as Map<String, dynamic>);
  }

  void _storeTokens(Map<String, dynamic> data) {
    _access = data['access_token'] as String;
    _refresh = data['refresh_token'] as String;
    onTokensChanged?.call(Tokens(_access!, _refresh!));
  }

  Future<bool> _tryRefresh() {
    final running = _refreshing;
    if (running != null) return running;
    final future = _doRefresh();
    _refreshing = future.whenComplete(() => _refreshing = null);
    return _refreshing!;
  }

  Future<bool> _doRefresh() async {
    final refresh = _refresh;
    if (refresh == null) return false;
    final http.Response resp;
    try {
      resp = await _client
          .post(
            Uri.parse('$baseUrl/v1/auth/refresh'),
            headers: _json,
            body: jsonEncode({'refresh_token': refresh}),
          )
          .timeout(timeout);
    } on Object catch (e) {
      throw OfflineException(e);
    }
    if (resp.statusCode != 200) return false;
    _storeTokens(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
    return true;
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Object? body,
    bool auth = true,
  }) async {
    var resp = await _raw(method, path, body: body, auth: auth);
    if (resp.statusCode == 401 && auth && await _tryRefresh()) {
      resp = await _raw(method, path, body: body, auth: auth);
    }
    if (resp.statusCode >= 400) throw _errorFrom(resp);
    if (resp.bodyBytes.isEmpty) return null;
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  Future<http.Response> _raw(
    String method,
    String path, {
    Object? body,
    required bool auth,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = {
      ..._json,
      if (auth && _access != null) 'Authorization': 'Bearer $_access',
    };
    final encoded = body == null ? null : jsonEncode(body);
    try {
      final future = switch (method) {
        'GET' => _client.get(uri, headers: headers),
        'POST' => _client.post(uri, headers: headers, body: encoded),
        _ => throw ArgumentError("Noma'lum metod: $method"),
      };
      return await future.timeout(timeout);
    } on TimeoutException catch (e) {
      throw OfflineException(e);
    } on http.ClientException catch (e) {
      throw OfflineException(e);
    }
  }

  ApiException _errorFrom(http.Response resp) {
    try {
      final body =
          jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
      final detail = body['detail'];
      return ApiException(
        resp.statusCode,
        body['title'] as String? ?? resp.reasonPhrase ?? 'Xatolik',
        detail is String ? detail : null,
      );
    } on FormatException {
      return ApiException(resp.statusCode, resp.reasonPhrase ?? 'Xatolik');
    }
  }

  Future<List<Map<String, dynamic>>> stores() async {
    final data = await _send('GET', '/v1/stores') as List<dynamic>;
    return data.cast<Map<String, dynamic>>();
  }
}
