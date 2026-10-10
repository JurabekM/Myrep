import 'package:decimal/decimal.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/domain/cart.dart';
import 'package:omborai_mobile/src/money.dart';

void main() {
  test('formatSom ming ajratuvchi bo\'shliq bilan', () {
    expect(formatSom(14500), '14 500');
    expect(formatSom(1234567), '1 234 567');
    expect(formatSom(0), '0');
    expect(formatSom(-2000), '-2 000');
  });

  test('roundSom ROUND_HALF_UP', () {
    expect(roundSom(Decimal.parse('2.5')), 3);
    expect(roundSom(Decimal.parse('2.4')), 2);
  });

  test('formatQty ortiqcha nollarni olib tashlaydi', () {
    expect(formatQty(Decimal.parse('2.000')), '2');
    expect(formatQty(Decimal.parse('1.500')), '1.5');
    expect(formatQty(Decimal.parse('3')), '3');
  });

  final sut = {
    'id': 'p1',
    'name': 'Sut 1 L',
    'unit': 'dona',
    'sale_price': 12000,
  };
  final shakar = {
    'id': 'p2',
    'name': 'Shakar 1 kg',
    'unit': 'kg',
    'sale_price': 14500,
  };

  test('savat bir xil tovarni birlashtiradi va jami hisoblaydi', () {
    final cart = Cart()
      ..add(sut)
      ..add(sut)
      ..add(shakar, qty: Decimal.parse('1.5'));
    expect(cart.lines.length, 2);
    expect(cart.lines.first.qty, Decimal.fromInt(2));
    expect(
      cart.subtotal,
      24000 + roundSom(Decimal.parse('1.5') * Decimal.fromInt(14500)),
    );
    expect(cart.total, cart.subtotal);
  });

  test('miqdor nolga tushsa qator o\'chadi', () {
    final cart = Cart()..add(sut, qty: Decimal.fromInt(3));
    cart.setQty('p1', Decimal.zero);
    expect(cart.isEmpty, isTrue);
  });

  test('savdo payload\'ida narx yo\'q, id esa UUID', () {
    final cart = Cart()..add(sut, qty: Decimal.fromInt(2));
    final payload = cart.toSalePayload(
      storeId: 's1',
      method: 'cash',
      amount: 24000,
    );
    expect(payload['items'], [
      {'product_id': 'p1', 'qty': '2'},
    ]);
    expect(payload.toString().contains('sale_price'), isFalse);
    expect(
      payload['id'],
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
    expect(payload['payments'], [
      {'method': 'cash', 'amount': 24000},
    ]);
  });
}
