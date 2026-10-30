import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/gen/app_localizations.dart';
import '../../widgets/disclaimer_banner.dart';

/// Boshlang'ich ekran (profil yo'q): yangi oflayn profil. Ilova to'liq oflayn (ADR-0017) — server yo'q.
class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.appTitle)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(l10n.startHint),
            const SizedBox(height: 24),
            FilledButton(
              key: const Key('start.create'),
              onPressed: () => context.go('/onboarding'),
              child: Text(l10n.createOfflineProfile),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
