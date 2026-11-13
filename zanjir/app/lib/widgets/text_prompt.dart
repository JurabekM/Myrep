import 'package:flutter/material.dart';

import '../l10n/gen/app_localizations.dart';

/// Bitta matn maydonli dialog. Controller dialog vidjetining o'zida — yopilish animatsiyasi tugagach dispose qilinadi.
Future<String?> promptText(
  BuildContext context, {
  required String title,
  required String label,
  required String confirm,
  Key? fieldKey,
}) => showDialog<String>(
  context: context,
  builder: (_) => _TextPrompt(title: title, label: label, confirm: confirm, fieldKey: fieldKey),
);

class _TextPrompt extends StatefulWidget {
  const _TextPrompt({required this.title, required this.label, required this.confirm, this.fieldKey});
  final String title;
  final String label;
  final String confirm;
  final Key? fieldKey;

  @override
  State<_TextPrompt> createState() => _TextPromptState();
}

class _TextPromptState extends State<_TextPrompt> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(widget.title),
      content: TextField(
        key: widget.fieldKey,
        controller: _controller,
        decoration: InputDecoration(labelText: widget.label),
        autofocus: true,
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(onPressed: () => Navigator.pop(context, _controller.text.trim()), child: Text(widget.confirm)),
      ],
    );
  }
}
