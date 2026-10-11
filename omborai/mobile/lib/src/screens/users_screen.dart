import 'package:flutter/material.dart';

import '../app_session.dart';
import '../auth.dart';
import '../sync/ops.dart' as ops;
import '../theme.dart';

/// Foydalanuvchilar va qurilmalar (faqat egasi qurilmasi va egasi hisobi): tasdiq, bloklash, kassirlar.
class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

const _roleNames = {'owner': 'Egasi', 'cashier': 'Kassir'};

class _UsersScreenState extends State<UsersScreen> {
  List<Map<String, dynamic>> _users = const [];
  List<Map<String, dynamic>> _devices = const [];

  @override
  void initState() {
    super.initState();
    widget.session.addListener(_reload);
    _reload();
  }

  @override
  void dispose() {
    widget.session.removeListener(_reload);
    super.dispose();
  }

  Future<void> _reload() async {
    try {
      final users = await widget.session.users();
      final devices = await widget.session.devices();
      if (!mounted) return;
      setState(() {
        _users = users;
        _devices = devices;
      });
    } on AuthException catch (e) {
      _showError(e);
    }
  }

  void _showError(Object e) {
    if (!mounted) return;
    final text = e is AuthException ? e.message : '$e';
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _run(Future<void> Function() action) async {
    try {
      await action();
      await _reload();
    } on Object catch (e) {
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
    final requests = widget.session.joinRequests;
    return Scaffold(
      appBar: AppBar(title: const Text('Foydalanuvchilar va qurilmalar')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addCashier,
        icon: const Icon(Icons.person_add_alt_1),
        label: const Text("Kassir qo'shish"),
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 96),
        children: [
          _Section(title: 'Tasdiq kutayotgan qurilmalar (${requests.length})'),
          if (requests.isEmpty)
            const ListTile(
              title: Text("Yangi so'rov yo'q"),
              subtitle: Text("Qurilma juftlash kodi bilan so'raganda shu yerda ko'rinadi"),
            ),
          for (final request in requests)
            _JoinRequestTile(
              request: request,
              onApprove: (role) => _run(
                () => widget.session.approveJoin(request, role: role),
              ),
              onReject: () {
                widget.session.rejectJoin(request);
                setState(() {});
              },
            ),
          const Divider(height: 24),
          const _Section(title: 'Qurilmalar'),
          for (final d in _devices)
            _DeviceTile(
              device: d,
              onActive: (v) => _run(
                () => widget.session.setDeviceState(d['device_id'] as String, active: v),
              ),
              onRole: () => _run(
                () => widget.session.setDeviceState(
                  d['device_id'] as String,
                  role: d['role'] == ops.roleCashier ? ops.roleOwner : ops.roleCashier,
                ),
              ),
            ),
          const Divider(height: 24),
          const _Section(title: 'Foydalanuvchilar (kassirlar)'),
          for (final u in _users)
            SwitchListTile(
              title: Text(u['name'] as String),
              subtitle: Text('${u['login']} · ${_roleNames[u['role']] ?? u['role']}'),
              value: u['active'] == true,
              onChanged: u['role'] == 'owner'
                  ? null
                  : (v) => _run(() => widget.session.setUserActive(u['id'] as String, active: v)),
            ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(title, style: const TextStyle(color: kMuted, fontWeight: FontWeight.w600)),
    );
  }
}

class _JoinRequestTile extends StatelessWidget {
  const _JoinRequestTile({
    required this.request,
    required this.onApprove,
    required this.onReject,
  });

  final Map<String, dynamic> request;
  final void Function(String role) onApprove;
  final VoidCallback onReject;

  @override
  Widget build(BuildContext context) {
    final payload = request['payload'] as Map<String, dynamic>;
    final label = (payload['label'] ?? '').toString();
    return ListTile(
      leading: const Icon(Icons.devices_other),
      title: Text(label.isEmpty ? 'Yangi qurilma' : label),
      subtitle: Text('ID: ${(payload['device_id'] as String).substring(0, 8)}'),
      trailing: Wrap(
        spacing: 4,
        children: [
          TextButton(onPressed: () => onApprove(ops.roleCashier), child: const Text('Kassir')),
          TextButton(onPressed: () => onApprove(ops.roleOwner), child: const Text('Egasi')),
          TextButton(onPressed: onReject, child: const Text('Rad')),
        ],
      ),
    );
  }
}

class _DeviceTile extends StatelessWidget {
  const _DeviceTile({required this.device, required this.onActive, required this.onRole});

  final Map<String, dynamic> device;
  final void Function(bool active) onActive;
  final VoidCallback onRole;

  @override
  Widget build(BuildContext context) {
    final isOwner = device['role'] == ops.roleOwner;
    final active = device['active'] == true;
    return ListTile(
      leading: Icon(
        isOwner ? Icons.admin_panel_settings_outlined : Icons.point_of_sale,
        color: active ? kSuccess : kDanger,
      ),
      title: Text((device['label'] ?? '').toString().isEmpty ? 'Qurilma' : device['label'] as String),
      subtitle: Text(
        '${_roleNames[device['role']] ?? device['role']} · '
        '${active ? 'faol' : 'bloklangan'} · ${(device['device_id'] as String).substring(0, 8)}',
      ),
      trailing: isOwner
          ? const Text('egasi', style: TextStyle(color: kMuted))
          : Wrap(
              spacing: 4,
              children: [
                IconButton(
                  tooltip: 'Rolni almashtirish',
                  onPressed: onRole,
                  icon: const Icon(Icons.swap_horiz),
                ),
                Switch(value: active, onChanged: onActive),
              ],
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
