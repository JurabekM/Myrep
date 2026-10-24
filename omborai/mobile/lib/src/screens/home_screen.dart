import 'package:flutter/material.dart';

import '../app_session.dart';
import '../money.dart';
import 'login_screen.dart';
import 'pairing_screen.dart';
import 'products_screen.dart';
import 'refunds_screen.dart';
import 'users_screen.dart';
import 'sale_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    widget.session.addListener(_onChanged);
  }

  @override
  void dispose() {
    widget.session.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  void _toast(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _toggleShift() async {
    final session = widget.session;
    final cash = await _askCash(
      context,
      session.shiftOpen
          ? "Kassadagi haqiqiy naqd (so'm)"
          : "Boshlang'ich naqd (so'm)",
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
              'Qaytarishlar: ${summary['refunds_count']} ta\n'
              'Farq: ${formatSom(cash - (summary['opening_cash'] as int) - ((summary['by_method'] as Map)['cash'] as int? ?? 0))} so\'m',
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
    } on StateError catch (e) {
      _toast(e.message);
    }
  }

  Future<void> _logout() async {
    await widget.session.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => LoginScreen(session: widget.session)),
      (_) => false,
    );
  }

  void _open(Widget screen) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => screen));
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
            tooltip: 'Juftlash (kalit)',
            onPressed: () => _open(PairingScreen(session: session)),
            icon: const Icon(Icons.key_outlined),
          ),
          IconButton(
            tooltip: session.connected ? 'MQTT ulangan' : 'MQTT uzilgan',
            onPressed: null,
            icon: Icon(
              session.connected
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
      body: ListView(
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
                session.connected
                    ? "Savdo qabul qilinadi"
                    : "Offline: savdo navbatga tushadi",
              ),
              trailing: OutlinedButton(
                onPressed: _toggleShift,
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
                    ? 'Navbatda: ${session.pending} ta operatsiya'
                    : 'Hammasi yuborilgan',
              ),
              subtitle: session.lastMessage == null
                  ? null
                  : Text(session.lastMessage!),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: session.hasStore && session.shiftOpen
                ? () => _open(SaleScreen(session: session))
                : null,
            icon: const Icon(Icons.shopping_cart_checkout),
            label: const Padding(
              padding: EdgeInsets.symmetric(vertical: 14),
              child: Text('Kassa'),
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: session.hasStore
                ? () => _open(ProductsScreen(session: session))
                : null,
            icon: const Icon(Icons.inventory_2_outlined),
            label: const Padding(
              padding: EdgeInsets.symmetric(vertical: 14),
              child: Text('Tovarlar'),
            ),
          ),
          if (session.isOwner) ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _open(UsersScreen(session: session)),
              icon: const Icon(Icons.people_outline),
              label: const Padding(
                padding: EdgeInsets.symmetric(vertical: 14),
                child: Text('Foydalanuvchilar'),
              ),
            ),
          ],
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: session.hasStore
                ? () => _open(RefundsScreen(session: session))
                : null,
            icon: const Icon(Icons.undo),
            label: const Padding(
              padding: EdgeInsets.symmetric(vertical: 14),
              child: Text('Qaytarish'),
            ),
          ),
        ],
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
