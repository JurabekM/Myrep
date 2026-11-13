import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../core/summary.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/verdict_chip.dart';
import 'attr_specs.dart';

class NodeCardScreen extends ConsumerWidget {
  const NodeCardScreen({super.key, required this.nodeId});
  final String nodeId;

  Future<void> _duplicate(BuildContext context, WidgetRef ref, String siteId) async {
    final l10n = AppLocalizations.of(context);
    final repos = await ref.read(repositoriesProvider.future);
    final copy = await repos.graph.duplicateNode(nodeId);
    invalidateSite(ref, siteId);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.duplicated(copy.label))));
      context.pushReplacement('/nodes/${copy.id}');
    }
  }

  Future<void> _delete(BuildContext context, WidgetRef ref, String siteId, String label) async {
    final l10n = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(l10n.deleteNodeConfirm(label)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(l10n.delete)),
        ],
      ),
    );
    if (ok != true) return;
    final repos = await ref.read(repositoriesProvider.future);
    await repos.graph.softDeleteNode(nodeId);
    invalidateSite(ref, siteId);
    ref.invalidate(nodeProvider(nodeId));
    if (context.mounted) context.pop();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return AsyncView(
      value: ref.watch(nodeProvider(nodeId)),
      builder: (node) {
        if (node == null)
          return Scaffold(
            appBar: AppBar(),
            body: Center(child: Text(l10n.codeNotFound)),
          );
        final specs = attrSpecsFor(node.kind);
        String attrValue(String key, Object? v) {
          final spec = specs.where((s) => s.key == key).firstOrNull;
          if (v is bool) return v ? l10n.yes : l10n.no;
          if (v is num) return formatDecimal(v);
          return spec == null ? '$v' : spec.optionLabel(l10n, '$v');
        }

        return Scaffold(
          appBar: AppBar(
            title: Text(node.label),
            actions: [
              IconButton(
                tooltip: l10n.edit,
                icon: const Icon(Icons.edit),
                onPressed: () => context.push('/sites/${node.siteId}/nodes/${node.id}/edit'),
              ),
              IconButton(
                key: const Key('node.duplicate'),
                tooltip: l10n.duplicate,
                icon: const Icon(Icons.copy),
                onPressed: () => _duplicate(context, ref, node.siteId),
              ),
              IconButton(
                tooltip: l10n.delete,
                icon: const Icon(Icons.delete),
                onPressed: () => _delete(context, ref, node.siteId, node.label),
              ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              ListTile(
                title: Text(l10n.kindName(node.kind)),
                subtitle: node.verified
                    ? Text(l10n.verified)
                    : Text(l10n.unverified, style: const TextStyle(color: ZanjirColors.warn)),
              ),
              if (node.attrs.isNotEmpty) ...[
                ListTile(title: Text(l10n.attributes, style: Theme.of(context).textTheme.titleMedium)),
                for (final e in node.attrs.entries)
                  ListTile(
                    dense: true,
                    title: Text(specs.where((s) => s.key == e.key).firstOrNull?.label(l10n) ?? e.key),
                    trailing: Text(attrValue(e.key, e.value)),
                  ),
              ],
              Center(
                child: Container(
                  color: Colors.white,
                  padding: const EdgeInsets.all(12),
                  child: QrImageView(data: nodeQrData(node.id), size: 180, semanticsLabel: l10n.qrHint),
                ),
              ),
              Center(
                child: Padding(padding: const EdgeInsets.all(8), child: Text(l10n.qrHint)),
              ),
              ListTile(title: Text(l10n.measurementsHistory, style: Theme.of(context).textTheme.titleMedium)),
              AsyncView(
                value: ref.watch(nodeMeasurementsProvider(nodeId)),
                builder: (list) => list.isEmpty
                    ? ListTile(title: Text(l10n.noMeasurements))
                    : Column(
                        children: [
                          for (final m in list)
                            ListTile(
                              title: Text(l10n.typeName(m.type)),
                              subtitle: Text(
                                '${summarizeValues(m.type, m.values)}\n${m.createdAt.toLocal().toString().substring(0, 16)}',
                              ),
                              isThreeLine: true,
                              trailing: VerdictChip(m.verdict),
                            ),
                        ],
                      ),
              ),
            ],
          ),
        );
      },
    );
  }
}
