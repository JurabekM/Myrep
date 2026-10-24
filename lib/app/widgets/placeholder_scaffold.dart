import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:flutter/material.dart';

/// Vazifa 1 dagi bo'sh ekranlar uchun umumiy karkas.
class PlaceholderScaffold extends StatelessWidget {
  const PlaceholderScaffold({
    required this.title,
    required this.description,
    this.children = const [],
    this.floatingActionButton,
    super.key,
  });

  final String title;
  final String description;
  final List<Widget> children;
  final Widget? floatingActionButton;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: const [SettingsActions()],
      ),
      floatingActionButton: floatingActionButton,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              children: [
                Text(description, style: theme.textTheme.bodyLarge),
                const SizedBox(height: 8),
                Text(
                  context.l10n.placeholderNotice,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                if (children.isNotEmpty) const SizedBox(height: 24),
                ...children,
              ],
            ),
          ),
        ),
      ),
    );
  }
}
