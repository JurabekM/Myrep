import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';
import 'plan_status_chip.dart';

/// Obyektning ajratish rejalari (ADR-0013). Ochilganda graf o'zgargan rejalar STALE bo'ladi.
class PlansScreen extends ConsumerWidget {
  const PlansScreen({super.key, required this.siteId});
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final labels = {for (final n in ref.watch(nodesProvider(siteId)).value ?? const []) n.id: n.label};
    final canBuild = ref.watch(profileProvider).value?.role != 'VIEWER';
    return Scaffold(
      appBar: AppBar(title: Text(l10n.plansTitle)),
      body: AsyncView(
        value: ref.watch(sitePlansProvider(siteId)),
        builder: (plans) => plans.isEmpty
            ? Center(child: Text(l10n.noPlans))
            : ListView(
                children: [
                  for (final p in plans)
                    ListTile(
                      key: Key('plan.${p.id}'),
                      title: Text(l10n.planZone(p.targetNodeIds.map((id) => labels[id] ?? '?').join(', '))),
                      subtitle: Text(p.createdAt.toLocal().toString().substring(0, 16)),
                      trailing: PlanStatusChip(p.status),
                      onTap: () async {
                        await context.push('/plans/${p.id}');
                        ref.invalidate(sitePlansProvider(siteId));
                      },
                    ),
                ],
              ),
      ),
      floatingActionButton: canBuild
          ? FloatingActionButton.extended(
              key: const Key('plans.new'),
              onPressed: () async {
                await context.push('/sites/$siteId/isolation');
                ref.invalidate(sitePlansProvider(siteId));
              },
              icon: const Icon(Icons.add),
              label: Text(l10n.newPlan),
            )
          : null,
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
