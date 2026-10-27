import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/disclaimer_banner.dart';

/// Serverga kirish (telefon + parol). Server sozlanmagan bo'lsa — oflayn profil yoki keyinroq ulanish.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _form = GlobalKey<FormState>();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(profileProvider.notifier).login(phone: _phone.text.trim(), password: _password.text);
      if (mounted) context.go('/');
    } catch (e) {
      if (mounted) setState(() => _error = l10n.serverErrorText(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final configured = ref.watch(serverApiProvider) != null;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.loginTitle)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (!configured)
              Text(l10n.serverNotConfigured, key: const Key('login.notConfigured'))
            else ...[
              TextFormField(
                key: const Key('login.phone'),
                controller: _phone,
                decoration: InputDecoration(labelText: l10n.phone),
                keyboardType: TextInputType.phone,
                autofillHints: const [AutofillHints.telephoneNumber],
                validator: (v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                key: const Key('login.password'),
                controller: _password,
                decoration: InputDecoration(labelText: l10n.password),
                obscureText: true,
                autofillHints: const [AutofillHints.password],
                validator: (v) => (v ?? '').isEmpty ? l10n.requiredField : null,
              ),
              const SizedBox(height: 16),
              FilledButton(
                key: const Key('login.submit'),
                onPressed: _busy ? null : _login,
                child: Text(l10n.loginButton),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(
                  _error!,
                  key: const Key('login.error'),
                  style: const TextStyle(color: ZanjirColors.danger),
                ),
              ],
              const SizedBox(height: 12),
              OutlinedButton(
                key: const Key('login.join'),
                onPressed: () => context.go('/join'),
                child: Text(l10n.joinWithInvite),
              ),
            ],
            const SizedBox(height: 24),
            OutlinedButton(onPressed: () => context.go('/onboarding'), child: Text(l10n.createOfflineProfile)),
          ],
        ),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
