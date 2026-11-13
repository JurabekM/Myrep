import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/sync/ops.dart' as o;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Har bir baza alohida fayl: ffi'da ':memory:' ulanishlari bir-biri bilan ulashiladi.
String _freshPath() =>
    '${Directory.systemTemp.createTempSync('omb').path}/db.sqlite';

const store = 'store-users';
const dev = 'dev-users';

void main() {
  group('foydalanuvchi va do\'kon (serversiz login)', () {
    late LocalDb users;

    setUpAll(() => sqfliteFfiInit());

    setUp(() async {
      users = await LocalDb.open(_freshPath(), factory: databaseFactoryFfi);
    });

    tearDown(() => users.close());

    Map<String, dynamic> userOp(
      String uid,
      String login,
      String ts, {
      String hash = 'h1',
      bool active = true,
    }) => o.newOp(
      opId: 'user-$uid-$ts',
      type: o.opUser,
      storeId: store,
      deviceId: dev,
      ts: ts,
      payload: {
        'id': uid,
        'login': login,
        'name': login,
        'role': 'cashier',
        'salt': 'aa',
        'pw_hash': hash,
        'active': active,
      },
    );

    test('foydalanuvchi LWW: yangi ts g\'olib, eski ts e\'tiborsiz', () async {
      await users.applyOp(
        userOp('u1', 'kassir', '2026-01-01T10:00:00Z', hash: 'eski'),
      );
      await users.applyOp(
        userOp('u1', 'kassir', '2026-01-05T10:00:00Z', hash: 'yangi'),
      );
      await users.applyOp(
        userOp('u1', 'kassir', '2026-01-03T10:00:00Z', hash: 'kechikkan'),
      );

      final u = await users.findUser(store, '  KASSIR ');
      expect(u?['pw_hash'], 'yangi');
    });

    test('nofaol foydalanuvchi topilmaydi', () async {
      await users.applyOp(
        userOp('u2', 'bekor', '2026-01-01T10:00:00Z', active: false),
      );
      expect(await users.findUser(store, 'bekor'), isNull);
    });

    test('do\'kon nomi LWW bilan yangilanadi', () async {
      await users.applyOp(
        o.newOp(
          opId: 'st-1',
          type: o.opStore,
          storeId: store,
          deviceId: dev,
          ts: '2026-01-01T10:00:00Z',
          payload: {'name': 'Eski nom'},
        ),
      );
      await users.applyOp(
        o.newOp(
          opId: 'st-2',
          type: o.opStore,
          storeId: store,
          deviceId: dev,
          ts: '2026-01-02T10:00:00Z',
          payload: {'name': 'Yangi nom'},
        ),
      );
      expect(await users.storeName(store), 'Yangi nom');
    });

    test(
      'snapshot do\'kon va foydalanuvchilarni bo\'sh qurilmaga olib keladi',
      () async {
        final source = await LocalDb.open(
          _freshPath(),
          factory: databaseFactoryFfi,
        );
        addTearDown(source.close);
        await source.applyOp(
          o.newOp(
            opId: 'st-src',
            type: o.opStore,
            storeId: store,
            deviceId: dev,
            ts: '2026-01-01T10:00:00Z',
            payload: {'name': 'Asosiy'},
          ),
        );
        await source.applyOp(userOp('u-src', 'egasi', '2026-01-01T10:00:00Z'));
        final snapshot = o.newOp(
          opId: 'snap-1',
          type: o.opSnapshot,
          storeId: store,
          deviceId: 'dev-src',
          payload: await source.snapshotPayload(store),
        );

        expect(await users.applyOp(snapshot), isTrue);
        expect(await users.storeName(store), 'Asosiy');
        expect(await users.findUser(store, 'egasi'), isNotNull);
      },
    );
  });
}
