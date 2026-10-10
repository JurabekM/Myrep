import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';

import '../api/api_client.dart';
import '../app_session.dart';
import '../money.dart';
import 'login_screen.dart';
import 'products_screen.dart';
import 'sale_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Map<String, dynamic>>? _low;
  String? _lowError;

  @override
  void initState() {
    super.initState();
    widget.session.addListener(_onChanged);
    _loadLow();
  }

  @override
  void dispose() {
    widget.session.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _loadLow() async {
    final session = widget.session;
    if (!session.hasStore) return;
    try {
      final rows = await session.api.balances(session.storeId, lowOnly: true);
      if (mounted) setState(() => _low = rows);
    } on OfflineException {
      if (mounted) {
        setState(
          () => _lowError = "Offline: ro'yxat aloqa tiklanganda yangilanadi",
        );
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _lowError = e.message);
    }
  }

  Future<void> _sync() async {
    await widget.session.syncNow();
    await _loadLow();
  }

  Future<void> _toggleShift() async {
    final session = widget.session;
    final cash = await _askCash(
      context,
      session.shiftOpen
          ? 'Kassadagi haqiqiy naqd (so\'m)'
          : 'Boshlang\'ich naqd (so\'m)',
      session.shiftOpen ? 'Smenani yopish' : 'Smena ochish',
    );
    if (cash == null) return;
    try {
      if (session.shiftOpen) {
        final summary = await session.closeShift(cash);
        if (!mounted) return;
        await showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Smena yopildi'),
            content: Text(
              'Savdolar: ${summary['sales_count']} ta, ${formatSom(summary['total_sales'] as int)} so\'m\n'
              'Kutilgan naqd: ${formatSom(summary['expected_cash'] as int)} so\'m\n'
              'Farq: ${formatSom((summary['difference'] as int?) ?? 0)} so\'m',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Yopish'),
              ),
            ],
          ),
        );
      } else {
        await session.openShift(cash);
      }
    } on ApiException catch (e) {
      _showError(e.message);
    } on OfflineException {
      _showError("Smena faqat internet bilan ochiladi/yopiladi");
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _logout() async {
    await widget.session.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => LoginScreen(session: widget.session)),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.session;
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(session.storeName ?? 'OmborAI'),
        actions: [
          IconButton(
            tooltip: 'Sinxronizatsiya',
            onPressed: session.syncing ? null : _sync,
            icon: session.syncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(
                    session.online
                        ? Icons.cloud_done_outlined
                        : Icons.cloud_off_outlined,
                  ),
          ),
          IconButton(
            tooltip: 'Chiqish',
            onPressed: _logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _sync,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: ListTile(
                leading: Icon(
                  session.shiftOpen ? Icons.point_of_sale : Icons.lock_clock,
                  color: session.shiftOpen ? Colors.green : scheme.error,
                ),
                title: Text(session.shiftOpen ? 'Smena ochiq' : 'Smena yopiq'),
                subtitle: Text(
                  session.online
                      ? 'Server bilan aloqa bor'
                      : "Offline — savdo navbatga tushadi",
                ),
                trailing: OutlinedButton(
                  onPressed: session.online || session.shiftOpen
                      ? _toggleShift
                      : null,
                  child: Text(session.shiftOpen ? 'Yopish' : 'Ochish'),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Card(
              child: ListTile(
                leading: Icon(
                  session.pending > 0
                      ? Icons.schedule
                      : Icons.check_circle_outline,
                  color: session.pending > 0 ? scheme.tertiary : Colors.green,
                ),
                title: Text(
                  session.pending > 0
                      ? 'Navbatda: ${session.pending} ta savdo'
                      : 'Hammasi sinxronlangan',
                ),
                subtitle: Text(
                  [
                    if (session.lastSync != null)
                      'Oxirgi sinxron: ${session.lastSync!.hour.toString().padLeft(2, '0')}:'
                          '${session.lastSync!.minute.toString().padLeft(2, '0')}',
                    if (session.rejected > 0)
                      'Rad etilgan: ${session.rejected}',
                    if (session.lastMessage != null) session.lastMessage!,
                  ].join(' · '),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: session.hasStore
                        ? () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => SaleScreen(session: session),
                            ),
                          )
                        : null,
                    icon: const Icon(Icons.shopping_cart_checkout),
                    label: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text('Kassa'),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: session.hasStore
                        ? () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => ProductsScreen(session: session),
                            ),
                          )
                        : null,
                    icon: const Icon(Icons.inventory_2_outlined),
                    label: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text('Tovarlar'),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Text(
              'Kam qolgan tovarlar',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (_lowError != null)
              Text(_lowError!, style: TextStyle(color: scheme.outline)),
            if (_low != null && _low!.isEmpty) const Text('Hammasi yetarli'),
            for (final row in _low ?? const <Map<String, dynamic>>[])
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(row['name'] as String),
                subtitle: Text('Minimal: ${row['min_stock']} ${row['unit']}'),
                trailing: Text(
                  '${formatQty(Decimal.parse('${row['qty']}'))} ${row['unit']}',
                  style: TextStyle(
                    color: scheme.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

Future<int?> _askCash(BuildContext context, String label, String title) async {
  final controller = TextEditingController(text: '0');
  final result = await showDialog<int>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: controller,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(labelText: label),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Bekor'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(
            ctx,
            int.tryParse(controller.text.replaceAll(' ', '')),
          ),
          child: const Text('Tasdiqlash'),
        ),
      ],
    ),
  );
  controller.dispose();
  return result;
}
