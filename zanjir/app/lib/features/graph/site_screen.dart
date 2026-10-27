import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';
import 'graph_layout.dart';
import 'node_icons.dart';

class SiteScreen extends ConsumerWidget {
  const SiteScreen({super.key, required this.siteId});
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final site = ref.watch(siteProvider(siteId));
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(site.value?.name ?? ''),
          actions: [
            IconButton(
              tooltip: l10n.isolationPlan,
              icon: const Icon(Icons.power_off),
              onPressed: () => context.push('/sites/$siteId/plans'),
            ),
            IconButton(
              tooltip: l10n.edit,
              icon: const Icon(Icons.edit),
              onPressed: () => context.push('/sites/$siteId/edit'),
            ),
          ],
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.treeMode),
              Tab(text: l10n.graphMode),
              Tab(text: l10n.sessions),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _TreeTab(siteId: siteId),
            _GraphTab(siteId: siteId),
            _SessionsTab(siteId: siteId),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          key: const Key('site.addNode'),
          onPressed: () => context.push('/sites/$siteId/nodes/new'),
          icon: const Icon(Icons.add),
          label: Text(l10n.addNode),
        ),
        bottomNavigationBar: const DisclaimerBanner(),
      ),
    );
  }
}

class _TreeTab extends ConsumerWidget {
  const _TreeTab({required this.siteId});
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return AsyncView(
      value: ref.watch(graphProvider(siteId)),
      onRetry: () => ref.invalidate(graphProvider(siteId)),
      builder: (g) {
        if (g.nodes.isEmpty) return Center(child: Text(l10n.emptyGraph));
        final tree = buildTree(g);
        return ListView(
          padding: const EdgeInsets.only(bottom: 96),
          children: [
            for (final r in tree.rows) _NodeTile(node: r.node, depth: r.depth),
            if (tree.unconnected.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
                child: Text(l10n.unconnected, style: const TextStyle(color: ZanjirColors.warn)),
              ),
              for (final n in tree.unconnected) _NodeTile(node: n, depth: 0),
            ],
          ],
        );
      },
    );
  }
}

class _NodeTile extends StatelessWidget {
  const _NodeTile({required this.node, required this.depth});
  final Node node;
  final int depth;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = node.state;
    return ListTile(
      contentPadding: EdgeInsets.only(left: 16.0 + depth * 20, right: 16),
      leading: Icon(nodeIcon(node.kind), color: node.kind.isSource ? ZanjirColors.accentText : ZanjirColors.ink),
      title: Text(node.label),
      subtitle: Text(
        [
          l10n.kindName(node.kind),
          if (state != null) state == SwitchState.open ? l10n.stateOpen : l10n.stateClosed,
        ].join(' · '),
      ),
      trailing: node.verified
          ? null
          : Tooltip(
              message: l10n.unverified,
              child: const Icon(Icons.warning_amber, color: ZanjirColors.warn),
            ),
      onTap: () => context.push('/nodes/${node.id}'),
    );
  }
}

class _GraphTab extends ConsumerWidget {
  const _GraphTab({required this.siteId});
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return AsyncView(
      value: ref.watch(graphProvider(siteId)),
      builder: (g) {
        if (g.nodes.isEmpty) return Center(child: Text(l10n.emptyGraph));
        final layout = GraphLayout.of(g);
        return InteractiveViewer(
          constrained: false,
          boundaryMargin: const EdgeInsets.all(200),
          minScale: 0.3,
          child: GestureDetector(
            onTapUp: (d) {
              final id = layout.hit(d.localPosition);
              if (id != null) context.push('/nodes/$id');
            },
            child: Semantics(
              label: l10n.graphMode,
              child: CustomPaint(size: layout.size, painter: _GraphPainter(g, layout)),
            ),
          ),
        );
      },
    );
  }
}

class _GraphPainter extends CustomPainter {
  _GraphPainter(this.graph, this.layout);
  final Graph graph;
  final GraphLayout layout;

  @override
  void paint(Canvas canvas, Size size) {
    final edgePaint = Paint()
      ..color = ZanjirColors.line
      ..strokeWidth = 2;
    for (final e in graph.edges) {
      final a = layout.positions[e.aNodeId]!;
      final b = layout.positions[e.bNodeId]!;
      canvas.drawLine(a.center, b.center, edgePaint);
    }
    for (final n in graph.nodes) {
      final r = layout.positions[n.id]!;
      final fill = Paint()..color = n.kind.isSource ? ZanjirColors.sidebar : ZanjirColors.surface;
      final border = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = !n.verified
            ? ZanjirColors.warn
            : n.kind.isSwitching
            ? ZanjirColors.accent
            : ZanjirColors.line;
      final rr = RRect.fromRectAndRadius(r, const Radius.circular(8));
      canvas.drawRRect(rr, fill);
      canvas.drawRRect(rr, border);
      final tp = TextPainter(
        text: TextSpan(
          text: n.label,
          style: const TextStyle(color: ZanjirColors.ink, fontSize: 14),
        ),
        textDirection: TextDirection.ltr,
        maxLines: 1,
        ellipsis: '…',
      )..layout(maxWidth: r.width - 8);
      tp.paint(canvas, Offset(r.center.dx - tp.width / 2, r.center.dy - tp.height / 2));
    }
  }

  @override
  bool shouldRepaint(_GraphPainter old) => old.graph != graph;
}

class _SessionsTab extends ConsumerWidget {
  const _SessionsTab({required this.siteId});
  final String siteId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return AsyncView(
      value: ref.watch(siteSessionsProvider(siteId)),
      builder: (sessions) => ListView(
        padding: const EdgeInsets.only(bottom: 96),
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: FilledButton.icon(
              key: const Key('site.startSession'),
              onPressed: () => context.push('/sites/$siteId/sessions/new'),
              icon: const Icon(Icons.play_arrow),
              label: Text(l10n.startSession),
            ),
          ),
          for (final s in sessions.reversed)
            Card(
              child: ListTile(
                leading: Icon(s.closedAt == null ? Icons.radio_button_checked : Icons.lock),
                title: Text(l10n.sessionKindName(s.kind)),
                subtitle: Text(s.startedAt.toLocal().toString().substring(0, 16)),
                onTap: () => context.push('/sessions/${s.id}'),
              ),
            ),
        ],
      ),
    );
  }
}
