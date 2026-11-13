import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/numbers.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/disclaimer_banner.dart';
import '../../widgets/number_field.dart';
import '../../widgets/text_prompt.dart';
import '../../widgets/verdict_chip.dart';

/// Dala uchun tez kiritish: nuqta → tur → qiymatlar → Saqlash → natija (rang) → avtomatik keyingi nuqta.
class MeasureScreen extends ConsumerStatefulWidget {
  const MeasureScreen({super.key, required this.sessionId, this.nodeId, this.supersedesId});
  final String sessionId;
  final String? nodeId;
  final String? supersedesId;

  @override
  ConsumerState<MeasureScreen> createState() => _MeasureScreenState();
}

const _singlePhasePairs = ['L1-PE', 'N-PE', 'L1-N'];
const _threePhaseExtra = ['L2-PE', 'L3-PE', 'L1-L2', 'L2-L3', 'L3-L1', 'L2-N', 'L3-N'];
const _earthMethods = ['3-wire', '4-wire', '2-wire', 'clamp'];

class _MeasureScreenState extends ConsumerState<MeasureScreen> {
  List<NodeRow> _nodes = const [];
  List<InstrumentRow> _instruments = const [];
  SiteRow? _site;
  MeasurementSessionRow? _session;
  int _index = 0;
  MeasurementType _type = MeasurementType.insulation;
  String? _instrumentId;
  String? _supersedesId;
  bool _loading = true;
  bool _saving = false;
  Object? _loadError;
  MeasurementRow? _last;
  String? _lastLabel;

  final _c = <String, TextEditingController>{};
  double _testVoltage = 1000;
  bool _threePhase = false;
  String _loopPair = 'L1-PE';
  double _multiplier = 1;
  bool? _tripped;
  String _method = '3-wire';
  String? _scope;

  TextEditingController _ctrl(String key) => _c.putIfAbsent(key, TextEditingController.new);

  @override
  void initState() {
    super.initState();
    _supersedesId = widget.supersedesId;
    _load();
  }

