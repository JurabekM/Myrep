import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/app_session.dart';
import 'package:omborai_mobile/src/auth.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/sync/ops.dart' as o;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

const _store = '11111111-2222-3333-4444-555555555555';
const _ownerId = 'aaaaaaaa-0000-4000-8000-000000000001';

String _freshPath() =>
    '${Directory.systemTemp.createTempSync('omb').path}/db.sqlite';

void main() {
  setUpAll(() => sqfliteFfiInit());

  late LocalDb db;
  late AppSession session;

  setUp(() async {
    db = await LocalDb.open(_freshPath(), factory: databaseFactoryFfi);
    final owner = await hashPassword('egasi-parol-1');
    await db.applyOp(
      o.newOp(
        type: o.opUser,
        storeId: _store,
        deviceId: 'dev-owner',
        payload: {
          'id': _ownerId,
          'login': 'egasi',
          'name': 'Egasi',
          'role': 'owner',
          'salt': owner.salt,
          'pw_hash': owner.hash,
          'active': true,
        },
      ),
    );
    await db.setState('store_id', _store);
    session = AppSession(db: db, keys: StoreKeyStore());
    await session.restore(); // faqat do'kon id'sini oladi, MQTT ishga tushmaydi
    session.currentUser = await db.getUser(_ownerId);
  });

  tearDown(() => db.close());

  test('egasi kassir qo\'shadi, kassir login qila oladi', () async {
    await session.addCashier(
      name: 'Ali',
      login: ' Ali ',
      password: 'kassir-parol-1',
    );

    final cashier = await db.findUser(_store, 'ali');
    expect(cashier, isNotNull);
    expect(cashier!['role'], 'cashier');
    expect(
      await verifyPassword(
        'kassir-parol-1',
        cashier['salt'] as String,
        cashier['pw_hash'] as String,
      ),
      isTrue,
    );
    expect(
      (await session.users()).map((u) => u['login']),
      containsAll(['egasi', 'ali']),
    );
  });

  test('band login va qisqa parol rad etiladi', () async {
    await session.addCashier(
      name: 'Ali',
      login: 'ali',
      password: 'kassir-parol-1',
    );
    await expectLater(
      session.addCashier(
        name: 'Boshqa',
        login: 'ALI',
        password: 'kassir-parol-2',
      ),
      throwsA(
        isA<AuthException>().having((e) => e.message, 'xabar', 'Bu login band'),
      ),
    );
    await expectLater(
      session.addCashier(name: 'Vali', login: 'vali', password: 'qisqa'),
      throwsA(isA<AuthException>()),
    );
  });

  test(
    'kassir o\'chirilsa login ishlamaydi, faollashtirilsa qayta ishlaydi',
    () async {
      await session.addCashier(
        name: 'Ali',
        login: 'ali',
        password: 'kassir-parol-1',
      );
      final id = (await db.findUser(_store, 'ali'))!['id'] as String;

      await session.setUserActive(id, active: false);
      expect(await db.findUser(_store, 'ali'), isNull);

      await session.setUserActive(id, active: true);
      expect(await db.findUser(_store, 'ali'), isNotNull);
    },
  );

  test('egasini o\'chirib bo\'lmaydi', () async {
    await expectLater(
      session.setUserActive(_ownerId, active: false),
      throwsA(isA<AuthException>()),
    );
  });

  test('kassir foydalanuvchi boshqara olmaydi', () async {
    await session.addCashier(
      name: 'Ali',
      login: 'ali',
      password: 'kassir-parol-1',
    );
    session.currentUser = await db.findUser(_store, 'ali');
    expect(session.isOwner, isFalse);
    await expectLater(
      session.addCashier(
        name: 'Vali',
        login: 'vali',
        password: 'kassir-parol-2',
      ),
      throwsA(isA<AuthException>()),
    );
    await expectLater(session.users(), throwsA(isA<AuthException>()));
  });
}
