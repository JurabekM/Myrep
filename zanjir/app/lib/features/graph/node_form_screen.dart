import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import 'attr_specs.dart';

/// Tugun qo'shish (`nodeId == null`) yoki tahrirlash.
class NodeFormScreen extends ConsumerStatefulWidget {
  const NodeFormScreen({super.key, required this.siteId, this.nodeId});
  final String siteId;
  final String? nodeId;

  @override
  ConsumerState<NodeFormScreen> createState() => _NodeFormScreenState();
}

class _NodeFormScreenState extends ConsumerState<NodeFormScreen> {
  final _form = GlobalKey<FormState>();
  final _label = TextEditingController();
  final _conductors = TextEditingController(text: 'L1 N PE');
  final _numbers = <String, TextEditingController>{};
  final _choices = <String, String?>{};
  NodeKind _kind = NodeKind.breaker;
  SwitchState? _state;
  bool _verified = false;
  String? _connectTo;
  NodeRow? _existing;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    final id = widget.nodeId;
    if (id == null) {
      // Birinchi tugun odatda manba (kirish).
      ref.read(nodesProvider(widget.siteId).future).then((nodes) {
        if (mounted && nodes.isEmpty) setState(() => _kind = NodeKind.srcGrid);
      });
      _loaded = true;
      return;
    }
    ref.read(nodeProvider(id).future).then((n) {
      if (n == null || !mounted) return;
      setState(() {
        _existing = n;
        _kind = n.kind;
        _label.text = n.label;
        _state = n.state;
        _verified = n.verified;
        for (final spec in attrSpecsFor(n.kind)) {
          final v = n.attrs[spec.key];
          if (v == null) continue;
          switch (spec.type) {
            case AttrType.number:
              _num(spec.key).text = v is num ? formatDecimal(v) : '$v';
            case AttrType.flag:
              _choices[spec.key] = v == true ? 'true' : 'false';
            case AttrType.choice || AttrType.text:
              _choices[spec.key] = '$v';
          }
        }
        _loaded = true;
      });
    });
  }

  TextEditingController _num(String key) => _numbers.putIfAbsent(key, TextEditingController.new);

  @override
  void dispose() {
    for (final c in [_label, _conductors, ..._numbers.values]) {
      c.dispose();
    }
    super.dispose();
  }

  /// Formadagi atributlar; mavjud tugundagi formada ko'rsatilmagan atributlar saqlanib qoladi.
  Map<String, Object?> _attrs() {
    final out = <String, Object?>{...?_existing?.attrs};
    for (final spec in attrSpecsFor(_kind)) {
      out.remove(spec.key);
      switch (spec.type) {
        case AttrType.number:
          final v = parseDecimal(_num(spec.key).text);
          if (v != null) out[spec.key] = v == v.roundToDouble() ? v.toInt() : v;
        case AttrType.flag:
          final v = _choices[spec.key];
          if (v != null) out[spec.key] = v == 'true';
        case AttrType.choice || AttrType.text:
          final v = _choices[spec.key];
          if (v != null) out[spec.key] = v;
      }
    }
    return out;
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final l10n = AppLocalizations.of(context);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final existing = _existing;
      final state = _kind.isSwitching ? _state : null;
      if (existing == null) {
        await repos.ctx.db.transaction(() async {
          final n = await repos.graph.addNode(
            siteId: widget.siteId,
            kind: _kind,
            label: _label.text.trim(),
            attrs: _attrs(),
            verified: _verified,
            state: state,
          );
          final parent = _connectTo;
          if (parent != null) {
            await repos.graph.addEdge(
              siteId: widget.siteId,
              aNodeId: parent,
              bNodeId: n.id,
              conductors: _conductors.text.trim(),
            );
          }
        });
      } else {
        await repos.graph.updateNode(
          existing.copyWith(
            kind: _kind,
            label: _label.text.trim(),
            attrs: _attrs(),
            verified: _verified,
            state: Value(state),
          ),
        );
        ref.invalidate(nodeProvider(existing.id));
      }
      invalidateSite(ref, widget.siteId);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  Widget _attrField(AppLocalizations l10n, AttrSpec spec) {
    final key = Key('node.attr.${spec.key}');
    switch (spec.type) {
      case AttrType.number:
        return TextFormField(
          key: key,
          controller: _num(spec.key),
          decoration: InputDecoration(labelText: spec.label(l10n)),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          validator: (v) => (v ?? '').trim().isEmpty || parseDecimal(v) != null ? null : l10n.invalidNumber,
        );
      case AttrType.flag || AttrType.choice || AttrType.text:
        final options = spec.type == AttrType.flag ? const ['true', 'false'] : spec.options;
        String optionText(String v) =>
            spec.type == AttrType.flag ? (v == 'true' ? l10n.yes : l10n.no) : spec.optionLabel(l10n, v);
        return DropdownButtonFormField<String?>(
          isExpanded: true,
          key: key,
          initialValue: _choices[spec.key],
          decoration: InputDecoration(labelText: spec.label(l10n)),
          items: [
            DropdownMenuItem(child: Text(l10n.notSet)),
            for (final o in options) DropdownMenuItem(value: o, child: Text(optionText(o))),
          ],
          onChanged: (v) => setState(() => _choices[spec.key] = v),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final nodes = ref.watch(nodesProvider(widget.siteId)).value ?? const <NodeRow>[];
    return Scaffold(
      appBar: AppBar(title: Text(l10n.nodeFormTitle)),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _form,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  DropdownButtonFormField<NodeKind>(
                    isExpanded: true,
                    key: const Key('node.kind'),
                    initialValue: _kind,
                    decoration: InputDecoration(labelText: l10n.nodeKind),
                    items: [for (final k in NodeKind.values) DropdownMenuItem(value: k, child: Text(l10n.kindName(k)))],
                    onChanged: (v) => setState(() => _kind = v!),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    key: const Key('node.label'),
                    controller: _label,
                    decoration: InputDecoration(labelText: l10n.label),
                    validator: (v) => (v ?? '').trim().isEmpty ? l10n.requiredField : null,
                  ),
                  for (final spec in attrSpecsFor(_kind)) ...[const SizedBox(height: 12), _attrField(l10n, spec)],
                  if (_kind.isSwitching) ...[
                    const SizedBox(height: 12),
                    DropdownButtonFormField<SwitchState?>(
                      isExpanded: true,
                      initialValue: _state,
                      decoration: InputDecoration(labelText: l10n.state),
                      items: [
                        DropdownMenuItem(child: Text(l10n.notSet)),
                        DropdownMenuItem(value: SwitchState.closed, child: Text(l10n.stateClosed)),
                        DropdownMenuItem(value: SwitchState.open, child: Text(l10n.stateOpen)),
                      ],
                      onChanged: (v) => setState(() => _state = v),
                    ),
                  ],
                  if (_existing == null) ...[
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String?>(
                      isExpanded: true,
                      key: const Key('node.connectTo'),
                      initialValue: _connectTo,
                      decoration: InputDecoration(labelText: l10n.connectTo),
                      items: [
                        DropdownMenuItem(child: Text(l10n.notSet)),
                        for (final n in nodes)
                          DropdownMenuItem(value: n.id, child: Text('${n.label} · ${l10n.kindName(n.kind)}')),
                      ],
                      onChanged: (v) => setState(() => _connectTo = v),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _conductors,
                      decoration: InputDecoration(labelText: l10n.conductors),
                    ),
                  ],
                  const SizedBox(height: 8),
                  SwitchListTile(
                    key: const Key('node.verified'),
                    value: _verified,
                    title: Text(l10n.verified),
                    onChanged: (v) => setState(() => _verified = v),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(key: const Key('node.save'), onPressed: _save, child: Text(l10n.save)),
                ],
              ),
            ),
    );
  }
}
