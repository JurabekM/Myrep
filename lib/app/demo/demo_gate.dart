import 'package:baraka_daftari/app/app_info.dart';
import 'package:baraka_daftari/app/demo/demo_config.dart';
import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/brand_logo.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Butun ilovani o'raydi (`MaterialApp.builder`). Demo bo'lmasa — o'zgarishsiz.
/// Demo'da: burchakda «DEMO» lentasi va pastda muallif / taqiq yozuvi;
/// muddat tugagan bo'lsa — ilova o'rniga faqat xabar ekrani.
class DemoGate extends ConsumerWidget {
  const DemoGate({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final demo = ref.watch(demoConfigProvider);
    if (!demo.enabled) return child;
    final today = Tashkent.dateOf(ref.watch(clockProvider).nowUtc());
    if (demo.expiredOn(today)) return DemoExpiredScreen(until: demo.until!);
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Banner(
      key: const Key('demo-banner'),
      message: l10n.demoBanner,
      location: BannerLocation.topEnd,
      color: theme.colorScheme.error,
      child: Column(
        children: [
          Expanded(child: child),
          Material(
            color: theme.colorScheme.errorContainer,
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 4,
                ),
                child: Text(
                  l10n.demoNotice(AppInfo.copyrightYear, AppInfo.author),
                  key: const Key('demo-notice'),
                  textAlign: TextAlign.center,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: theme.colorScheme.onErrorContainer,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Demo muddati tugagach ko'rsatiladigan yagona ekran.
class DemoExpiredScreen extends StatelessWidget {
  const DemoExpiredScreen({required this.until, super.key});

  final LocalDate until;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Scaffold(
      key: const Key('demo-expired'),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const BrandLogo(),
                const SizedBox(height: 16),
                Text(
                  l10n.demoExpiredTitle,
                  style: theme.textTheme.headlineSmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  l10n.demoExpiredBody(formatDate(until), AppInfo.author),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
