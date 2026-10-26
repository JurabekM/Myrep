import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../widgets/disclaimer_banner.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _form = GlobalKey<FormState>();
  AuthResult? _result;
  bool _busy = false;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final r = await ref.read(authGatewayProvider).login(phone: _phone.text.trim(), password: _password.text);
    if (mounted) {
      setState(() {
        _result = r;
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.loginTitle)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _phone,
              decoration: InputDecoration(labelText: l10n.phone),
              keyboardType: TextInputType.phone,
              autofillHints: const [AutofillHints.telephoneNumber],
              validator: (v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _password,
              decoration: InputDecoration(labelText: l10n.password),
              obscureText: true,
              autofillHints: const [AutofillHints.password],
              validator: (v) => (v ?? '').isEmpty ? l10n.requiredField : null,
            ),
            const SizedBox(height: 16),
            FilledButton(onPressed: _busy ? null : _login, child: Text(l10n.loginButton)),
            if (_result == AuthResult.serverUnavailable) ...[const SizedBox(height: 16), Text(l10n.serverUnavailable)],
            const SizedBox(height: 24),
            OutlinedButton(onPressed: () => context.go('/onboarding'), child: Text(l10n.createOfflineProfile)),
          ],
        ),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
