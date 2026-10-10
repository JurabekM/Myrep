import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../app_session.dart';
import '../money.dart';
import 'scanner_screen.dart';

class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  final _query = TextEditingController();
  List<Map<String, dynamic>> _items = const [];
  String? _message;

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<void> _search(String text) async {
    final session = widget.session;
    try {
      final items = await session.api.searchProducts(text, session.storeId);
      if (mounted) {
        setState(() {
          _items = items;
          _message = null;
        });
      }
    } on OfflineException {
      final items = await session.db.searchProducts(text, session.storeId);
      if (mounted) {
        setState(() {
          _items = items;
          _message = 'Offline: mahalliy kesh';
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _message = e.message);
    }
  }

  Future<void> _scan() async {
    final code = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const ScannerScreen()),
    );
    if (code == null || code.isEmpty) return;
    _query.text = code;
    await _search(code);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tovarlar')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _query,
                    onChanged: _search,
                    decoration: const InputDecoration(
                      hintText: 'Nom yoki shtrix-kod',
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filledTonal(
                  tooltip: 'Skanerlash',
                  onPressed: _scan,
                  icon: const Icon(Icons.qr_code_scanner),
                ),
              ],
            ),
          ),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(_message!),
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
                    '${formatSom((p['sale_price'] as num).toInt())} so\'m',
                  ),
                  trailing: Text('$stock ${p['unit']}'),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
