import 'package:flutter/material.dart';

import '../../l10n/gen/app_localizations.dart';
import '../../widgets/disclaimer_banner.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.homeTitle)),
      body: Center(child: Text(l10n.homeEmpty)),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
