import 'package:baraka_daftari/core/money/money.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('wholeMajor — tiyin tashlanadi, manfiyda nolga qarab', () {
    expect(const Money(123456, CurrencyCode.uzs).wholeMajor, 1234);
    expect(const Money(-123456, CurrencyCode.uzs).wholeMajor, -1234);
    expect(const Money(99, CurrencyCode.uzs).wholeMajor, 0);
    expect(const Money(12345, CurrencyCode.usd).wholeMajor, 123);
  });
}
