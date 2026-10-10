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

/// Server bilan aloqa yo'q (tarmoq uzilgan yoki vaqt tugagan). Offline rejimga o'tish uchun.
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

/// Tokenlarni saqlash (production'da xavfsiz xotira, testda oddiy xotira).
abstract class TokenStorage {
  Future<Tokens?> read();
  Future<void> write(Tokens tokens);
  Future<void> clear();
}

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

  /// Tokenlar o'zgarganda chaqiriladi (saqlash uchun).
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

  // --- autentifikatsiya -----------------------------------------------------

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

  // --- so'rovlar -------------------------------------------------------------

  static const _json = {'Content-Type': 'application/json; charset=utf-8'};

  Future<dynamic> _send(
    String method,
    String path, {
    Object? body,
    Map<String, Object?>? query,
    bool auth = true,
  }) async {
    var resp = await _raw(method, path, body: body, query: query, auth: auth);
    if (resp.statusCode == 401 && auth && await _tryRefresh()) {
      resp = await _raw(method, path, body: body, query: query, auth: auth);
    }
    if (resp.statusCode >= 400) throw _errorFrom(resp);
    if (resp.bodyBytes.isEmpty) return null;
    return jsonDecode(utf8.decode(resp.bodyBytes));
  }

  Future<http.Response> _raw(
    String method,
    String path, {
    Object? body,
    Map<String, Object?>? query,
    required bool auth,
  }) async {
    final uri = Uri.parse('$baseUrl$path')
        .replace(queryParameters: query?.map((k, v) => MapEntry(k, '$v')));
    final headers = {
      ..._json,
      if (auth && _access != null) 'Authorization': 'Bearer $_access',
    };
    final encoded = body == null ? null : jsonEncode(body);
    try {
      final future = switch (method) {
        'GET' => _client.get(uri, headers: headers),
        'POST' => _client.post(uri, headers: headers, body: encoded),
        _ => throw ArgumentError('Noma\'lum metod: $method'),
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

  // --- biznes so'rovlari ----------------------------------------------------

  Future<List<Map<String, dynamic>>> stores() async {
    final data = await _send('GET', '/v1/stores') as List<dynamic>;
    return data.cast<Map<String, dynamic>>();
  }

  /// Ochiq smena yo'q bo'lsa null (server 409 qaytaradi).
  Future<Map<String, dynamic>?> currentShift(String storeId) async {
    try {
      return await _send(
        'GET',
        '/v1/shifts/current',
        query: {'store_id': storeId},
      ) as Map<String, dynamic>;
    } on ApiException catch (e) {
      if (e.status == 409) return null;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> openShift(
    String storeId,
    int openingCash,
  ) async {
    return await _send(
      'POST',
      '/v1/shifts',
      body: {'store_id': storeId, 'opening_cash': openingCash},
    ) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> closeShift(
    String shiftId,
    int closingCash,
  ) async {
    return await _send(
      'POST',
      '/v1/shifts/$shiftId/close',
      body: {'closing_cash': closingCash},
    ) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>?> productByBarcode(
    String code,
    String storeId,
  ) async {
    try {
      return await _send(
        'GET',
        '/v1/products/by-barcode/$code',
        query: {'store_id': storeId},
      ) as Map<String, dynamic>;
    } on ApiException catch (e) {
      if (e.status == 404) return null;
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> searchProducts(
    String query,
    String storeId, {
    int limit = 50,
  }) async {
    final page = await _send(
      'GET',
      '/v1/products',
      query: {'q': query, 'store_id': storeId, 'limit': limit},
    ) as Map<String, dynamic>;
    return (page['items'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> balances(
    String storeId, {
    bool lowOnly = false,
  }) async {
    final data = await _send(
      'GET',
      '/v1/stock/balances',
      query: {'store_id': storeId, 'low_only': lowOnly},
    ) as List<dynamic>;
    return data.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> createSale(Map<String, dynamic> payload) async {
    return await _send('POST', '/v1/sales', body: payload)
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> syncPush(List<Map<String, dynamic>> ops) async {
    return await _send('POST', '/v1/sync/push', body: {'ops': ops})
        as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> syncPull(
    String storeId,
    Map<String, String> cursors, {
    int limit = 200,
  }) async {
    return await _send(
      'GET',
      '/v1/sync/pull',
      query: {
        'store_id': storeId,
        'products_cursor': cursors['products'] ?? '',
        'movements_cursor': cursors['movements'] ?? '',
        'sales_cursor': cursors['sales'] ?? '',
        'limit': limit,
      },
    ) as Map<String, dynamic>;
  }
}
