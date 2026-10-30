import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_data/zanjir_data.dart' show readBackupHeader;

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../widgets/disclaimer_banner.dart';
import '../../widgets/password_prompt.dart';

/// Boshlang'ich ekran (profil yo'q): yangi oflayn profil yoki shifrlangan zaxiradan tiklash. Ilova to'liq oflayn
/// (ADR-0017) — server yo'q.
class StartScreen extends ConsumerWidget {
  const StartScreen({super.key});

  Future<void> _restore(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final bytes = await ref.read(fileActionsProvider).pick();
      if (bytes == null || !context.mounted) return;
      // Parol so'rashdan oldin: fayl ZANJIR zaxirasimi va qachon yaratilgan.
      final header = readBackupHeader(bytes);
      final password = await promptPassword(
        context,
        title: l10n.backupRestore,
        confirm: l10n.backupRestore,
        message: l10n.backupCreatedAt(formatLocalDateTime(header.createdAt)),
      );
      if (password == null || !context.mounted) return;
      await withProgress(
        context,
        l10n.restoreWorking,
        () => ref.read(profileProvider.notifier).restore(bytes, password),
      );
      // Profil paydo bo'lgach router o'zi bosh sahifaga o'tkazadi.
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
            const SizedBox(height: 12),
            OutlinedButton.icon(
              key: const Key('start.restore'),
              onPressed: () => _restore(context, ref),
              icon: const Icon(Icons.restore),
              label: Text(l10n.backupRestore),
            ),
          ],
        ),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
