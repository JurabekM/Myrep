import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../../core/providers.dart';
import '../../core/summary.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';
import '../../widgets/verdict_chip.dart';

class SummaryScreen extends ConsumerWidget {
  const SummaryScreen({super.key, required this.sessionId});
  final String sessionId;

  Future<void> _close(BuildContext context, WidgetRef ref, String siteId) async {
    final l10n = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.closeSession),
        content: Text(l10n.closeSessionConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FilledButton(
            key: const Key('summary.confirmClose'),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.closeSession),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final repos = await ref.read(repositoriesProvider.future);
      await repos.sessions.close(sessionId);
      ref.invalidate(sessionProvider(sessionId));
      ref.invalidate(siteSessionsProvider(siteId));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return AsyncView(
      value: ref.watch(sessionProvider(sessionId)),
      builder: (session) {
        if (session == null)
          return Scaffold(
            appBar: AppBar(),
            body: Center(child: Text(l10n.codeNotFound)),
          );
        final open = session.closedAt == null;
        final nodes = {for (final n in ref.watch(nodesProvider(session.siteId)).value ?? const []) n.id: n.label};
        return Scaffold(
          appBar: AppBar(title: Text(l10n.summaryTitle)),
          body: AsyncView(
            value: ref.watch(sessionMeasurementsProvider(sessionId)),
            builder: (list) {
              final counts = {for (final v in Verdict.values) v: list.where((m) => m.verdict == v).length};
              return ListView(
                padding: const EdgeInsets.only(bottom: 24),
                children: [
                  ListTile(
                    title: Text(l10n.sessionKindName(session.kind)),
                    subtitle: Text(
                      [
                        session.startedAt.toLocal().toString().substring(0, 16),
                        if (session.ambientTempC != null) '${session.ambientTempC} °C',
                        if (!open) l10n.sessionClosed,
                      ].join(' · '),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Text(l10n.measurementCount(list.length)),
                        for (final v in Verdict.values)
                          if (counts[v]! > 0)
                            Row(mainAxisSize: MainAxisSize.min, children: [VerdictChip(v), Text(' ${counts[v]}')]),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  for (final m in list)
                    ListTile(
                      key: Key('summary.m.${m.id}'),
                      title: Text('${nodes[m.nodeId] ?? '?'} · ${l10n.typeName(m.type)}'),
                      subtitle: Text(
                        [
                          summarizeValues(m.type, m.values),
                          if (m.evalDetail['reason'] is String) l10n.reasonText(m.evalDetail['reason']! as String),
                        ].join('\n'),
                      ),
                      isThreeLine: m.evalDetail['reason'] is String,
                      trailing: VerdictChip(m.verdict),
                      onLongPress: open
                          ? () => context.push('/sessions/$sessionId/measure?node=${m.nodeId}&supersedes=${m.id}')
                          : null,
                    ),
                  const SizedBox(height: 16),
                  if (open) ...[
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: FilledButton(
                        onPressed: () => context.push('/sessions/$sessionId/measure'),
                        child: Text(l10n.continueMeasuring),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: OutlinedButton(
                        key: const Key('summary.close'),
                        onPressed: () => _close(context, ref, session.siteId),
                        child: Text(l10n.closeSession),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Text(l10n.supersedeHint, style: const TextStyle(color: ZanjirColors.inkMuted)),
                    ),
                  ] else
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: FilledButton(
                        onPressed: () => context.push('/sessions/$sessionId/protocol'),
                        child: Text(l10n.protocol),
                      ),
                    ),
                ],
              );
            },
          ),
          bottomNavigationBar: const DisclaimerBanner(),
        );
      },
    );
  }
}
