import 'package:flutter/material.dart';

import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';

/// Reja holati: rang + matn (faqat rangga tayanmaydi).
class PlanStatusChip extends StatelessWidget {
  const PlanStatusChip(this.status, {super.key});
  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'APPROVED' => ZanjirColors.accentText,
      'EXECUTED' => ZanjirColors.success,
      'STALE' || 'CANCELLED' => ZanjirColors.danger,
      _ => ZanjirColors.inkMuted,
    };
    return Chip(
      label: Text(AppLocalizations.of(context).planStatusName(status), style: TextStyle(color: color)),
      side: BorderSide(color: color),
    );
  }
}
