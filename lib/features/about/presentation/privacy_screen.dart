import 'package:baraka_daftari/app/app_info.dart';
import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:flutter/material.dart';

/// Maxfiylik siyosati: Google Play talabi bo'yicha ilova ichida ham to'liq
/// matn. Ochiq nusxasi — `docs/PRIVACY_POLICY.md` (mazmuni bir xil saqlanadi).
class PrivacyScreen extends StatelessWidget {
  const PrivacyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final sections = [
      (l10n.privacyStoredTitle, l10n.privacyStoredBody),
      (l10n.privacyNoNetworkTitle, l10n.privacyNoNetworkBody),
      (l10n.privacyPermissionsTitle, l10n.privacyPermissionsBody),
      (l10n.privacyShareTitle, l10n.privacyShareBody),
      (l10n.privacyDeleteTitle, l10n.privacyDeleteBody),
      (l10n.privacyChildrenTitle, l10n.privacyChildrenBody),
      (l10n.privacyChangesTitle, l10n.privacyChangesBody),
    ];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.privacyTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            l10n.privacyUpdated,
            key: const Key('privacy-updated'),
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          Text(l10n.privacyIntro(AppInfo.author)),
          for (final (title, body) in sections) ...[
            const SizedBox(height: 16),
            Text(title, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(body),
          ],
        ],
      ),
    );
  }
}
