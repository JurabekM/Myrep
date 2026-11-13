import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../app_session.dart';

const _units = ['dona', 'kg', 'litr', 'metr', 'quti', 'paket'];
final _barcodeRe = RegExp(r'^[A-Za-z0-9-]{4,64}$');

/// Tovar qo'shish yoki tahrirlash. Saqlash MQTT 'product' operatsiyasini yuboradi.
class ProductFormScreen extends StatefulWidget {
  const ProductFormScreen({super.key, required this.session, this.product});

  final AppSession session;
  final Map<String, dynamic>? product;

  @override
  State<ProductFormScreen> createState() => _ProductFormScreenState();
}

class _ProductFormScreenState extends State<ProductFormScreen> {
  late final TextEditingController _name;
  late final TextEditingController _sale;
  late final TextEditingController _cost;
  late final TextEditingController _minStock;
  late final TextEditingController _barcodes;
  late String _unit;
  String? _error;

  @override
  void initState() {
    super.initState();
    final p = widget.product;
    _name = TextEditingController(text: p?['name'] as String? ?? '');
    _sale = TextEditingController(text: '${p?['sale_price'] ?? 0}');
    _cost = TextEditingController(text: '${p?['cost_price'] ?? 0}');
    _minStock = TextEditingController(text: '${p?['min_stock'] ?? '0'}');
    _barcodes = TextEditingController(
      text: ((p?['barcodes'] as List?) ?? const []).join(', '),
    );
    _unit = (p?['unit'] as String?) ?? 'dona';
  }

  @override
  void dispose() {
    for (final c in [_name, _sale, _cost, _minStock, _barcodes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final name = _name.text.trim();
    final sale = int.tryParse(_sale.text.trim());
    final cost = int.tryParse(_cost.text.trim());
    final minStock = Decimal.tryParse(
      _minStock.text.trim().replaceAll(',', '.'),
    );
    final codes = _barcodes.text
        .split(',')
        .map((c) => c.trim())
        .where((c) => c.isNotEmpty)
        .toList();
    if (name.length < 2) return _fail("Nomi kamida 2 belgi bo'lishi kerak");
    if (sale == null || cost == null || sale < 0 || cost < 0) {
      return _fail("Narxlar butun son bo'lishi kerak");
    }
    if (minStock == null || minStock < Decimal.zero) {
      return _fail('Minimal qoldiq musbat raqam bo\'lishi kerak');
    }
    if (codes.any((c) => !_barcodeRe.hasMatch(c)) ||
        codes.toSet().length != codes.length) {
      return _fail('Shtrix-kodlar noto\'g\'ri yoki takrorlangan');
    }
    await widget.session.saveProduct({
      'id': widget.product?['id'] ?? const Uuid().v4(),
      'name': name,
      'unit': _unit,
      'sale_price': sale,
      'cost_price': cost,
      'min_stock': minStock.toString(),
      'barcodes': codes,
      'deleted': false,
    });
    if (mounted) Navigator.pop(context);
  }

  Future<void> _delete() async {
    final p = widget.product;
    if (p == null) return;
    await widget.session.deleteProduct({
      ...p,
      'min_stock': '${p['min_stock']}',
    });
    if (mounted) Navigator.pop(context);
  }

  void _fail(String message) => setState(() => _error = message);

  @override
  Widget build(BuildContext context) {
    final editing = widget.product != null;
    return Scaffold(
      appBar: AppBar(
        title: Text(editing ? 'Tovarni tahrirlash' : 'Yangi tovar'),
        actions: [
          if (editing)
            IconButton(
              tooltip: "O'chirish",
              onPressed: _delete,
              icon: const Icon(Icons.delete_outline),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _name,
            decoration: const InputDecoration(labelText: 'Nomi'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _unit,
            decoration: const InputDecoration(labelText: 'Birlik'),
            items: [
              for (final u in _units)
                DropdownMenuItem(value: u, child: Text(u)),
            ],
            onChanged: (v) => setState(() => _unit = v ?? _unit),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _sale,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: "Sotuv narxi (so'm)"),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _cost,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: "Tannarx (so'm)"),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _minStock,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Minimal qoldiq'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _barcodes,
            decoration: const InputDecoration(
              labelText: 'Shtrix-kodlar (vergul bilan)',
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _save,
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(52),
            ),
            child: const Text('Saqlash'),
          ),
        ],
      ),
    );
  }
}
