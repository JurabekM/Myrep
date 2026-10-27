import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// Xotiradagi soxta ZANJIR serveri (ilova UI testlari uchun). Haqiqiy server qoidalari — server pytest va
/// `packages/zanjir_data/test/e2e` (FastAPI + PostgreSQL) da tekshiriladi.
class FakeHttpServer {
  static const now = '2026-10-26T08:00:00.000Z';

  final rows = <String, Map<String, Object?>>{}; // "table/id"
  final revs = <String, int>{};
  final ops = <String>{};
  final users = <String, ({String id, String org, String password})>{}; // phone →
  final tokens = <String, String>{}; // access → user id
  final refresh = <String, String>{}; // refresh → user id
  final invites = <String, ({String org, String role})>{};
  var rev = 0;
  var _n = 0;
  int pushCalls = 0;
  String? rejectPushReason;

  late final http.Client client = MockClient(_handle);

  List<Map<String, Object?>> table(String t) => [
    for (final e in rows.entries)
      if (e.key.startsWith('$t/')) e.value,
  ];

  void _put(String table, Map<String, Object?> row) {
    rows['$table/${row['id']}'] = row;
    revs['$table/${row['id']}'] = ++rev;
  }

  String _id() => '00000000-0000-7000-8000-${(++_n).toString().padLeft(12, '0')}';

  Map<String, Object?> _session(String userId) {
    final access = 'a${++_n}', refreshToken = 'r${++_n}-refresh-token-xxxxxxxxxxxx';
    tokens[access] = userId;
    refresh[refreshToken] = userId;
    final u = rows['app_user/$userId']!;
    return {
      'access_token': access,
      'refresh_token': refreshToken,
      'token_type': 'bearer',
      'expires_in': 900,
      'user': {
        'id': userId,
        'org_id': u['org_id'],
        'full_name': u['full_name'],
        'role': u['role'],
        'safety_group': u['safety_group'],
      },
    };
  }

  void _user(String id, String org, Map<String, Object?> b, String role) {
    users[b['phone']! as String] = (id: id, org: org, password: b['password']! as String);
    _put('app_user', {
      'id': id,
      'org_id': org,
      'created_at': now,
      'updated_at': now,
      'rev': 1,
      'deleted': false,
      'full_name': b['full_name'],
      'role': role,
      'safety_group': b['safety_group'],
    });
  }

  http.Response _json(int status, Object body) =>
      http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json; charset=utf-8'});

  http.Response _err(int status, String code, [String? reason]) => _json(status, {
    'detail': {'code': code, 'reason': ?reason},
  });

  Future<http.Response> _handle(http.Request r) async {
    final path = r.url.path.replaceFirst(RegExp('^/'), '');
    final body = r.body.isEmpty ? <String, Object?>{} : (jsonDecode(r.body) as Map).cast<String, Object?>();
    switch ((r.method, path)) {
      case ('POST', 'auth/register'):
        if (users.containsKey(body['phone'])) return _err(409, 'conflict');
        final org = (body['org_id'] as String?) ?? _id();
        _put('organization', {
          'id': org,
          'created_at': now,
          'updated_at': now,
          'rev': 1,
          'deleted': false,
          'name': body['org_name'],
          'license_no': body['license_no'],
          'license_valid_until': body['license_valid_until'],
        });
        final id = (body['user_id'] as String?) ?? _id();
        _user(id, org, body, body['role']! as String);
        return _json(201, _session(id));
      case ('POST', 'auth/login'):
        final u = users[body['phone']];
        if (u == null || u.password != body['password']) return _err(401, 'invalid_credentials');
        return _json(200, _session(u.id));
      case ('POST', 'auth/accept-invite'):
        final inv = invites.remove(body['code']);
        if (inv == null) return _err(400, 'invalid_invite');
        final id = (body['user_id'] as String?) ?? _id();
        _user(id, inv.org, body, inv.role);
        return _json(201, _session(id));
      case ('POST', 'auth/refresh'):
        final u = refresh.remove(body['refresh_token']);
        return u == null ? _err(401, 'invalid_refresh') : _json(200, _session(u));
      case ('POST', 'auth/logout'):
        refresh.remove(body['refresh_token']);
        return http.Response('', 204);
    }
    final user = tokens[(r.headers['authorization'] ?? '').replaceFirst('Bearer ', '')];
    if (user == null) return _err(401, 'invalid_token');
    final me = rows['app_user/$user']!;
    switch ((r.method, path)) {
      case ('GET', 'me'):
        return _json(200, me);
      case ('POST', 'invites'):
        final code = 'KOD${(++_n).toString().padLeft(13, '0')}';
        invites[code] = (org: me['org_id']! as String, role: body['role']! as String);
        return _json(201, {'id': _id(), 'role': body['role'], 'expires_at': now, 'used_at': null, 'code': code});
      case ('POST', 'devices'):
        _put('device', {
          'id': body['id'],
          'org_id': me['org_id'],
          'created_at': now,
          'updated_at': now,
          'rev': 1,
          'deleted': false,
          'user_id': user,
          'public_key_ed25519': body['public_key_ed25519'],
          'sig_alg': body['sig_alg'],
          'registered_at': now,
          'revoked_at': null,
        });
        return _json(201, rows['device/${body['id']}']!);
      case ('GET', 'sync/pull'):
        final since = int.parse(r.url.queryParameters['since'] ?? '0');
        final changes = [
          for (final e in revs.entries)
            if (e.value > since) {'table': e.key.split('/').first, 'server_rev': e.value, 'row': rows[e.key]},
        ]..sort((a, b) => (a['server_rev']! as int).compareTo(b['server_rev']! as int));
        return _json(200, {
          'changes': changes,
          'server_rev': changes.isEmpty ? since : changes.last['server_rev']!,
          'has_more': false,
        });
      case ('POST', 'sync/push'):
        pushCalls++;
        if (rejectPushReason != null) return _err(422, 'push_rejected', rejectPushReason);
        final results = <Map<String, String>>[];
        for (final op in (body['ops']! as List).cast<Map<String, Object?>>()) {
          final id = op['client_op_id']! as String;
          final t = op['table']! as String;
          final row = (op['row']! as Map).cast<String, Object?>();
          final old = rows['$t/${row['id']}'];
          String status;
          if (!ops.add(id)) {
            status = 'duplicate';
          } else if (old != null &&
              (old['updated_at']! as String).compareTo(row['updated_at']! as String) >= 0 &&
              (old['rev']! as int) >= (row['rev']! as int)) {
            status = 'stale';
          } else {
            _put(t, row);
            status = 'applied';
          }
          results.add({'client_op_id': id, 'status': status});
        }
        return _json(200, {'results': results, 'server_rev': rev});
    }
    return _err(404, 'not_found');
  }
}
