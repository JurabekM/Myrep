import 'package:flutter/material.dart';

import '../l10n/gen/app_localizations.dart';
import '../theme/tokens.dart';

/// O'zgarmas qoida 1: ilova faqat tavsiya beradi — matn doim ko'rinadi.
class DisclaimerBanner extends StatelessWidget {
  const DisclaimerBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Container(
        color: ZanjirColors.surface,
        padding: const EdgeInsets.all(12),
        child: Text(
          AppLocalizations.of(context).disclaimer,
          style: const TextStyle(color: ZanjirColors.inkMuted),
        ),
      ),
    );
  }
}
