import 'package:baraka_daftari/app/app_info.dart';
import 'package:baraka_daftari/app/demo/demo_config.dart';
import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/brand_logo.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// «Ilova haqida»: nom, versiya, muallif, mualliflik huquqi, maxfiylik va
/// ochiq kodli kutubxonalar litsenziyalari.
class AboutScreen extends ConsumerWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final demo = ref.watch(demoConfigProvider);
    final copyright = l10n.aboutCopyright(
      AppInfo.copyrightYear,
      AppInfo.author,
    );
    final version = l10n.aboutVersion(AppInfo.version, AppInfo.build);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.aboutTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Center(child: BrandLogo(size: 88)),
          const SizedBox(height: 12),
          Text(
            l10n.appTitle,
            style: theme.textTheme.headlineSmall,
            textAlign: TextAlign.center,
          ),
          Text(
            version,
            key: const Key('about-version'),
            style: theme.textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
          if (demo.enabled && demo.until != null)
            Text(
              l10n.demoUntil(formatDate(demo.until!)),
              key: const Key('about-demo'),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.error,
              ),
              textAlign: TextAlign.center,
            ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.aboutAuthor(AppInfo.author),
                    key: const Key('about-author'),
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(copyright, key: const Key('about-copyright')),
                  const SizedBox(height: 8),
                  Text(l10n.aboutRights, style: theme.textTheme.bodySmall),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              key: const Key('about-privacy'),
              leading: const Icon(Icons.lock_outline),
              title: Text(l10n.privacyTitle),
              subtitle: Text(l10n.aboutPrivacy),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(AppRoutes.privacy),
            ),
          ),
          const SizedBox(height: 8),
          Text(l10n.contentDisclaimer, style: theme.textTheme.bodySmall),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            key: const Key('about-licenses'),
            icon: const Icon(Icons.description_outlined),
            label: Text(l10n.aboutLicenses),
            onPressed: () => showLicensePage(
              context: context,
              applicationName: l10n.appTitle,
              applicationVersion: version,
              applicationLegalese: copyright,
            ),
          ),
        ],
      ),
    );
  }
}
