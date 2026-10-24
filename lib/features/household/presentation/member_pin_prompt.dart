import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Oilaviy rozilik: a'zoning shaxsiy PIN'ini so'rash (havas chegarasi,
/// marosim muhokamasi). Bekor qilinsa — `null`.
Future<String?> showMemberPinPrompt(
  BuildContext context, {
  required String name,
  required String okLabel,
}) => showDialog<String>(
  context: context,
  builder: (_) => _MemberPinDialog(name: name, okLabel: okLabel),
);

class _MemberPinDialog extends StatefulWidget {
  const _MemberPinDialog({required this.name, required this.okLabel});

  final String name;
  final String okLabel;

  @override
  State<_MemberPinDialog> createState() => _MemberPinDialogState();
}

class _MemberPinDialogState extends State<_MemberPinDialog> {
  final _pin = TextEditingController();

  @override
  void dispose() {
    _pin.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.memberPinPrompt(widget.name)),
      content: TextField(
        key: const Key('member-pin-field'),
        controller: _pin,
        autofocus: true,
        obscureText: true,
        keyboardType: TextInputType.number,
        maxLength: 6,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('member-pin-ok'),
          onPressed: () => Navigator.pop(context, _pin.text),
          child: Text(widget.okLabel),
        ),
      ],
    );
  }
}
