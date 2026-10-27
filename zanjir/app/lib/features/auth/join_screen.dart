import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/disclaimer_banner.dart';

/// Taklif kodi bilan laboratoriyaga qo'shilish: foydalanuvchi, qurilma kaliti, serverdan barcha ma'lumot.
class JoinScreen extends ConsumerStatefulWidget {
  const JoinScreen({super.key});

  @override
  ConsumerState<JoinScreen> createState() => _JoinScreenState();
}

class _JoinScreenState extends ConsumerState<JoinScreen> {
  final _form = GlobalKey<FormState>();
  final _code = TextEditingController();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _repeat = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    for (final c in [_code, _name, _phone, _password, _repeat]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _join() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(profileProvider.notifier)
          .join(
            code: _code.text.trim().toUpperCase(),
            fullName: _name.text.trim(),
            phone: _phone.text.trim(),
            password: _password.text,
          );
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
    String? required(String? v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.joinTitle)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              key: const Key('join.code'),
              controller: _code,
              decoration: InputDecoration(labelText: l10n.inviteCode),
              textCapitalization: TextCapitalization.characters,
              validator: (v) => (v ?? '').trim().length == 16 ? null : l10n.invalidInvite,
            ),
            TextFormField(
              key: const Key('join.name'),
              controller: _name,
              decoration: InputDecoration(labelText: l10n.fullName),
              validator: required,
            ),
            TextFormField(
              key: const Key('join.phone'),
              controller: _phone,
              decoration: InputDecoration(labelText: l10n.phone),
              keyboardType: TextInputType.phone,
              validator: required,
            ),
            TextFormField(
              key: const Key('join.password'),
              controller: _password,
              decoration: InputDecoration(labelText: l10n.password),
              obscureText: true,
              validator: (v) => (v ?? '').length >= 10 ? null : l10n.passwordTooShort,
            ),
            TextFormField(
              key: const Key('join.repeat'),
              controller: _repeat,
              decoration: InputDecoration(labelText: l10n.passwordRepeat),
              obscureText: true,
              validator: (v) => v == _password.text ? null : l10n.passwordMismatch,
            ),
            const SizedBox(height: 16),
            FilledButton(key: const Key('join.submit'), onPressed: _busy ? null : _join, child: Text(l10n.joinButton)),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(
                _error!,
                key: const Key('join.error'),
                style: const TextStyle(color: ZanjirColors.danger),
              ),
            ],
          ],
        ),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
