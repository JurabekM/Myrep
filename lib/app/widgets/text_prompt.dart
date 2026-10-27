import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:flutter/material.dart';

/// Bitta matn maydonli oyna. Natija — kiritilgan matn (bekor qilinsa
/// `null`).
///
/// `TextEditingController` oyna holatiga tegishli: `showDialog` qaytgandan
/// keyin ham yopilish animatsiyasi maydonni chizadi, shuning uchun uni
/// chaqiruvchi tomonda darhol `dispose` qilib bo'lmaydi.
Future<String?> showTextPrompt(
  BuildContext context, {
  required String title,
  required String label,
  Key? fieldKey,
  Key? okKey,
  String initial = '',
  TextInputType? keyboardType,
}) => showDialog<String>(
  context: context,
  builder: (_) => _TextPrompt(
    title: title,
    label: label,
    fieldKey: fieldKey,
    okKey: okKey,
    initial: initial,
    keyboardType: keyboardType,
  ),
);

class _TextPrompt extends StatefulWidget {
  const _TextPrompt({
    required this.title,
    required this.label,
    required this.initial,
    this.fieldKey,
    this.okKey,
    this.keyboardType,
  });

  final String title;
  final String label;
  final String initial;
  final Key? fieldKey;
  final Key? okKey;
  final TextInputType? keyboardType;

  @override
  State<_TextPrompt> createState() => _TextPromptState();
}

class _TextPromptState extends State<_TextPrompt> {
  late final _controller = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(widget.title),
      content: TextField(
        key: widget.fieldKey,
        controller: _controller,
        autofocus: true,
        keyboardType: widget.keyboardType,
        decoration: InputDecoration(labelText: widget.label),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: widget.okKey,
          onPressed: () => Navigator.pop(context, _controller.text),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}
