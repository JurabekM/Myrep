import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

import '../app_session.dart';
import '../money.dart';
import 'product_form_screen.dart';

/// Tovarlar katalogi: qidiruv, qo'shish, tahrirlash. Har bir o'zgarish MQTT operatsiyasi.
class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  final _query = TextEditingController();
  List<Map<String, dynamic>> _items = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final session = widget.session;
    final text = _query.text.trim().toLowerCase();
    final all = await session.db.searchProducts(
      '',
      session.storeId,
      limit: 1000,
    );
    if (!mounted) return;
    setState(() {
      _items = text.isEmpty
          ? all
          : all
                .where(
                  (p) => (p['name'] as String).toLowerCase().contains(text),
                )
                .toList();
    });
  }

  Future<void> _open([Map<String, dynamic>? product]) async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) =>
            ProductFormScreen(session: widget.session, product: product),
      ),
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tovarlar')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(),
        icon: const Icon(Icons.add),
        label: const Text('Yangi tovar'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: TextField(
              controller: _query,
              onChanged: (_) => _load(),
              decoration: const InputDecoration(
                hintText: 'Nom bo\'yicha qidirish',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
              ),
            ),
          ),
          Expanded(
            child: ListView.separated(
              itemCount: _items.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final p = _items[index];
                final stock = formatQty(
                  Decimal.parse('${p['stock_qty'] ?? 0}'),
                );
                return ListTile(
                  title: Text(p['name'] as String),
                  subtitle: Text(
                    "${formatSom((p['sale_price'] as num).toInt())} so'm · "
                    '${(p['barcodes'] as List).join(', ')}',
                  ),
                  trailing: Text('$stock ${p['unit']}'),
                  onTap: () => _open(p),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
