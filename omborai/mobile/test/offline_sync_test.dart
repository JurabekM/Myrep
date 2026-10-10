import 'dart:convert';

import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:omborai_mobile/src/api/api_client.dart';
import 'package:omborai_mobile/src/domain/cart.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/offline/sync_service.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

const _store = 's1';
const _product = {
  'id': 'p1',
  'name': 'Shakar 1 kg',
  'unit': 'kg',
  'sale_price': 14500,
  'barcodes': ['4780012300017'],
};

Future<LocalDb> _db() async {
  sqfliteFfiInit();
  return LocalDb.open(inMemoryDatabasePath, factory: databaseFactoryFfi);
}

Map<String, dynamic> _movement(
  String id,
  String qty, {
  String kind = 'receipt',
  String? ref,
}) => {
  'id': id,
  'store_id': _store,
  'product_id': 'p1',
  'qty': qty,
  'kind': kind,
  'reference_id': ref,
};

Cart _cartWith(String qty) {
  final cart = Cart()..add(_product, qty: Decimal.parse(qty));
  return cart;
}

void main() {
  setUpAll(() => sqfliteFfiInit());

  test('qoldiq = serverdan kelgan harakatlar - navbatdagi savdolar', () async {
    final db = await _db();
    await db.applyPull({
      'products': [_product],
      'movements': [_movement('m1', '10')],
      'cursors': {'movements': 'c1'},
      'has_more': false,
    });
    await db.enqueueSale(
      _store,
      _cartWith('3')
          .toSalePayload(storeId: _store, method: 'cash', amount: 43500),
      createdAt: '2026-10-10T10:00:00',
    );

    expect(await db.balance(_store, 'p1'), Decimal.fromInt(7));
    expect(await db.pendingCount(), 1);
    await db.close();
  });

  test('applied savdo serverdan harakat kelguncha hisobda qoladi, keyin tozalanadi', () async {
    final db = await _db();
    final payload = _cartWith('1')
        .toSalePayload(storeId: _store, method: 'cash', amount: 14500);
    await db.applyPull({
      'products': [_product],
      'movements': [_movement('m1', '5')],
      'cursors': {},
      'has_more': false,
    });
    await db.enqueueSale(_store, payload, createdAt: '2026-10-10T10:00:00');
    await db.applyPushResults([
      {'op_id': payload['id'], 'status': 'applied'},
    ]);
    expect(await db.pendingCount(), 0);
    expect(await db.balance(_store, 'p1'), Decimal.fromInt(4));

    await db.applyPull({
      'products': [],
      'movements': [
        _movement('m2', '-1', kind: 'sale', ref: payload['id'] as String),
      ],
      'cursors': {},
      'has_more': false,
    });
    expect(await db.balance(_store, 'p1'), Decimal.fromInt(4));
    expect(await db.rejectedOps(), isEmpty);
    await db.close();
  });

  test('rad etilgan savdo saqlanadi va qoldiqni band qilmaydi', () async {
    final db = await _db();
    await db.applyPull({
      'products': [_product],
      'movements': [_movement('m1', '5')],
      'cursors': {},
      'has_more': false,
    });
    final bad = _cartWith('50')
        .toSalePayload(storeId: _store, method: 'cash', amount: 725000);
    await db.enqueueSale(_store, bad, createdAt: '2026-10-10T10:00:00');
    await db.applyPushResults([
      {
        'op_id': bad['id'],
        'status': 'rejected',
        'error_title': 'Qoldiq yetarli emas',
        'error_detail': '5',
      },
    ]);

    final rejected = await db.rejectedOps();
    expect(rejected.single['error_title'], 'Qoldiq yetarli emas');
    expect(await db.balance(_store, 'p1'), Decimal.fromInt(5));
    await db.acknowledgeRejected(bad['id'] as String);
    expect(await db.rejectedOps(), isEmpty);
    await db.close();
  });

  test(
    'pull idempotent va kursorlar saqlanadi; mahsulot qidiruvi va shtrix-kod',
    () async {
      final db = await _db();
      final page = {
        'products': [_product],
        'movements': [_movement('m1', '2')],
        'cursors': {'movements': 'x'},
        'has_more': false,
      };
      await db.applyPull(page);
      await db.applyPull(page);
      expect(await db.balance(_store, 'p1'), Decimal.fromInt(2));
      expect(await db.cursors(), {'movements': 'x'});
      expect(
        (await db.productByBarcode('4780012300017', _store))?['name'],
        'Shakar 1 kg',
      );
      expect((await db.searchProducts('SHAKAR', _store)).length, 1);
      await db.close();
    },
  );

  test('SyncService: avval push, keyin sahifalangan pull', () async {
    final db = await _db();
    final sale = _cartWith('1')
        .toSalePayload(storeId: _store, method: 'cash', amount: 14500);
    await db.enqueueSale(_store, sale, createdAt: '2026-10-10T10:00:00');

    final pulls = <String>[];
    final client = MockClient((req) async {
      if (req.url.path == '/v1/sync/push') {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        final op = (body['ops'] as List).single as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'results': [
              {'op_id': op['op_id'], 'status': 'applied', 'duplicate': false},
            ],
          }),
          200,
        );
      }
      pulls.add(req.url.queryParameters['products_cursor'] ?? '');
      final page = pulls.length == 1
          ? {
              'products': [_product],
              'movements': [_movement('m1', '4')],
              'cursors': {'movements': 'a'},
              'has_more': true,
            }
          : {
              'products': [],
              'movements': [
                _movement('m2', '-1', kind: 'sale', ref: sale['id'] as String),
              ],
              'cursors': {'movements': 'b'},
              'has_more': false,
            };
      return http.Response(jsonEncode(page), 200);
    });
    final api = ApiClient(baseUrl: 'http://api.test', client: client)
      ..restoreTokens(const Tokens('a', 'r'));

    final report = await SyncService(api, db).runOnce(_store);

    expect(report.pushed, 1);
    expect(report.applied, 1);
    expect(report.pulledMovements, 2);
    expect(await db.pendingCount(), 0);
    expect(await db.balance(_store, 'p1'), Decimal.fromInt(3));
    expect(await db.cursors(), {'movements': 'b'});
    await db.close();
  });

  test(
    'aloqa yo\'q bo\'lsa sync OfflineException tashlaydi, navbat saqlanadi',
    () async {
      final db = await _db();
      await db.enqueueSale(
        _store,
        _cartWith('1')
            .toSalePayload(storeId: _store, method: 'cash', amount: 14500),
        createdAt: '2026-10-10T10:00:00',
      );
      final client = MockClient(
        (_) async => throw http.ClientException('yo\'q'),
      );
      final api = ApiClient(baseUrl: 'http://api.test', client: client)
        ..restoreTokens(const Tokens('a', 'r'));

      await expectLater(
        SyncService(api, db).runOnce(_store),
        throwsA(isA<OfflineException>()),
      );
      expect(await db.pendingCount(), 1);
      await db.close();
    },
  );
}
