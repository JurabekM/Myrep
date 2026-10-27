import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/settings/settings_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// AppBar uchun til va mavzu tugmalari.
class SettingsActions extends ConsumerWidget {
  const SettingsActions({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final controller = ref.read(settingsControllerProvider.notifier);
    final l10n = context.l10n;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          key: const Key('switch-language'),
          tooltip: l10n.switchLanguageTooltip,
          icon: const Icon(Icons.translate),
          onPressed: controller.toggleLanguage,
        ),
        IconButton(
          key: const Key('switch-theme'),
          tooltip: l10n.switchThemeTooltip,
          icon: const Icon(Icons.brightness_6_outlined),
          onPressed: () => controller.toggleTheme(Theme.of(context).brightness),
        ),
      ],
    );
  }
}
