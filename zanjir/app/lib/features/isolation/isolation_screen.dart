import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';

/// Ajratish rejasi — tavsiya (ko'rib chiqish). Tasdiqlash va bajarish checklist'i — 9-faza.
/// "Kuchlanish yo'qligini tekshirish" qadami doim ko'rsatiladi va belgilanmaydi (CLAUDE.md, 2-qoida).
class IsolationScreen extends ConsumerStatefulWidget {
  const IsolationScreen({super.key, required this.siteId});
  final String siteId;

  @override
  ConsumerState<IsolationScreen> createState() => _IsolationScreenState();
}

class _IsolationScreenState extends ConsumerState<IsolationScreen> {
  final _zone = <String>{};
  IsolationResult? _result;

  void _build(Graph g, EarthingSystem? es) => setState(() => _result = planIsolation(g, _zone, earthingSystem: es));

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final site = ref.watch(siteProvider(widget.siteId)).value;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.isolationTitle)),
      body: AsyncView(
        value: ref.watch(graphProvider(widget.siteId)),
        builder: (g) {
          String labelOf(String id) => g.node(id)?.label ?? id;
          final nodes = g.nodes.where((n) => !n.kind.isSource).toList()..sort((a, b) => a.label.compareTo(b.label));
          final r = _result;
          return ListView(
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              ListTile(title: Text(l10n.selectZone, style: Theme.of(context).textTheme.titleMedium)),
              for (final n in nodes)
                CheckboxListTile(
                  key: Key('zone.${n.id}'),
                  value: _zone.contains(n.id),
                  title: Text(n.label),
                  subtitle: Text(l10n.kindName(n.kind)),
                  onChanged: (v) => setState(() {
                    v == true ? _zone.add(n.id) : _zone.remove(n.id);
                    _result = null;
                  }),
                ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: FilledButton(
                  key: const Key('isolation.build'),
                  onPressed: _zone.isEmpty ? null : () => _build(g, site?.earthingSystem),
                  child: Text(l10n.buildPlan),
                ),
              ),
              if (r is IsolationBlocked) ...[
                ListTile(
                  title: Text(l10n.planBlocked, style: const TextStyle(color: ZanjirColors.danger)),
                  subtitle: Text(
                    '${switch (r.reason) {
                      BlockReason.noSwitchingDevice => l10n.blockedNoSwitching,
                      BlockReason.sourceInZone => l10n.blockedSourceInZone,
                      BlockReason.verificationFailed => l10n.blockedVerification,
                    }}\n${r.path.map(labelOf).join(' → ')}',
                  ),
                ),
              ],
              if (r is IsolationPlan) ...[
                ListTile(title: Text(l10n.steps, style: Theme.of(context).textTheme.titleMedium)),
                for (final s in r.steps)
                  ListTile(
                    key: Key('step.${s.order}'),
                    leading: CircleAvatar(
                      backgroundColor: s.kind == StepKind.verifyNoVoltage ? ZanjirColors.accent : ZanjirColors.surface,
                      foregroundColor: s.kind == StepKind.verifyNoVoltage ? ZanjirColors.accentInk : ZanjirColors.ink,
                      child: Text('${s.order}'),
                    ),
                    title: Text(l10n.stepText(s, labelOf)),
                    subtitle: s.kind == StepKind.verifyNoVoltage ? Text(l10n.mandatory) : null,
                  ),
              ],
              if (r != null && r.warnings.isNotEmpty) ...[
                ListTile(title: Text(l10n.warnings, style: Theme.of(context).textTheme.titleMedium)),
                for (final w in r.warnings)
                  ListTile(
                    leading: const Icon(Icons.warning_amber, color: ZanjirColors.warn),
                    title: Text(l10n.warningText(w, labelOf)),
                  ),
              ],
            ],
          );
        },
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
