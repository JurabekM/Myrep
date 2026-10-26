import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/profile.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';

/// Oflayn laboratoriya profili: yaratuvchi — ish rahbari yoki administrator.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _form = GlobalKey<FormState>();
  final _lab = TextEditingController();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  String _role = ProfileService.creatorRoles.first;
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    for (final c in [_lab, _name, _phone]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _create() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(profileProvider.notifier)
          .create(labName: _lab.text.trim(), fullName: _name.text.trim(), phone: _phone.text.trim(), role: _role);
      if (mounted) context.go('/');
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e;
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? required(String? v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.onboardingTitle)),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(l10n.onboardingHint),
            const SizedBox(height: 16),
            TextFormField(
              key: const Key('onboarding.lab'),
              controller: _lab,
              decoration: InputDecoration(labelText: l10n.labName),
              validator: required,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('onboarding.name'),
              controller: _name,
              decoration: InputDecoration(labelText: l10n.fullName),
              validator: required,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('onboarding.phone'),
              controller: _phone,
              decoration: InputDecoration(labelText: l10n.phone),
              keyboardType: TextInputType.phone,
              validator: required,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              isExpanded: true,
              initialValue: _role,
              decoration: InputDecoration(labelText: l10n.role),
              items: [
                for (final r in ProfileService.creatorRoles) DropdownMenuItem(value: r, child: Text(l10n.roleName(r))),
              ],
              onChanged: (v) => setState(() => _role = v!),
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: const Key('onboarding.create'),
              onPressed: _busy ? null : _create,
              child: Text(l10n.onboardingCreate),
            ),
            if (_error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(l10n.errorText(_error!))),
          ],
        ),
      ),
    );
  }
}
