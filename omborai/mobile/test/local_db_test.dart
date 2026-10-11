import 'dart:io';
import 'dart:typed_data';

import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/auth.dart';
import 'package:omborai_mobile/src/money.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/sync/identity.dart';
import 'package:omborai_mobile/src/sync/ops.dart' as ops;
import 'package:path/path.dart' as p;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:uuid/uuid.dart';

const _storeId = '5151ea51-5151-4151-8151-515151515151';
const _productId = '00000000-0000-0000-0000-000000000077';

/// Har bir test uchun alohida fayl (in-memory ulashilmasin).
Future<LocalDb> _openDb() async {
  sqfliteFfiInit();
  final dir = Directory.systemTemp.createTempSync('omborai_db_');
  return LocalDb.open(p.join(dir.path, 'db.db'), factory: databaseFactoryFfi);
}

/// Imzolovchi qurilma: o'z kaliti va lokal bazasi.
class _Dev {
  _Dev(this.identity, this.db, this.id);

  final DeviceIdentity identity;
  final LocalDb db;
  final String id;

  Future<Map<String, dynamic>> op(
    String type,
    Map<String, dynamic> payload, {
    String? opId,
    String? ts,
  }) {
    return ops.signedOp(
      identity,
      type: type,
      storeId: _storeId,
      payload: payload,
      deviceId: id,
      opId: opId,
      ts: ts,
    );
  }
}

Future<_Dev> _dev(int seedByte) async {
  final identity = await DeviceIdentity.fromSeed(Uint8List.fromList(List.filled(32, seedByte)));
  final db = await _openDb();
  return _Dev(identity, db, await db.deviceId());
}

Future<_Dev> _owner() async {
  final owner = await _dev(1);
  await owner.db.initOwner(
    storeId: _storeId,
    deviceId: owner.id,
    publicKeyHex: owner.identity.publicKeyHex,
    label: 'egasi',
  );
  return owner;
}

Future<_Dev> _joined(_Dev owner, int seedByte, {String role = ops.roleCashier}) async {
  final cashier = await _dev(seedByte);
  await cashier.db.setPairing(
    storeId: _storeId,
    ownerDeviceId: owner.id,
    ownerPublicKeyHex: owner.identity.publicKeyHex,
  );
  final approval = await owner.op(ops.opDevice, {
    'device_id': cashier.id,
    'public_key': cashier.identity.publicKeyHex,
    'role': role,
    'label': 'kassa-$seedByte',
    'active': true,
  });
  await owner.db.applyOp(approval);
  await cashier.db.applyOp(approval);
  final snapshot = await owner.op(ops.opSnapshot, await owner.db.snapshotPayload(_storeId));
  expect(await cashier.db.applyOp(snapshot), ops.resultApplied);
  return cashier;
}

Future<Map<String, dynamic>> _product(_Dev owner, int price, {String? name}) async {
  return owner.op(ops.opProduct, {
    'id': _productId,
    'name': name ?? 'Un',
    'unit': 'kg',
    'sale_price': price,
    'cost_price': 0,
    'min_stock': '0',
    'barcodes': <String>[],
    'deleted': false,
  });
}

Future<Map<String, dynamic>> _receipt(_Dev owner, String qty, {String kind = 'receipt'}) {
  return owner.op(ops.opMovement, {'product_id': _productId, 'qty': qty, 'kind': kind});
}

Future<Map<String, dynamic>> _sale(_Dev dev, String qty, int price, {String? shiftId}) async {
  final line = roundSom(Decimal.parse(qty) * Decimal.fromInt(price));
  final saleId = const Uuid().v4();
  final payload = {
    'id': saleId,
    'store_id': _storeId,
    'items': [
      {
        'product_id': _productId,
        'qty': qty,
        'product_name': 'Un',
        'unit': 'kg',
        'unit_price': price,
        'line_total': line,
      },
    ],
    'discount': 0,
    'subtotal': line,
    'total': line,
    'payments': [
      {'method': 'cash', 'amount': line},
    ],
    'shift_id': shiftId,
    'number': 'T-1',
    'created_at': ops.nowTs(),
  };
  return dev.op(ops.opSale, payload, opId: saleId);
}

