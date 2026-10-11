import 'package:flutter/material.dart';

import '../app_session.dart';
import '../money.dart';

/// Oxirgi cheklar. Tugmani bosib, chekni qaytarish (MQTT 'refund' operatsiyasi).
class RefundsScreen extends StatefulWidget {
  const RefundsScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<RefundsScreen> createState() => _RefundsScreenState();
}

class _RefundsScreenState extends State<RefundsScreen> {
  List<Map<String, dynamic>> _sales = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final rows = await widget.session.db.sales(widget.session.storeId);
    if (mounted) setState(() => _sales = rows);
  }

  Future<void> _refund(Map<String, dynamic> sale) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Chek #${sale['number']} ni qaytarish'),
        content: Text(
          "${formatSom(sale['total'] as int)} so'm qaytariladi. Tasdiqlaysizmi?",
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Yo\'q'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Ha, qaytarish'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.session.refund(sale['id'] as String);
    } on StateError catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Qaytarish')),
      body: ListView.separated(
        itemCount: _sales.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final sale = _sales[index];
          final refunded = sale['status'] == 'refunded';
          return ListTile(
            title: Text('Chek #${sale['number']}'),
            subtitle: Text(
              '${formatSom(sale['total'] as int)} so\'m · ${refunded ? 'qaytarilgan' : 'to\'langan'}',
            ),
            trailing: refunded
                ? const Icon(Icons.undo, color: Colors.grey)
                : TextButton(
                    onPressed: () => _refund(sale),
                    child: const Text('Qaytarish'),
                  ),
          );
        },
      ),
    );
  }
}
