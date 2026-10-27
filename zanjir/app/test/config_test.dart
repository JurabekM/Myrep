import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/core/config.dart';

void main() {
  test('server manzili: faqat https; http — faqat debug va lokal (ADR-0014)', () {
    expect(isAllowedServerUrl('https://zanjir.uz/', debug: false), isTrue);
    expect(isAllowedServerUrl('http://zanjir.uz/', debug: false), isFalse);
    expect(isAllowedServerUrl('http://zanjir.uz/', debug: true), isFalse);
    expect(isAllowedServerUrl('http://10.0.2.2:8080/', debug: true), isTrue);
    expect(isAllowedServerUrl('http://10.0.2.2:8080/', debug: false), isFalse);
    expect(isAllowedServerUrl('https://user:parol@zanjir.uz/', debug: false), isFalse);
    expect(isAllowedServerUrl('zanjir.uz', debug: true), isFalse);
    expect(isAllowedServerUrl('ftp://zanjir.uz/', debug: true), isFalse);
  });
}
