import 'dart:async';

import 'package:flutter/material.dart';
import 'package:zanjir_data/zanjir_data.dart' show backupPasswordMinLength;

import '../l10n/gen/app_localizations.dart';

/// Zaxira paroli. [confirmRepeat] — yangi parol (ikki marta, kamida [backupPasswordMinLength] belgi); aks holda — bitta
/// maydon (tiklash). Parol hech qayerda saqlanmaydi va logga yozilmaydi.
Future<String?> promptPassword(
  BuildContext context, {
  required String title,
  required String confirm,
  String? message,
  bool confirmRepeat = false,
}) => showDialog<String>(
  context: context,
  builder: (_) => _PasswordPrompt(title: title, confirm: confirm, message: message, confirmRepeat: confirmRepeat),
);

class _PasswordPrompt extends StatefulWidget {
  const _PasswordPrompt({required this.title, required this.confirm, required this.confirmRepeat, this.message});
  final String title;
  final String confirm;
  final String? message;
  final bool confirmRepeat;

  @override
  State<_PasswordPrompt> createState() => _PasswordPromptState();
}

class _PasswordPromptState extends State<_PasswordPrompt> {
  final _form = GlobalKey<FormState>();
  final _password = TextEditingController();
  final _repeat = TextEditingController();

  @override
  void dispose() {
    _password.dispose();
    _repeat.dispose();
    super.dispose();
  }

  void _submit() {
    if (_form.currentState!.validate()) Navigator.pop(context, _password.text);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(widget.title),
      content: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.message != null) ...[Text(widget.message!), const SizedBox(height: 12)],
              TextFormField(
                key: const Key('password.value'),
                controller: _password,
                decoration: InputDecoration(labelText: l10n.password),
                obscureText: true,
                enableSuggestions: false,
                autocorrect: false,
                autofocus: true,
                onFieldSubmitted: widget.confirmRepeat ? null : (_) => _submit(),
                validator: (v) {
                  if ((v ?? '').isEmpty) return l10n.requiredField;
                  if (widget.confirmRepeat && v!.length < backupPasswordMinLength) return l10n.passwordTooShort;
                  return null;
                },
              ),
              if (widget.confirmRepeat)
                TextFormField(
                  key: const Key('password.repeat'),
                  controller: _repeat,
                  decoration: InputDecoration(labelText: l10n.passwordRepeat),
                  obscureText: true,
                  enableSuggestions: false,
                  autocorrect: false,
                  validator: (v) => v == _password.text ? null : l10n.passwordMismatch,
                  onFieldSubmitted: (_) => _submit(),
                ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(key: const Key('password.confirm'), onPressed: _submit, child: Text(widget.confirm)),
      ],
    );
  }
}

/// Uzoq amal (Argon2id, nusxalash) davomida yopib bo'lmaydigan kutish oynasi; [work] tugagach aynan shu oyna olib
/// tashlanadi (tiklashdan keyin router sahifani almashtirgan bo'lsa ham boshqa sahifa yopilmaydi).
Future<T> withProgress<T>(BuildContext context, String message, Future<T> Function() work) async {
  final navigator = Navigator.of(context, rootNavigator: true);
  final route = DialogRoute<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) => PopScope(
      canPop: false,
      child: AlertDialog(
        content: Row(
          children: [
            const CircularProgressIndicator(),
            const SizedBox(width: 16),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    ),
  );
  unawaited(navigator.push(route));
  try {
    return await work();
  } finally {
    if (route.isActive) navigator.removeRoute(route);
  }
}
