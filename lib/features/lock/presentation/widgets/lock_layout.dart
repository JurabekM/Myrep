import 'package:flutter/material.dart';

/// Qulf va PIN o'rnatish ekranlari uchun umumiy joylashuv: yuqorida matn,
/// pastda klaviatura. Kichik ekranda aylantiriladi (kontent siqilmaydi).
class LockLayout extends StatelessWidget {
  const LockLayout({
    required this.header,
    required this.pad,
    this.message,
    super.key,
  });

  final List<Widget> header;
  final String? message;
  final Widget pad;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                ...header,
                const SizedBox(height: 8),
                SizedBox(
                  height: 48,
                  child: message == null
                      ? null
                      : Text(
                          message!,
                          key: const Key('lock-message'),
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.error,
                          ),
                        ),
                ),
                const SizedBox(height: 8),
                Center(child: pad),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
