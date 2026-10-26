import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/numbers.dart';
import '../l10n/gen/app_localizations.dart';

/// Raqamli klaviatura, birlik ko'rsatkichi, vergul/nuqta. Bo'sh qoldirish mumkin (natija — NEEDS_REVIEW).
class NumberField extends StatelessWidget {
  const NumberField({
    super.key,
    required this.controller,
    required this.label,
    this.required = false,
    this.textInputAction = TextInputAction.next,
    this.onSubmitted,
    this.fieldKey,
  });
  final TextEditingController controller;
  final String label;
  final bool required;
  final TextInputAction textInputAction;
  final ValueChanged<String>? onSubmitted;
  final Key? fieldKey;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return TextFormField(
      key: fieldKey,
      controller: controller,
      decoration: InputDecoration(labelText: label),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))],
      textInputAction: textInputAction,
      onFieldSubmitted: onSubmitted,
      validator: (v) {
        if ((v ?? '').trim().isEmpty) return required ? l10n.requiredField : null;
        return parseDecimal(v) == null ? l10n.invalidNumber : null;
      },
    );
  }
}
