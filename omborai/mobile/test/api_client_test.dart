import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:omborai_mobile/src/api/api_client.dart';

const _base = 'http://api.test';

Map<String, dynamic> _tokens(String access, String refresh) => {
  'access_token': access,
  'refresh_token': refresh,
  'token_type': 'bearer',
  'expires_in': 900,
};

void main() {
  test('login tokenlarni saqlaydi va Bearer yuboradi', () async {
    final seen = <String>[];
    final client = MockClient((req) async {
      if (req.url.path == '/v1/auth/login') {
        return http.Response(jsonEncode(_tokens('a1', 'r1')), 200);
      }
      seen.add(req.headers['Authorization'] ?? '');
      return http.Response(jsonEncode([]), 200);
    });
    final api = ApiClient(baseUrl: _base, client: client);
    await api.login('a@b.uz', 'parol-12345');
    await api.stores();
    expect(seen, ['Bearer a1']);
  });

  test(
    '401 bo\'lsa refresh qilinadi va so\'rov bir marta qayta yuboriladi',
    () async {
      final paths = <String>[];
      final client = MockClient((req) async {
        paths.add(req.url.path);
        if (req.url.path == '/v1/auth/refresh') {
          return http.Response(jsonEncode(_tokens('a2', 'r2')), 200);
        }
        if (req.headers['Authorization'] == 'Bearer a1') {
          return http.Response(
            jsonEncode({'title': 'Token muddati tugagan'}),
            401,
          );
        }
        return http.Response(jsonEncode([]), 200);
      });
      final api = ApiClient(baseUrl: _base, client: client)
        ..restoreTokens(const Tokens('a1', 'r1'));
      expect(await api.stores(), isEmpty);
      expect(paths, ['/v1/stores', '/v1/auth/refresh', '/v1/stores']);
    },
  );

  test('problem+json xatosi ApiException bo\'ladi', () async {
    final client = MockClient(
      (_) async => http.Response(
        jsonEncode({'title': 'Ruxsat yo\'q', 'detail': 'Do\'kon topilmadi'}),
        403,
        headers: {'content-type': 'application/problem+json'},
      ),
    );
    final api = ApiClient(baseUrl: _base, client: client)
      ..restoreTokens(const Tokens('a', 'r'));
    await expectLater(
      api.stores(),
      throwsA(
        isA<ApiException>()
            .having((e) => e.status, 'status', 403)
            .having(
              (e) => e.message,
              'message',
              'Ruxsat yo\'q: Do\'kon topilmadi',
            ),
      ),
    );
  });

  test('tarmoq uzilsa OfflineException', () async {
    final client = MockClient(
      (_) async => throw http.ClientException('uzildi'),
    );
    final api = ApiClient(baseUrl: _base, client: client)
      ..restoreTokens(const Tokens('a', 'r'));
    await expectLater(api.stores(), throwsA(isA<OfflineException>()));
  });
}
