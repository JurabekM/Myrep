import 'package:flutter/material.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../l10n/gen/app_localizations.dart';
import '../l10n/labels.dart';
import '../theme/tokens.dart';

/// Natija: rang + belgi + matn (faqat rangga tayanmaydi — TalkBack va rang ko'rishi zaif foydalanuvchilar uchun).
class VerdictChip extends StatelessWidget {
  const VerdictChip(this.verdict, {super.key, this.large = false});
  final Verdict verdict;
  final bool large;

  static Color colorOf(Verdict v) => switch (v) {
    Verdict.pass => ZanjirColors.success,
    Verdict.fail => ZanjirColors.danger,
    Verdict.needsReview => ZanjirColors.warn,
    Verdict.notApplicable => ZanjirColors.inkMuted,
  };

  static IconData iconOf(Verdict v) => switch (v) {
    Verdict.pass => Icons.check_circle,
    Verdict.fail => Icons.cancel,
    Verdict.needsReview => Icons.help,
    Verdict.notApplicable => Icons.remove_circle,
  };

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context).verdictName(verdict);
    return Semantics(
      label: text,
      excludeSemantics: true,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: large ? 14 : 8, vertical: large ? 10 : 4),
        decoration: BoxDecoration(color: colorOf(verdict), borderRadius: BorderRadius.circular(16)),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(iconOf(verdict), color: ZanjirColors.accentInk, size: large ? 24 : 16),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                text,
                softWrap: true,
                style: TextStyle(color: ZanjirColors.accentInk, fontWeight: FontWeight.w700, fontSize: large ? 18 : 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
