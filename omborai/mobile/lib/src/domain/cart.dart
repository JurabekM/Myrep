import 'package:decimal/decimal.dart';
import 'package:uuid/uuid.dart';

import '../money.dart';

class CartLine {
  CartLine({
    required this.productId,
    required this.name,
    required this.unit,
    required this.unitPrice,
    required this.qty,
  });

  final String productId;
  final String name;
  final String unit;
  final int unitPrice;
  Decimal qty;

  int get lineTotal => roundSom(qty * Decimal.fromInt(unitPrice));
}

/// Savat. Narx klientda faqat ko'rsatish uchun; yuborilayotgan savdoda narx bo'lmaydi.
class Cart {
  final List<CartLine> _lines = [];

  List<CartLine> get lines => List.unmodifiable(_lines);
  bool get isEmpty => _lines.isEmpty;
  int get subtotal => _lines.fold(0, (sum, line) => sum + line.lineTotal);
  int get total => subtotal; // mobil ilovada chegirma yo'q

  CartLine? _find(String productId) {
    for (final line in _lines) {
      if (line.productId == productId) return line;
    }
    return null;
  }

  void add(Map<String, dynamic> product, {Decimal? qty}) {
    final amount = qty ?? Decimal.one;
    if (amount <= Decimal.zero) {
      throw ArgumentError('Miqdor musbat bo\'lishi kerak');
    }
    final existing = _find(product['id'] as String);
    if (existing != null) {
      existing.qty = existing.qty + amount;
      return;
    }
    _lines.add(
      CartLine(
        productId: product['id'] as String,
        name: product['name'] as String,
        unit: product['unit'] as String,
        unitPrice: (product['sale_price'] as num).toInt(),
        qty: amount,
      ),
    );
  }

  void setQty(String productId, Decimal qty) {
    final line = _find(productId);
    if (line == null) throw ArgumentError('Qatorga topilmadi: $productId');
    if (qty <= Decimal.zero) {
      remove(productId);
    } else {
      line.qty = qty;
    }
  }

  void remove(String productId) =>
      _lines.removeWhere((line) => line.productId == productId);

  void clear() => _lines.clear();

  /// MQTT orqali yuboriladigan savdo (desktop bilan bir xil shakl). Narx va jami qurilmada hisoblanadi.
  Map<String, dynamic> toSalePayload({
    required String storeId,
    required String method,
    String? saleId,
  }) {
    final total = this.total;
    return {
      'id': saleId ?? const Uuid().v4(),
      'store_id': storeId,
      'items': [
        for (final line in _lines)
          {
            'product_id': line.productId,
            'qty': line.qty.toString(),
            'product_name': line.name,
            'unit': line.unit,
            'unit_price': line.unitPrice,
            'line_total': line.lineTotal,
          },
      ],
      'discount': 0,
      'subtotal': subtotal,
      'total': total,
      'payments': [
        {'method': method, 'amount': total},
      ],
    };
  }
}
