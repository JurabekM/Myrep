import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/security/integrity/integrity_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Qurilma yaxlitligi ogohlantirishi. Ilovani bloklamaydi (MVP qarori).
class IntegrityBanner extends ConsumerWidget {
  const IntegrityBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final risks = ref.watch(integrityRisksProvider).valueOrNull ?? const {};
    final dismissed = ref.watch(integrityWarningDismissedProvider);
    if (risks.isEmpty || dismissed) return const SizedBox.shrink();

    final l10n = context.l10n;
    final theme = Theme.of(context);
    final names = [
      for (final r in IntegrityRisk.values)
        if (risks.contains(r))
          switch (r) {
            IntegrityRisk.rooted => l10n.integrityRiskRooted,
            IntegrityRisk.emulator => l10n.integrityRiskEmulator,
            IntegrityRisk.debugger => l10n.integrityRiskDebugger,
            IntegrityRisk.signatureMismatch => l10n.integrityRiskSignature,
            IntegrityRisk.debuggable => l10n.integrityRiskDebuggable,
          },
    ].join(', ');

    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Card(
        key: const Key('integrity-banner'),
        color: theme.colorScheme.tertiaryContainer,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.info_outline,
                    color: theme.colorScheme.onTertiaryContainer,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      l10n.integrityTitle,
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: theme.colorScheme.onTertiaryContainer,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                l10n.integrityBody(names),
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onTertiaryContainer,
                ),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  key: const Key('integrity-dismiss'),
                  onPressed: ref
                      .read(integrityWarningDismissedProvider.notifier)
                      .dismiss,
                  child: Text(l10n.integrityDismiss),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
