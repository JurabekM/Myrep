import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/sync/ops.dart' as o;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

const store = 'store-1';
const dev = 'dev-a';

Map<String, dynamic> product(
  String id, {
  int price = 12000,
  String ts = '2026-01-01T10:00:00Z',
  String name = 'Sut 1 L',
}) => {
  'id': id,
  'name': name,
  'unit': 'dona',
  'sale_price': price,
  'updated_ts': ts,
};

Map<String, dynamic> saleOp(
  String opId,
  String saleId,
  String productId,
  String qty,
) => o.newOp(
  opId: opId,
  type: o.opSale,
  storeId: store,
  deviceId: dev,
  ts: '2026-01-02T09:00:00Z',
  payload: {
    'id': saleId,
    'shift_id': 'shift-1',
    'number': 1,
    'total': 24000,
    'created_at': '2026-01-02T09:00:00Z',
    'items': [
      {'product_id': productId, 'qty': qty},
    ],
  },
);

Map<String, dynamic> refundOp(String saleId) => o.newOp(
  opId: o.refundOpId(saleId),
  type: o.opRefund,
  storeId: store,
  deviceId: 'dev-b',
  payload: {'sale_id': saleId},
);

void main() {
  late LocalDb db;

  setUpAll(() => sqfliteFfiInit());

  setUp(() async {
    db = await LocalDb.open(inMemoryDatabasePath, factory: databaseFactoryFfi);
  });

  tearDown(() => db.close());

  test('sotuv qoldiqni kamaytiradi va dublikat op e\'tiborsiz', () async {
    await db.applyOp(
      o.newOp(
        type: o.opProduct,
        storeId: store,
        deviceId: dev,
        ts: '2026-01-01T10:00:00Z',
        payload: product('p1'),
      ),
    );
    await db.applyOp(
      o.newOp(
        type: o.opMovement,
        storeId: store,
        deviceId: dev,
        payload: {'product_id': 'p1', 'qty': '10', 'kind': 'purchase'},
      ),
    );

    final sale = saleOp('op-sale-1', 'sale-1', 'p1', '2');
    expect(await db.applyOp(sale), isTrue);
    expect(
      await db.applyOp(sale),
      isFalse,
      reason: 'bir xil op_id ikki marta qo\'llanmasin',
    );

    expect(await db.balance(store, 'p1'), Decimal.fromInt(8));
  });

  test('qaytarish qoldiqni tiklaydi, faqat bir marta', () async {
    await db.applyOp(
      o.newOp(
        type: o.opProduct,
        storeId: store,
        deviceId: dev,
        ts: '2026-01-01T10:00:00Z',
        payload: product('p1'),
      ),
    );
    await db.applyOp(
      o.newOp(
        type: o.opMovement,
        storeId: store,
        deviceId: dev,
        payload: {'product_id': 'p1', 'qty': '5', 'kind': 'purchase'},
      ),
    );
    await db.applyOp(saleOp('op-sale-1', 'sale-1', 'p1', '2'));

    expect(await db.applyOp(refundOp('sale-1')), isTrue);
    // Ikkinchi qaytarish (boshqa qurilmadan ham) qoldiqni yana oshirmasligi kerak.
    expect(await db.applyOp(refundOp('sale-1')), isFalse);

    expect(await db.balance(store, 'p1'), Decimal.fromInt(5));
    final sale = await db.getSale('sale-1');
    expect(sale?['status'], 'refunded');
  });

  test(
    'yangi ts\'li tovar eskisini almashtiradi, eski ts e\'tiborsiz',
    () async {
      await db.applyOp(
        o.newOp(
          type: o.opProduct,
          storeId: store,
          deviceId: dev,
          ts: '2026-01-01T10:00:00Z',
          payload: product('p1', price: 12000),
        ),
      );
      await db.applyOp(
        o.newOp(
          type: o.opProduct,
          storeId: store,
          deviceId: dev,
          ts: '2026-01-05T10:00:00Z',
          payload: product('p1', price: 13000),
        ),
      );
      // Kechikib kelgan eski o'zgarish yangisini bosmasin.
      await db.applyOp(
        o.newOp(
          type: o.opProduct,
          storeId: store,
          deviceId: dev,
          ts: '2026-01-03T10:00:00Z',
          payload: product('p1', price: 9000),
        ),
      );

      final p = await db.getProduct('p1', store);
      expect(p?['sale_price'], 13000);
    },
  );

  test('ochiq smena bo\'lsa ikkinchi shift_open e\'tiborsiz', () async {
    Map<String, dynamic> open(String id) => o.newOp(
      type: o.opShiftOpen,
      storeId: store,
      deviceId: dev,
      payload: {'shift_id': id, 'opening_cash': 100000},
    );
    await db.applyOp(open('shift-1'));
    await db.applyOp(open('shift-2'));

    final current = await db.openShift(store);
    expect(current?['id'], 'shift-1');
  });

  test('snapshot faqat bo\'sh qurilmaga qo\'llanadi', () async {
    await db.applyOp(
      o.newOp(
        type: o.opProduct,
        storeId: store,
        deviceId: dev,
        ts: '2026-01-01T10:00:00Z',
        payload: product('p1'),
      ),
    );
    final snapshot = o.newOp(
      type: o.opSnapshot,
      storeId: store,
      deviceId: 'dev-b',
      payload: {
        'products': [product('p2', name: 'Non')],
        'balances': {'p2': '7'},
        'open_shift': null,
      },
    );
    expect(await db.applyOp(snapshot), isFalse);
    expect(await db.getProduct('p2', store), isNull);
    expect(await db.balance(store, 'p2'), Decimal.zero);
  });

  test('bo\'sh qurilma snapshot oladi', () async {
    final snapshot = o.newOp(
      type: o.opSnapshot,
      storeId: store,
      deviceId: 'dev-b',
      payload: {
        'products': [product('p2', name: 'Non')],
        'balances': {'p2': '7'},
        'open_shift': null,
      },
    );
    expect(await db.applyOp(snapshot), isTrue);
    expect((await db.getProduct('p2', store))?['name'], 'Non');
    expect(await db.balance(store, 'p2'), Decimal.fromInt(7));
  });
}
