import 'package:flutter/material.dart';

import '../../l10n/gen/app_localizations.dart';
import '../../widgets/disclaimer_banner.dart';

/// Protokol: deterministik PDF, QR va imzolash — 6-fazada. Hozircha holat matni.
class ProtocolScreen extends StatelessWidget {
  const ProtocolScreen({super.key, required this.sessionId});
  final String sessionId;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.protocol)),
      body: Padding(padding: const EdgeInsets.all(16), child: Text(l10n.protocolNotReady)),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
