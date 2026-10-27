import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';
import 'package:zanjir_data/zanjir_data.dart';

void main() {
  group('ServerApi refresh', () {
    test('parallel so\'rovlar — bitta refresh, ikkalasi ham muvaffaqiyatli (L2, ADR-0014)', () async {
      var refreshes = 0;
      var valid = 'a1';
      final gate = Completer<void>();
      final client = MockClient((req) async {
        if (req.url.path.endsWith('/auth/refresh')) {
          refreshes++;
          final body = jsonDecode(req.body) as Map;
          // Eski refresh token qayta kelsa — server sessiyani yopadi (reuse detection).
          if (body['refresh_token'] != 'r$refreshes') return http.Response('{"detail":{"code":"invalid_token"}}', 401);
          await gate.future;
          valid = 'a${refreshes + 1}';
          return http.Response(jsonEncode({'access_token': valid, 'refresh_token': 'r${refreshes + 1}'}), 200);
        }
        if (req.headers['authorization'] != 'Bearer $valid' || valid == 'a1') {
          return http.Response('{"detail":{"code":"invalid_token"}}', 401);
        }
        return http.Response(jsonEncode({'id': 'u', 'org_id': 'o', 'full_name': 'F', 'role': 'LEAD'}), 200);
      });
      final store = MemoryTokenStore();
      await store.write(const ServerTokens('a1', 'r1'));
      final api = ServerApi('https://example.test', tokens: store, client: client);
      final both = Future.wait([api.me(), api.me(), api.me()]);
      await Future<void>.delayed(const Duration(milliseconds: 10));
      gate.complete();
      final users = await both;
      expect(users.map((u) => u.id), ['u', 'u', 'u']);
      expect(refreshes, 1);
      expect((await store.read())!.refresh, 'r2');
      // Keyingi so'rov — yangi token bilan, refresh'siz.
      await api.me();
      expect(refreshes, 1);
    });

    test('refresh rad etilsa — tokenlar o\'chiriladi, session_expired', () async {
      final client = MockClient((req) async => http.Response('{"detail":{"code":"invalid_token"}}', 401));
      final store = MemoryTokenStore();
      await store.write(const ServerTokens('a1', 'r1'));
      final api = ServerApi('https://example.test', tokens: store, client: client);
      await expectLater(api.me(), throwsA(isA<ServerException>().having((e) => e.code, 'code', 'session_expired')));
      expect(await store.read(), isNull);
    });
  });
}
