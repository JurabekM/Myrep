import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';
import '../../widgets/text_prompt.dart';

/// `zanjir://app/n/<id>` yoki shunchaki `<id>` → tugun ID.
String? nodeIdFromCode(String code) {
  final t = code.trim();
  if (t.isEmpty) return null;
  final uri = Uri.tryParse(t);
  if (uri != null && uri.scheme == 'zanjir') {
    final segs = uri.pathSegments;
    return segs.length == 2 && segs.first == 'n' ? segs.last : null;
  }
  return t;
}

class SitesScreen extends ConsumerWidget {
  const SitesScreen({super.key});

  Future<void> _openByCode(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final code = await promptText(
      context,
      title: l10n.openByCode,
      label: l10n.nodeCode,
      confirm: l10n.open,
      fieldKey: const Key('openByCode.field'),
    );
    final id = code == null ? null : nodeIdFromCode(code);
    if (id == null || !context.mounted) return;
    final repos = await ref.read(repositoriesProvider.future);
    final node = await repos.graph.getNode(id);
    if (!context.mounted) return;
    if (node == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.codeNotFound)));
    } else {
      unawaited(context.push('/nodes/${node.id}'));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final sites = ref.watch(sitesProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.homeTitle),
        actions: [
          IconButton(
            tooltip: l10n.openByCode,
            icon: const Icon(Icons.qr_code_2),
            onPressed: () => _openByCode(context, ref),
          ),
          IconButton(
            tooltip: l10n.settings,
            icon: const Icon(Icons.settings),
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: AsyncView(
        value: sites,
        onRetry: () => ref.invalidate(sitesProvider),
        builder: (list) => list.isEmpty
            ? Center(child: Text(l10n.homeEmpty))
            : ListView(
                children: [
                  for (final s in list)
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.apartment),
                        title: Text(s.name),
                        subtitle: Text([s.address, s.earthingSystem?.code].whereType<String>().join(' · ')),
                        onTap: () => context.push('/sites/${s.id}'),
                      ),
                    ),
                ],
              ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('sites.add'),
        onPressed: () => context.push('/sites/new'),
        icon: const Icon(Icons.add),
        label: Text(l10n.addSite),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
