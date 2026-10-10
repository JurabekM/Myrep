import 'package:flutter/material.dart';

import '../app_session.dart';
import '../auth.dart';

/// Serversiz kirish: do'kon bo'lmasa yaratish yoki juftlash; bor bo'lsa login/parol.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

enum _Mode { choose, create, join, login }

class _LoginScreenState extends State<LoginScreen> {
  final _storeName = TextEditingController();
  final _ownerName = TextEditingController();
  final _login = TextEditingController();
  final _password = TextEditingController();
  final _password2 = TextEditingController();
  final _code = TextEditingController();
  late _Mode _mode;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.session.hasStore ? _Mode.login : _Mode.choose;
  }

  @override
  void dispose() {
    for (final c in [
      _storeName,
      _ownerName,
      _login,
      _password,
      _password2,
      _code,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on AuthException catch (e) {
      setState(() => _error = e.message);
    } on FormatException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submitLogin() async {
    if (_login.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = 'Login va parolni kiriting');
      return;
    }
    await _run(() => widget.session.login(_login.text, _password.text));
  }

  Future<void> _submitCreate() async {
    if ([_storeName, _ownerName, _login].any((c) => c.text.trim().isEmpty)) {
      setState(() => _error = "Hamma maydonlarni to'ldiring");
      return;
    }
    if (_password.text.length < 8) {
      setState(() => _error = "Parol kamida 8 belgi bo'lsin");
      return;
    }
    if (_password.text != _password2.text) {
      setState(() => _error = 'Parollar bir xil emas');
      return;
    }
    await _run(
      () => widget.session.createStore(
        storeName: _storeName.text.trim(),
        ownerName: _ownerName.text.trim(),
        login: _login.text,
        password: _password.text,
      ),
    );
  }

  Future<void> _submitJoin() async {
    parsePairingCode(_code.text); // avval formatni tekshiradi
    await _run(() => widget.session.joinStore(_code.text));
    if (!mounted) return;
    setState(() {
      _mode = _Mode.login;
      _error = "Do'kon qo'shildi. Ma'lumot kelishi uchun bir oz kuting, so'ng login qiling.";
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('OmborAI')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          switch (_mode) {
            _Mode.choose => _choose(),
            _Mode.create => _createForm(),
            _Mode.join => _joinForm(),
            _Mode.login => _loginForm(),
          },
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }

  Widget _choose() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const Text(
        "Do'kon hali yo'q. Yangi do'kon yarating yoki mavjud do'konga qo'shiling.",
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: () => setState(() {
          _mode = _Mode.create;
          _error = null;
        }),
        child: const Text("Yangi do'kon yaratish"),
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: () => setState(() {
          _mode = _Mode.join;
          _error = null;
        }),
        child: const Text("Do'konga qo'shilish (juftlash kodi)"),
      ),
    ],
  );

  Widget _createForm() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      TextField(
        controller: _storeName,
        decoration: const InputDecoration(labelText: "Do'kon nomi"),
      ),
      TextField(
        controller: _ownerName,
        decoration: const InputDecoration(labelText: 'Egasi ismi'),
      ),
      TextField(
        controller: _login,
        decoration: const InputDecoration(labelText: 'Login'),
      ),
      TextField(
        controller: _password,
        obscureText: true,
        decoration: const InputDecoration(labelText: 'Parol (kamida 8 belgi)'),
      ),
      TextField(
        controller: _password2,
        obscureText: true,
        decoration: const InputDecoration(labelText: 'Parolni takrorlang'),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _busy ? null : _submitCreate,
        child: const Text('Yaratish'),
      ),
      TextButton(
        onPressed: () => setState(() => _mode = _Mode.choose),
        child: const Text('Orqaga'),
      ),
    ],
  );

  Widget _joinForm() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      TextField(
        controller: _code,
        decoration: const InputDecoration(
          labelText: 'Juftlash kodi',
          hintText: "<do'kon ID>:<kalit>",
        ),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _busy ? null : _submitJoin,
        child: const Text("Qo'shilish"),
      ),
      TextButton(
        onPressed: () => setState(() => _mode = _Mode.choose),
        child: const Text('Orqaga'),
      ),
    ],
  );

  Widget _loginForm() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      TextField(
        controller: _login,
        decoration: const InputDecoration(labelText: 'Login'),
      ),
      TextField(
        controller: _password,
        obscureText: true,
        decoration: const InputDecoration(labelText: 'Parol'),
        onSubmitted: (_) => _submitLogin(),
      ),
      const SizedBox(height: 12),
      FilledButton(
        onPressed: _busy ? null : _submitLogin,
        child: const Text('Kirish'),
      ),
    ],
  );
}
