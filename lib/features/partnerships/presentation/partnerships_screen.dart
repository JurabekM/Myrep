import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Sherikliklar (5-qonun, SPEC 2E).
class PartnershipsScreen extends ConsumerWidget {
  const PartnershipsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final list = ref.watch(partnershipsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.pnTitle),
        actions: [
          IconButton(
            key: const Key('pn-offer-check'),
            tooltip: l10n.offerTitle,
            icon: const Icon(Icons.fact_check_outlined),
            onPressed: () => context.push(AppRoutes.offerCheck),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('pn-new'),
        icon: const Icon(Icons.add),
        label: Text(l10n.pnNew),
        onPressed: () async {
          await context.push(AppRoutes.partnershipNew);
          ref.invalidate(partnershipsProvider);
        },
      ),
      body: switch (list) {
        AsyncData(:final value) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(l10n.pnHint),
            const SizedBox(height: 12),
            if (value.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(l10n.pnEmpty),
              ),
            for (final p in value)
              Card(
                key: Key('pn-${p.meta.id}'),
                child: ListTile(
                  leading: const Icon(Icons.join_inner),
                  title: Text(p.title),
                  subtitle: Text(
                    '${l10n.partnershipType(p.type)} · '
                    '${l10n.partnershipStatus(p.status)}',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await context.push(AppRoutes.partnership(p.meta.id));
                    ref.invalidate(partnershipsProvider);
                  },
                ),
              ),
          ],
        ),
        AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

/// Bosh ekran: «Taklifni tekshirish» (SPEC 2E.5 — istalgan joydan).
class OfferCheckHomeCard extends StatelessWidget {
  const OfferCheckHomeCard({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Card(
      key: const Key('home-offer-check'),
      child: ListTile(
        leading: const Icon(Icons.fact_check_outlined),
        title: Text(l10n.offerTitle),
        subtitle: Text(l10n.homeOfferCheckBody),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push(AppRoutes.offerCheck),
      ),
    );
  }
}
