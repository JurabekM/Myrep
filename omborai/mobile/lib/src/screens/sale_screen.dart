import 'package:decimal/decimal.dart';
import 'package:flutter/material.dart';

import '../app_session.dart';
import '../domain/cart.dart';
import '../money.dart';
import 'scanner_screen.dart';

const _methods = {
  'cash': 'Naqd',
  'card': 'Karta',
  'click': 'Click',
  'payme': 'Payme',
};

/// Mobil kassa. Savdo MQTT orqali; aloqa bo'lmasa navbatga tushadi.
class SaleScreen extends StatefulWidget {
  const SaleScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<SaleScreen> createState() => _SaleScreenState();
}

class _SaleScreenState extends State<SaleScreen> {
  final _cart = Cart();
  final _query = TextEditingController();
  List<Map<String, dynamic>> _results = const [];
  String _method = 'cash';
  bool _busy = false;

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  void _toast(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _search(String text) async {
    final db = widget.session.db;
    final storeId = widget.session.storeId;
    final isCode = text.length >= 4 && int.tryParse(text) != null;
    if (isCode) {
      final product = await db.productByBarcode(text, storeId);
      if (product != null) {
        _add(product);
        _query.clear();
        setState(() => _results = const []);
      } else {
        _toast('Tovar topilmadi: $text');
      }
      return;
    }
    final found = await db.searchProducts(text, storeId);
    if (mounted) setState(() => _results = found);
  }

  void _add(Map<String, dynamic> product) {
    setState(() => _cart.add(product));
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

  Future<void> _pay() async {
    if (_cart.isEmpty || _busy) return;
    setState(() => _busy = true);
    try {
      final payload = await widget.session.submitSale(_cart, _method);
      setState(_cart.clear);
      _toast('Chek #${payload['number']} saqlandi');
    } on StateError catch (e) {
      _toast(e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Kassa')),
      body: Column(
        children: [
          if (!widget.session.connected)
            Container(
              width: double.infinity,
              color: scheme.tertiaryContainer,
              padding: const EdgeInsets.all(8),
              child: const Text(
                "Offline: savdolar aloqa tiklanganda yuboriladi",
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _query,
                    autofocus: true,
                    onSubmitted: _search,
                    onChanged: (t) => _search(t),
                    decoration: const InputDecoration(
                      hintText: 'Shtrix-kod yoki nom',
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filledTonal(
                  onPressed: _scan,
                  icon: const Icon(Icons.qr_code_scanner),
                ),
              ],
            ),
          ),
          if (_results.isNotEmpty)
            SizedBox(
              height: 150,
              child: ListView(
                children: [
                  for (final p in _results)
                    ListTile(
                      dense: true,
                      title: Text(p['name'] as String),
                      subtitle: Text(
                        "${formatSom((p['sale_price'] as num).toInt())} so'm · "
                        '${formatQty(Decimal.parse('${p['stock_qty']}'))} ${p['unit']}',
                      ),
                      onTap: () {
                        _add(p);
                        _query.clear();
                        setState(() => _results = const []);
                      },
                    ),
                ],
              ),
            ),
          const Divider(height: 1),
          Expanded(
            child: _cart.isEmpty
                ? const Center(
                    child: Text(
                      "Savat bo'sh. Tovarni skanerlang yoki tanlang.",
                    ),
                  )
                : ListView(
                    children: [
                      for (final line in _cart.lines)
                        ListTile(
                          title: Text(line.name),
                          subtitle: Text(
                            "${formatSom(line.unitPrice)} so'm × ${formatQty(line.qty)} ${line.unit}",
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                onPressed: () => setState(
                                  () => _cart.setQty(
                                    line.productId,
                                    line.qty - Decimal.one,
                                  ),
                                ),
                                icon: const Icon(Icons.remove_circle_outline),
                              ),
                              IconButton(
                                onPressed: () => setState(
                                  () => _cart.setQty(
                                    line.productId,
                                    line.qty + Decimal.one,
                                  ),
                                ),
                                icon: const Icon(Icons.add_circle_outline),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Jami', style: TextStyle(fontSize: 18)),
                      Text(
                        "${formatSom(_cart.total)} so'm",
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Fiskal chek: ishlab chiqish jarayonida',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 8),
                  SegmentedButton<String>(
                    segments: [
                      for (final e in _methods.entries)
                        ButtonSegment(value: e.key, label: Text(e.value)),
                    ],
                    selected: {_method},
                    onSelectionChanged: (s) =>
                        setState(() => _method = s.first),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _cart.isEmpty || _busy ? null : _pay,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(56),
                    ),
                    child: _busy
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text("To'lash", style: TextStyle(fontSize: 18)),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