Future<Map<String, dynamic>> _shiftOpen(_Dev dev) async {
  final shiftId = const Uuid().v4();
  return dev.op(ops.opShiftOpen, {'shift_id': shiftId, 'opening_cash': 0}, opId: shiftId);
}

void main() {
  test('egasi: tovar va kirim, qoldiq to\'g\'ri', () async {
    final owner = await _owner();
    expect(await owner.db.applyOp(await _product(owner, 10000)), ops.resultApplied);
    expect(await owner.db.applyOp(await _receipt(owner, '10')), ops.resultApplied);
    expect(await owner.db.balance(_storeId, _productId), Decimal.fromInt(10));
  });

  test('kassir tovar yoki kirim qo\'sha olmaydi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    expect(await cashier.db.applyOp(await _product(cashier, 1)), ops.resultRejected);
    expect(await cashier.db.applyOp(await _receipt(cashier, '100')), ops.resultRejected);
  });

  test('noto\'g\'ri imzoli operatsiya rad etiladi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    final op = await _product(owner, 1000);
    op['device'] = cashier.id; // muallif o'zgartirildi: imzo egasiniki
    expect(await owner.db.applyOp(op), ops.resultRejected);
    expect(await owner.db.applyOp({'nope': 1}), ops.resultRejected);
  });

  test('narx katalogga mos bo\'lishi shart (Y1)', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    await owner.db.applyOp(await _product(owner, 10000));
    await owner.db.applyOp(await _receipt(owner, '10'));
    expect(await owner.db.applyOp(await _sale(cashier, '2', 10000)), ops.resultApplied);
    expect(await owner.db.applyOp(await _sale(cashier, '2', 1)), ops.resultRejected);
    expect(await owner.db.balance(_storeId, _productId), Decimal.fromInt(8));
  });

  test('katalog hali kelmagan sotuv kutiladi, katalog kelgach qo\'llanadi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    final catalog = await _product(owner, 500);
    final sale = await _sale(cashier, '1', 500);
    expect(await owner.db.applyOp(sale), ops.resultPending);
    expect(await owner.db.applyOp(catalog), ops.resultApplied);
    expect(await owner.db.getSale(sale['op_id'] as String), isNotNull);
  });

  test('qaytarish o\'z mahsulotlarini olib yuradi (K6): snapshotdan keyin ulangan qurilma', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    await owner.db.applyOp(await _product(owner, 1000));
    await owner.db.applyOp(await _receipt(owner, '10'));
    final sale = await _sale(cashier, '3', 1000);
    await owner.db.applyOp(sale);
    final late = await _joined(owner, 5);
    expect(await late.db.balance(_storeId, _productId), Decimal.fromInt(7));
    final refund = await owner.op(
      ops.opRefund,
      {
        'sale_id': sale['op_id'],
        'items': [
          {'product_id': _productId, 'qty': '3'},
        ],
      },
      opId: ops.refundOpId(sale['op_id'] as String),
    );
    expect(await owner.db.applyOp(refund), ops.resultApplied);
    expect(await late.db.applyOp(refund), ops.resultApplied);
    expect(await late.db.balance(_storeId, _productId), Decimal.fromInt(10));
  });

  test('qaytarish sotuvdan oldin kelsa ham chek holati to\'g\'ri (K7)', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    await owner.db.applyOp(await _product(owner, 1000));
    await owner.db.applyOp(await _receipt(owner, '10'));
    final other = await _joined(owner, 6); // snapshot: qoldiq 10, sotuv hali yo'q
    final sale = await _sale(cashier, '3', 1000); // T dan keyin
    await owner.db.applyOp(sale);
    final refund = await owner.op(
      ops.opRefund,
      {
        'sale_id': sale['op_id'],
        'items': [
          {'product_id': _productId, 'qty': '3'},
        ],
      },
      opId: ops.refundOpId(sale['op_id'] as String),
    );
    expect(await other.db.applyOp(refund), ops.resultApplied);
    expect(await other.db.applyOp(sale), ops.resultApplied);
    expect(await other.db.balance(_storeId, _productId), Decimal.fromInt(10));
    expect((await other.db.getSale(sale['op_id'] as String))!['status'], 'refunded');
  });

  test('kassir qaytara olmaydi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    await owner.db.applyOp(await _product(owner, 1000));
    await owner.db.applyOp(await _receipt(owner, '10'));
    final sale = await _sale(cashier, '1', 1000);
    await owner.db.applyOp(sale);
    final fake = await cashier.op(
      ops.opRefund,
      {
        'sale_id': sale['op_id'],
        'items': [
          {'product_id': _productId, 'qty': '1'},
        ],
      },
      opId: ops.refundOpId(sale['op_id'] as String),
    );
    expect(await owner.db.applyOp(fake), ops.resultRejected);
  });

  test('smena: har bir qurilmada alohida; bir qurilmada ikkinchi smena rad', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    final own = await _shiftOpen(owner);
    final theirs = await _shiftOpen(cashier);
    expect(await owner.db.applyOp(own), ops.resultApplied);
    expect(await owner.db.applyOp(theirs), ops.resultApplied);
    expect((await owner.db.openShiftForDevice(owner.id))!['id'], own['op_id']);
    expect((await owner.db.openShiftForDevice(cashier.id))!['id'], theirs['op_id']);
    expect(await owner.db.applyOp(await _shiftOpen(cashier)), ops.resultRejected);
  });

  test('K5: bootstrapgacha jonli sotuv snapshot\'ni rad ettirmaydi, ikki marta sanalmaydi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    await owner.db.applyOp(await _product(owner, 1000));
    await owner.db.applyOp(await _receipt(owner, '10'));
    final newcomer = await _dev(7);
    await newcomer.db.setPairing(
      storeId: _storeId,
      ownerDeviceId: owner.id,
      ownerPublicKeyHex: owner.identity.publicKeyHex,
    );
    final live = await _sale(cashier, '2', 1000);
    await owner.db.applyOp(live);
    expect(await newcomer.db.applyOp(live), ops.resultPending);
    final approval = await owner.op(ops.opDevice, {
      'device_id': newcomer.id,
      'public_key': newcomer.identity.publicKeyHex,
      'role': ops.roleCashier,
      'label': 'yangi',
      'active': true,
    });
    await owner.db.applyOp(approval);
    await newcomer.db.applyOp(approval);
    final snapshot = await owner.op(ops.opSnapshot, await owner.db.snapshotPayload(_storeId));
    expect(await newcomer.db.applyOp(snapshot), ops.resultApplied);
    expect(await newcomer.db.isBootstrapped(), isTrue);
    expect(await newcomer.db.balance(_storeId, _productId), Decimal.fromInt(8));
  });

  test('bootstrapdan keyin kelgan sotuv qo\'llanadi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    await owner.db.applyOp(await _product(owner, 1000));
    await owner.db.applyOp(await _receipt(owner, '10'));
    final newcomer = await _joined(owner, 8);
    final late = await _sale(cashier, '4', 1000);
    await owner.db.applyOp(late);
    expect(await newcomer.db.applyOp(late), ops.resultApplied);
    expect(await newcomer.db.balance(_storeId, _productId), Decimal.fromInt(6));
  });

  test('snapshot faqat egasidan; ikkinchi snapshot rad etiladi', () async {
    final owner = await _owner();
    final cashier = await _joined(owner, 2);
    final fake = await cashier.op(ops.opSnapshot, {
      'store': null,
      'devices': <Object>[],
      'users': <Object>[],
      'products': <Object>[],
      'balances': <String, String>{},
      'open_shifts': <Object>[],
    });
    final newcomer = await _dev(9);
    await newcomer.db.setPairing(
      storeId: _storeId,
      ownerDeviceId: owner.id,
      ownerPublicKeyHex: owner.identity.publicKeyHex,
    );
    expect(await newcomer.db.applyOp(fake), isNot(ops.resultApplied));
    expect(await newcomer.db.isBootstrapped(), isFalse);
    final again = await owner.op(ops.opSnapshot, await owner.db.snapshotPayload(_storeId));
    expect(await cashier.db.applyOp(again), ops.resultRejected);
  });

  test('qo\'shilish so\'rovi: faqat o\'z kaliti bilan imzolangan va hali qo\'shilmagan', () async {
    final owner = await _owner();
    final newcomer = await _dev(10);
    await newcomer.db.setPairing(
      storeId: _storeId,
      ownerDeviceId: owner.id,
      ownerPublicKeyHex: owner.identity.publicKeyHex,
    );
    final request = await newcomer.op(ops.opJoinRequest, {
      'device_id': newcomer.id,
      'public_key': newcomer.identity.publicKeyHex,
      'label': 'Telefon',
    });
    await owner.db.applyOp(
      await owner.op(ops.opStore, {'name': 'Do\'kon'}),
    );
    expect(await owner.db.verifyJoinRequest(request), isTrue);
    final forged = Map<String, dynamic>.from(request)
      ..['payload'] = {
        ...request['payload'] as Map<String, dynamic>,
        'public_key': (await _dev(11)).identity.publicKeyHex,
      };
    expect(await owner.db.verifyJoinRequest(forged), isFalse);
  });

  test('foydalanuvchi: kassir qo\'shiladi, egasi nofaol qilinmaydi', () async {
    final owner = await _owner();
    const salt = '00112233445566778899aabbccddeeff';
    final hash = await hashPassword('parol-12345', saltHex: salt);
    final userId = const Uuid().v4();
    final add = await owner.op(ops.opUser, {
      'id': userId,
      'login': 'ali',
      'name': 'Ali',
      'role': ops.roleCashier,
      'salt': hash.salt,
      'pw_hash': hash.hash,
      'active': true,
    });
    expect(await owner.db.applyOp(add), ops.resultApplied);
    expect(await owner.db.findUser(_storeId, 'ALI'), isNotNull);
    final ownerRow = await owner.db.findUser(_storeId, 'ali');
    expect(ownerRow, isNotNull);
    final deactivate = await owner.op(ops.opUser, {
      'id': userId,
      'login': 'ali',
      'name': 'Ali',
      'role': ops.roleCashier,
      'salt': hash.salt,
      'pw_hash': hash.hash,
      'active': false,
    });
    expect(await owner.db.applyOp(deactivate), ops.resultApplied);
    expect(await owner.db.findUser(_storeId, 'ali'), isNull);
  });

  test('noma\'lum muallif kutiladi, uning qurilmasi qo\'shilgach qo\'llanadi', () async {
    final owner = await _owner();
    final stranger = await _dev(12);
    await owner.db.applyOp(await _product(owner, 1000));
    final sale = await _sale(stranger, '1', 1000);
    expect(await owner.db.applyOp(sale), ops.resultPending);
    final approval = await owner.op(ops.opDevice, {
      'device_id': stranger.id,
      'public_key': stranger.identity.publicKeyHex,
      'role': ops.roleCashier,
      'label': 'yangi',
      'active': true,
    });
    expect(await owner.db.applyOp(approval), ops.resultApplied);
    expect(await owner.db.getSale(sale['op_id'] as String), isNotNull);
  });

  test('egasi qurilmasini bloklab bo\'lmaydi', () async {
    final owner = await _owner();
    final block = await owner.op(ops.opDevice, {
      'device_id': owner.id,
      'public_key': owner.identity.publicKeyHex,
      'role': ops.roleOwner,
      'label': 'egasi',
      'active': false,
    });
    expect(await owner.db.applyOp(block), ops.resultRejected);
  });

  test('takroriy yetkazish idempotent', () async {
    final owner = await _owner();
    final op = await _product(owner, 1000);
    expect(await owner.db.applyOp(op), ops.resultApplied);
    expect(await owner.db.applyOp(op), ops.resultDuplicate);
  });

  test('navbat: qo\'shish, PUBACK dan keyin o\'chirish', () async {
    final owner = await _owner();
    final op = await _product(owner, 100);
    await owner.db.enqueue(op);
    await owner.db.enqueue(op);
    expect(await owner.db.pendingCount(), 1);
    await owner.db.dropOutbox(op['op_id'] as String);
    expect(await owner.db.pendingCount(), 0);
  });
}