  Future<void> _load() async {
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final session = await repos.sessions.require(widget.sessionId);
      final nodes = await repos.graph.nodes(session.siteId);
      final instruments = await repos.instruments.list();
      final site = await repos.sites.require(session.siteId);
      if (!mounted) return;
      setState(() {
        _session = session;
        _site = site;
        _nodes = nodes;
        _instruments = instruments;
        _instrumentId = instruments.isEmpty ? null : instruments.first.id;
        final i = nodes.indexWhere((n) => n.id == widget.nodeId);
        _selectNode(i < 0 ? 0 : i);
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadError = e;
          _loading = false;
        });
      }
    }
  }

  void _selectNode(int i) {
    _index = i;
    if (_nodes.isNotEmpty) _type = defaultMeasurementType(_nodes[i].kind);
    _resetInputs();
  }

  void _resetInputs() {
    for (final c in _c.values) {
      c.clear();
    }
    _tripped = null;
    _scope = null;
  }

  @override
  void dispose() {
    for (final c in _c.values) {
      c.dispose();
    }
    super.dispose();
  }

  NodeRow? get _node => _nodes.isEmpty ? null : _nodes[_index];

  void _put(Map<String, Object?> m, String key, String field) {
    final v = parseDecimal(_ctrl(field).text);
    if (v != null) m[key] = v;
  }

  /// Bo'sh maydonlar qo'shilmaydi — baholovchi ularni `value_missing` (NEEDS_REVIEW) deb belgilaydi.
  Map<String, Object?> _values() {
    final v = <String, Object?>{};
    switch (_type) {
      case MeasurementType.insulation:
        v['test_voltage_v'] = _testVoltage;
        v['pairs'] = [
          for (final p in [..._singlePhasePairs, if (_threePhase) ..._threePhaseExtra])
            if (parseDecimal(_ctrl('pair.$p').text) case final mohm?) {'pair': p, 'mohm': mohm},
        ];
      case MeasurementType.loopImpedance:
        v['pair'] = _loopPair;
        _put(v, 'zs_ohm', 'zs');
      case MeasurementType.rcdTrip:
        v['multiplier'] = _multiplier;
        _put(v, 'trip_time_ms', 'time');
        if (_multiplier == 1) _put(v, 'trip_current_ma', 'current');
        if (_tripped != null) v['tripped'] = _tripped;
      case MeasurementType.earthResistance:
        _put(v, 'r_ohm', 'earth');
        _put(v, 'season_coeff', 'season');
        v['method'] = _method;
        if (_scope != null) v['scope'] = _scope;
      case MeasurementType.continuityBonding:
        _put(v, 'r_ohm', 'bond');
        for (final k in ['from', 'to']) {
          final t = _ctrl('bond.$k').text.trim();
          if (t.isNotEmpty) v[k] = t;
        }
    }
    return v;
  }

  Future<void> _save([Map<String, Object?>? values]) async {
    final node = _node;
    final instrumentId = _instrumentId;
    if (node == null || instrumentId == null || _saving) return;
    final l10n = AppLocalizations.of(context);
    setState(() => _saving = true);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final settings = await repos.settings.current();
      final m = await repos.measurements.record(
        sessionId: widget.sessionId,
        nodeId: node.id,
        type: _type,
        instrumentId: instrumentId,
        values: values ?? _values(),
        enteredVia: EnteredVia.manual,
        normSetVersion: settings.activeNormSetVersion ?? (throw StateError('norm_set')),
        supersedesId: _supersedesId,
      );
      ref.invalidate(sessionMeasurementsProvider(widget.sessionId));
      ref.invalidate(nodeMeasurementsProvider(node.id));
      if (!mounted) return;
      setState(() {
        _last = m;
        _lastLabel = node.label;
        _supersedesId = null;
        _saving = false;
        _selectNode((_index + 1) % _nodes.length);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  Future<void> _notApplicable() async {
    final l10n = AppLocalizations.of(context);
    final reason = await promptText(
      context,
      title: l10n.notApplicable,
      label: l10n.notApplicableReason,
      confirm: l10n.save,
      fieldKey: const Key('measure.naReason'),
    );
    if (reason != null && reason.isNotEmpty) await _save({'not_applicable_reason': reason});
  }

  Widget _chips<T>(List<T> options, T selected, String Function(T) label, ValueChanged<T> onSelected) => Wrap(
    spacing: 8,
    children: [
      for (final o in options)
        ChoiceChip(label: Text(label(o)), selected: o == selected, onSelected: (_) => setState(() => onSelected(o))),
    ],
  );

  List<Widget> _fields(AppLocalizations l10n) {
    Widget num(String key, String label, {bool last = false}) => Padding(
      padding: const EdgeInsets.only(top: 12),
      child: NumberField(
        fieldKey: Key('measure.$key'),
        controller: _ctrl(key),
        label: label,
        textInputAction: last ? TextInputAction.done : TextInputAction.next,
        onSubmitted: last ? (_) => _save() : null,
      ),
    );
    switch (_type) {
      case MeasurementType.insulation:
        final pairs = [..._singlePhasePairs, if (_threePhase) ..._threePhaseExtra];
        return [
          Text(l10n.testVoltage),
          _chips<double>(const [500, 1000, 2500], _testVoltage, (v) => '${v.toInt()} V', (v) => _testVoltage = v),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: _threePhase,
            title: Text(l10n.threePhase),
            onChanged: (v) => setState(() => _threePhase = v),
          ),
          for (final p in pairs) num('pair.$p', '$p, MΩ', last: p == pairs.last),
        ];
      case MeasurementType.loopImpedance:
        final pen = _site?.earthingSystem == EarthingSystem.tnC;
        return [
          Text(l10n.pair),
          _chips<String>(
            [
              for (final l in ['L1', 'L2', 'L3']) '$l-${pen ? 'PEN' : 'PE'}',
            ],
            _loopPair,
            (v) => v,
            (v) => _loopPair = v,
          ),
          num('zs', l10n.zsOhm, last: true),
        ];
      case MeasurementType.rcdTrip:
        return [
          Text(l10n.multiplier),
          _chips<double>(const [0.5, 1, 2, 5], _multiplier, (v) => '${formatDecimal(v)}·IΔn', (v) => _multiplier = v),
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: SegmentedButton<bool>(
              key: const Key('measure.tripped'),
              segments: [
                ButtonSegment(value: true, label: Text(l10n.trippedYes)),
                ButtonSegment(value: false, label: Text(l10n.trippedNo)),
              ],
              selected: {?_tripped},
              emptySelectionAllowed: true,
              onSelectionChanged: (s) => setState(() => _tripped = s.firstOrNull),
            ),
          ),
          num('time', l10n.tripTime, last: _multiplier != 1),
          if (_multiplier == 1) num('current', l10n.tripCurrent, last: true),
        ];
      case MeasurementType.earthResistance:
        return [
          num('earth', l10n.earthR),
          num('season', l10n.seasonCoeff, last: true),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            isExpanded: true,
            initialValue: _method,
            decoration: InputDecoration(labelText: l10n.method),
            items: [for (final m in _earthMethods) DropdownMenuItem(value: m, child: Text(m))],
            onChanged: (v) => setState(() => _method = v!),
          ),
          if (_node?.attrs['role'] == 'repeat') ...[
            const SizedBox(height: 12),
            Text(l10n.scope),
            _chips<String?>(
              const ['single', 'total'],
              _scope,
              (v) => v == 'total' ? l10n.scopeTotal : l10n.scopeSingle,
              (v) => _scope = v,
            ),
          ],
        ];
      case MeasurementType.continuityBonding:
        return [
          num('bond', l10n.bondR, last: true),
          const SizedBox(height: 12),
          TextField(
            controller: _ctrl('bond.from'),
            decoration: InputDecoration(labelText: l10n.bondFrom),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _ctrl('bond.to'),
            decoration: InputDecoration(labelText: l10n.bondTo),
          ),
        ];
    }
  }

  Widget _lastResult(AppLocalizations l10n) {
    final m = _last!;
    final reason = m.evalDetail['reason'] as String?;
    final checks = (m.evalDetail['checks'] as List?)?.whereType<Map<Object?, Object?>>() ?? const [];
    final limit = checks.where((c) => c['norm_id'] == m.normId).firstOrNull?['limit'];
    return Card(
      key: const Key('measure.result'),
      shape: RoundedRectangleBorder(
        side: BorderSide(color: VerdictChip.colorOf(m.verdict), width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.lastResult(_lastLabel ?? ''), style: const TextStyle(color: ZanjirColors.inkMuted)),
            const SizedBox(height: 8),
            VerdictChip(m.verdict, large: true),
            if (reason != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(l10n.reasonText(reason))),
            if (limit is num) Text(l10n.limitLabel(formatDecimal(limit))),
            if (m.normId != null) Text(m.normId!, style: const TextStyle(color: ZanjirColors.inkMuted)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final err = _loadError;
    if (err != null)
      return Scaffold(
        appBar: AppBar(),
        body: Center(child: Text(l10n.loadError('$err'))),
      );
    final node = _node;
    final closed = _session?.closedAt != null;
    final instrument = _instruments.where((i) => i.id == _instrumentId).firstOrNull;
    final instrumentValid = instrument != null && instrumentVerificationValid(instrument, ref.read(clockProvider)());

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.measureTitle),
        actions: [
          IconButton(
            tooltip: l10n.summaryTitle,
            icon: const Icon(Icons.fact_check),
            onPressed: () => context.push('/sessions/${widget.sessionId}'),
          ),
        ],
      ),
      body: node == null
          ? Center(child: Text(l10n.emptyGraph))
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (closed) Text(l10n.sessionClosed, style: const TextStyle(color: ZanjirColors.danger)),
                if (_last != null) _lastResult(l10n),
                Row(
                  children: [
                    IconButton(
                      tooltip: l10n.previousPoint,
                      icon: const Icon(Icons.chevron_left),
                      onPressed: () => setState(() => _selectNode((_index - 1 + _nodes.length) % _nodes.length)),
                    ),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        isExpanded: true,
                        key: const Key('measure.point'),
                        initialValue: _index,
                        decoration: InputDecoration(labelText: l10n.point),
                        items: [
                          for (var i = 0; i < _nodes.length; i++)
                            DropdownMenuItem(
                              value: i,
                              child: Text('${_nodes[i].label} · ${l10n.kindName(_nodes[i].kind)}'),
                            ),
                        ],
                        onChanged: (i) => setState(() => _selectNode(i!)),
                      ),
                    ),
                    IconButton(
                      tooltip: l10n.nextPoint,
                      icon: const Icon(Icons.chevron_right),
                      onPressed: () => setState(() => _selectNode((_index + 1) % _nodes.length)),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(l10n.measurementType),
                _chips<MeasurementType>(MeasurementType.values, _type, l10n.typeName, (t) {
                  _type = t;
                  _resetInputs();
                }),
                const SizedBox(height: 12),
                if (_instruments.isEmpty)
                  Text(l10n.noInstruments, style: const TextStyle(color: ZanjirColors.warn))
                else
                  DropdownButtonFormField<String>(
                    isExpanded: true,
                    initialValue: _instrumentId,
                    decoration: InputDecoration(labelText: l10n.instrument),
                    items: [
                      for (final i in _instruments)
                        DropdownMenuItem(value: i.id, child: Text('${i.model} · ${i.serialNo}')),
                    ],
                    onChanged: (v) => setState(() => _instrumentId = v),
                  ),
                if (instrument != null && !instrumentValid)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(l10n.instrumentExpired, style: const TextStyle(color: ZanjirColors.warn)),
                  ),
                if (_supersedesId != null)
                  Padding(padding: const EdgeInsets.only(top: 8), child: Text(l10n.supersedeHint)),
                const SizedBox(height: 8),
                ..._fields(l10n),
                const SizedBox(height: 16),
                FilledButton.icon(
                  key: const Key('measure.save'),
                  onPressed: closed || _saving || _instrumentId == null ? null : _save,
                  icon: const Icon(Icons.save),
                  label: Text(l10n.saveMeasurement),
                ),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: closed || _saving || _instrumentId == null ? null : _notApplicable,
                  child: Text(l10n.notApplicable),
                ),
              ],
            ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}
