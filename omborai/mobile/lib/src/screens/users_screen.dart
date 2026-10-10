import 'package:flutter/material.dart';

import '../app_session.dart';
import '../auth.dart';

/// Foydalanuvchilar (faqat do'kon egasi): ro'yxat, kassir qo'shish, faollashtirish/o'chirish.
class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

const _roleNames = {'owner': 'Egasi', 'cashier': 'Kassir'};

class _UsersScreenState extends State<UsersScreen> {
  List<Map<String, dynamic>> _users = const [];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final users = await widget.session.users();
    if (!mounted) return;
    setState(() => _users = users);
  }

  void _showError(Object e) {
    final text = e is AuthException ? e.message : '$e';
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _toggle(Map<String, dynamic> user, bool active) async {
    try {
      await widget.session.setUserActive(user['id'] as String, active: active);
      await _reload();
    } on AuthException catch (e) {
      _showError(e);
    }
  }

  Future<void> _addCashier() async {
    final added = await showDialog<bool>(
      context: context,
      builder: (_) => _AddCashierDialog(session: widget.session),
    );
    if (added == true) await _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Foydalanuvchilar')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addCashier,
        icon: const Icon(Icons.person_add_alt_1),
        label: const Text("Kassir qo'shish"),
      ),
      body: ListView.separated(
        itemCount: _users.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, i) {
          final u = _users[i];
          final isOwner = u['role'] == 'owner';
          return SwitchListTile(
            title: Text(u['name'] as String),
            subtitle: Text(
              '${u['login']} · ${_roleNames[u['role']] ?? u['role']}',
            ),
            value: u['active'] == 1,
            onChanged: isOwner ? null : (v) => _toggle(u, v),
          );
        },
      ),
    );
  }
}

class _AddCashierDialog extends StatefulWidget {
  const _AddCashierDialog({required this.session});

  final AppSession session;

  @override
  State<_AddCashierDialog> createState() => _AddCashierDialogState();
}

class _AddCashierDialogState extends State<_AddCashierDialog> {
  final _name = TextEditingController();
  final _login = TextEditingController();
  final _password = TextEditingController();
  final _password2 = TextEditingController();
  String? _error;

  @override
  void dispose() {
    for (final c in [_name, _login, _password, _password2]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_password.text != _password2.text) {
      setState(() => _error = 'Parollar bir xil emas');
      return;
    }
    try {
      await widget.session.addCashier(
        name: _name.text,
        login: _login.text,
        password: _password.text,
      );
      if (mounted) Navigator.pop(context, true);
    } on AuthException catch (e) {
      setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text("Kassir qo'shish"),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _name,
              decoration: const InputDecoration(labelText: 'Ism'),
            ),
            TextField(
              controller: _login,
              decoration: const InputDecoration(labelText: 'Login'),
            ),
            TextField(
              controller: _password,
              obscureText: true,
              decoration: InputDecoration(
                labelText: 'Parol (kamida $minPasswordLength belgi)',
              ),
            ),
            TextField(
              controller: _password2,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Parolni takrorlang',
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Bekor qilish'),
        ),
        FilledButton(onPressed: _submit, child: const Text("Qo'shish")),
      ],
    );
  }
}
