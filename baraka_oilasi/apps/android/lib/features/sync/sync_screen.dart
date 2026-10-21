import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/debt_widgets.dart';
import '../../shared/files.dart';
import '../../shared/widgets.dart';
import '../setup/setup_screen.dart' show pickFileProvider;

/// Yadrodagi chegara bilan bir xil (`MIN_PASSWORD_CHARS`) — faqat tugmani faollashtirish uchun.
const _minPassword = 8;
const barakaMime = 'application/octet-stream';

String _when(String? iso) =>
    iso == null ? '—' : iso.substring(0, iso.length < 16 ? iso.length : 16).replaceAll('T', ' ');

String _tableLabel(BuildContext context, String table) =>
    context.tr.has('sync.table.$table') ? context.t('sync.table.$table') : table;

/// `.baraka` almashish (8.3–8.5): qurilmalar, shifrlangan eksport, import oldidan ko'rinish va
/// ziddiyatlarni tanlash, yangi qurilmani ulash. Birlashtirish qoidalari yadroda.
class SyncScreen extends ConsumerWidget {
  const SyncScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final role = ref.watch(query(['deviceRole'], (c) => c.deviceRole())).valueOrNull;
    final owner = (role?.role ?? 'OWNER') == 'OWNER';
    return ScreenBody(
      mentorKey: 'mentor.sync',
      children: [
        Card(
          color: context.palette.sidebar,
          child: Padding(padding: const EdgeInsets.all(16), child: Text(context.t('sync.intro'))),
        ),
        _Devices(owner: owner),
        const _Export(),
        const _Import(),
        if (owner) const _Pairing() else SectionCard(children: [Hint(context.t('sync.roleNote'))]),
      ],
    );
  }
}

class _Devices extends ConsumerStatefulWidget {
  const _Devices({required this.owner});

  final bool owner;

  @override
  ConsumerState<_Devices> createState() => _DevicesState();
}

class _DevicesState extends ConsumerState<_Devices> with ActionState {
  /// Bekor qilish — ikki bosqichda (tasdiq shu yerning o'zida).
  String? _confirm;

  @override
  Widget build(BuildContext context) {
    final q = ref.watch(query(['devices'], (c) => c.devices()));
    final list = q.valueOrNull ?? <DeviceDto>[];
    return SectionCard(
      title: context.t('sync.devices'),
      children: [
        if (q.hasError) ErrorText(q.error),
        for (final d in list)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(d.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                    Hint('· ${d.platform}'),
                    if (d.isThis) Tag(context.t('sync.thisDevice'), tone: 'accent'),
                    if (d.role != null)
                      Tag(
                        '${context.t('sync.role.${d.role}')}${d.revoked ? ' · ${context.t('sync.revoked')}' : ''}',
                        key: Key('device-role-${d.name}'),
                      ),
                  ],
                ),
                if (!d.isThis)
                  Hint(
                    '${context.t('sync.lastImport')}: ${_when(d.lastImportAt)} · ${context.t('sync.lastExport')}: ${_when(d.lastExportAt)}',
                  ),
                if (widget.owner && d.role != null && !d.revoked && _confirm == d.id)
                  Wrap(
                    spacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(context.t('sync.revokeConfirm'), style: TextStyle(color: context.palette.warn)),
                      OutlinedButton(
                        onPressed: busy
                            ? null
                            : () async {
                                final r = await act(() => ref.read(coreProvider).revokeDevice(deviceId: d.id));
                                if (r != null) setState(() => _confirm = null);
                              },
                        child: Text(context.t('sync.revokeYes')),
                      ),
                      TextButton(
                        onPressed: () => setState(() => _confirm = null),
                        child: Text(context.t('common.cancel')),
                      ),
                    ],
                  )
                else if (widget.owner && d.role != null && !d.revoked)
                  TextButton(
                    onPressed: () => setState(() => _confirm = d.id),
                    child: Text(context.t('sync.revoke')),
                  ),
              ],
            ),
          ),
        ErrorText(error),
        if (list.where((d) => !d.isThis).isEmpty) Hint(context.t('sync.noPeers')),
      ],
    );
  }
}

class _Export extends ConsumerStatefulWidget {
  const _Export();

  @override
  ConsumerState<_Export> createState() => _ExportState();
}

class _ExportState extends ConsumerState<_Export> with ActionState {
  String _mode = 'FULL';
  String? _peer;
  final _pw = TextEditingController();
  final _pw2 = TextEditingController();
  int? _exported;

  @override
  void initState() {
    super.initState();
    _pw.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _pw.dispose();
    _pw2.dispose();
    super.dispose();
  }

  Future<void> _run(List<DeviceDto> peers) async {
    final share = ref.read(shareFileProvider);
    final r = await act(() async {
      if (_pw.text != _pw2.text) throw const AppError(code: 'PASSWORD_MISMATCH', field: 'password');
      final f = await ref
          .read(coreProvider)
          .exportBaraka(
            input: ExportInput(
              password: _pw.text,
              mode: _mode,
              peerDeviceId: _mode == 'INCREMENTAL' ? _peer ?? peers.firstOrNull?.id : null,
            ),
          );
      await share(f.bytes, f.fileName, barakaMime);
      return f.rows;
    });
    if (r != null) {
      _pw.clear();
      _pw2.clear();
      setState(() => _exported = r);
    }
  }

  @override
  Widget build(BuildContext context) {
    final peers = (ref.watch(query(['devices'], (c) => c.devices())).valueOrNull ?? [])
        .where((d) => !d.isThis)
        .toList();
    return SectionCard(
      title: context.t('sync.export'),
      children: [
        for (final m in ['FULL', 'INCREMENTAL'])
          if (m == 'FULL' || peers.isNotEmpty)
            ChoiceTile(
              label: context.t('sync.mode.$m'),
              hint: context.t('sync.modeHint.$m'),
              selected: _mode == m,
              onTap: () => setState(() {
                _mode = m;
                _exported = null;
              }),
            ),
        if (_mode == 'INCREMENTAL')
          Select<String>(
            label: context.t('sync.forDevice'),
            items: [for (final d in peers) (d.id, d.name)],
            value: _peer ?? peers.firstOrNull?.id,
            onChanged: (v) => setState(() => _peer = v),
          ),
        const SizedBox(height: 8),
        Field(label: context.t('sync.password'), controller: _pw, obscure: true),
        const SizedBox(height: 8),
        Field(label: context.t('sync.passwordRepeat'), controller: _pw2, obscure: true),
        const SizedBox(height: 4),
        Hint(context.t('sync.passwordHint')),
        ErrorText(error),
        if (_exported != null)
          Text(context.t('sync.exported', {'count': _exported}), style: TextStyle(color: context.palette.accentText)),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(
            onPressed: busy || _pw.text.length < _minPassword ? null : () => _run(peers),
            child: Text(context.t('sync.saveFile')),
          ),
        ),
      ],
    );
  }
}

class _Import extends ConsumerStatefulWidget {
  const _Import();

  @override
  ConsumerState<_Import> createState() => _ImportState();
}

class _ImportState extends ConsumerState<_Import> with ActionState {
  ({String name, Uint8List bytes})? _file;
  final _pw = TextEditingController();
  final _choices = <String, String>{};
  ImportPreviewDto? _pv;
  ImportResultDto? _applied;

  @override
  void initState() {
    super.initState();
    _pw.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _pw.dispose();
    super.dispose();
  }

  Future<void> _pick() async {
    final f = await act(() => ref.read(pickFileProvider)());
    if (f != null) {
      setState(() {
        _file = f;
        _pv = null;
        _applied = null;
        _choices.clear();
      });
    }
  }

  Future<void> _inspect() async {
    setState(() {
      _applied = null;
      _choices.clear();
    });
    final pv = await act(() => ref.read(coreProvider).inspectBaraka(file: _file!.bytes, password: _pw.text));
    if (pv != null) setState(() => _pv = pv);
  }

  Future<void> _apply() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .applyBaraka(
            file: _file!.bytes,
            password: _pw.text,
            choices: [for (final e in _choices.entries) ConflictChoiceInput(key: e.key, choice: e.value)],
          ),
    );
    if (r != null) {
      _pw.clear();
      setState(() {
        _applied = r;
        _pv = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final pv = _pv;
    final applied = _applied;
    final unresolved = pv == null ? 0 : pv.conflicts.where((c) => !_choices.containsKey(c.key)).length;
    return SectionCard(
      title: context.t('sync.import'),
      children: [
        Row(
          children: [
            OutlinedButton(onPressed: busy ? null : _pick, child: Text(context.t('sync.pickFile'))),
            const SizedBox(width: 12),
            Expanded(child: Hint(_file?.name ?? context.t('sync.noFile'))),
          ],
        ),
        if (_file != null) ...[
          const SizedBox(height: 8),
          Field(label: context.t('sync.password'), controller: _pw, obscure: true),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: busy || _pw.text.isEmpty ? null : _inspect,
              child: Text(context.t('sync.inspect')),
            ),
          ),
        ],
        ErrorText(error),
        if (pv != null) ...[
          _Preview(pv: pv, choices: _choices, onChoose: (k, c) => setState(() => _choices[k] = c)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              FilledButton(
                onPressed: !pv.canApply || unresolved > 0 || busy ? null : _apply,
                child: Text(context.t('sync.apply')),
              ),
              if (unresolved > 0)
                Text(
                  context.t('sync.unresolved', {'count': unresolved}),
                  style: TextStyle(color: context.palette.warn),
                ),
            ],
          ),
        ],
        if (applied != null)
          Text(
            [
              context.t('sync.applied', {
                'inserted': applied.inserted,
                'updated': applied.updated,
                'journal': applied.journalAppended,
                'conflicts': applied.conflictsLocal + applied.conflictsRemote,
              }),
              if (applied.rejected > 0) context.t('sync.appliedRejected', {'count': applied.rejected}),
            ].join(' '),
            key: const Key('sync-applied'),
            style: TextStyle(color: context.palette.accentText),
          ),
      ],
    );
  }
}

class _Preview extends StatelessWidget {
  const _Preview({required this.pv, required this.choices, required this.onChoose});

  final ImportPreviewDto pv;
  final Map<String, String> choices;
  final void Function(String key, String choice) onChoose;

  Widget _box(BuildContext context, Color c, List<Widget> children) => Container(
    margin: const EdgeInsets.only(top: 8),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      border: Border.all(color: c),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
  );

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        Text(
          '${context.t('sync.from', {'name': pv.sourceDeviceName, 'date': _when(pv.exportedAt)})} · ${context.t('sync.mode.${pv.mode}')}',
        ),
        ValueRow(context.t('sync.count.inserts'), '${pv.inserts}'),
        ValueRow(context.t('sync.count.updates'), '${pv.updates}'),
        ValueRow(context.t('sync.count.journal'), '${pv.journalAppended}'),
        ValueRow(context.t('sync.count.same'), '${pv.same + pv.keptLocal}'),
        if (pv.forks.isNotEmpty)
          _box(context, p.danger, [
            Text(
              context.t('sync.forkTitle'),
              style: TextStyle(color: p.danger, fontWeight: FontWeight.w700),
            ),
            for (final f in pv.forks) Text(context.t('sync.fork.${f.reason}', {'title': f.title, 'seq': f.seq})),
            Hint(context.t('sync.forkHint')),
          ]),
        if (pv.protected.isNotEmpty)
          _box(context, p.warn, [
            Text(
              context.t('sync.protectedTitle', {'count': pv.protected.length}),
              style: TextStyle(color: p.warn, fontWeight: FontWeight.w700),
            ),
            for (final x in pv.protected)
              Hint('${_tableLabel(context, x.table)}: ${x.label.isEmpty ? x.rowId : x.label}'),
          ]),
        if (pv.rejected.isNotEmpty)
          _box(context, p.warn, [
            Text(
              context.t('sync.rejectedTitle', {'count': pv.rejected.length}),
              key: const Key('sync-rejected'),
              style: TextStyle(color: p.warn, fontWeight: FontWeight.w700),
            ),
            Hint(context.t('sync.rejectedHint')),
            for (final x in pv.rejected)
              Text(
                '${_tableLabel(context, x.table)}: ${x.label.isEmpty ? x.rowId : x.label} — ${context.t('error.${x.reason}')}',
              ),
          ]),
        if (pv.ignored > 0) Hint(context.t('sync.ignored', {'count': pv.ignored})),
        if (pv.conflicts.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            context.t('sync.conflictsTitle', {'count': pv.conflicts.length}),
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          Hint(context.t('sync.conflictsHint')),
          for (final c in pv.conflicts)
            _box(context, p.warn, [
              Text('${_tableLabel(context, c.table)}: ${c.label.isEmpty ? c.rowId : c.label}'),
              if (c.localDeleted != c.remoteDeleted)
                _diff(
                  context,
                  context.t('sync.state'),
                  context.t(c.localDeleted ? 'sync.deleted' : 'sync.kept'),
                  context.t(c.remoteDeleted ? 'sync.deleted' : 'sync.kept'),
                ),
              for (final f in c.fields.where((f) => f.field != 'deleted_at'))
                _diff(
                  context,
                  context.tr.has('sync.col.${f.field}') ? context.t('sync.col.${f.field}') : f.field,
                  f.local,
                  f.remote,
                ),
              SegmentedChoice<String>(
                label: context.t('sync.choose'),
                options: [
                  for (final x in ['LOCAL', 'REMOTE']) (x, context.t('sync.keep.$x')),
                ],
                value: choices[c.key],
                onChanged: (x) => onChoose(c.key, x),
              ),
            ]),
        ],
        if (pv.conflicts.isEmpty && pv.forks.isEmpty)
          Text(context.t('sync.noConflicts'), style: TextStyle(color: p.accentText)),
      ],
    );
  }

  Widget _diff(BuildContext context, String field, String local, String remote) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Hint(field),
        Text('${context.t('sync.local')}: $local'),
        Text('${context.t('sync.remote')}: $remote'),
      ],
    ),
  );
}

class _Pairing extends ConsumerStatefulWidget {
  const _Pairing();

  @override
  ConsumerState<_Pairing> createState() => _PairingState();
}

class _PairingState extends ConsumerState<_Pairing> with ActionState {
  PairingOfferDto? _view;
  String _role = 'FAMILY';
  String? _space;

  @override
  Widget build(BuildContext context) {
    final spaces = ref.watch(query(['household'], (c) => c.household())).valueOrNull?.spaces ?? [];
    final businesses = spaces.where((s) => s.kind == 'KASBKOR').toList();
    // Uydagi oila qurilmasi (ADR-0004) — Musofir makoniga bog'lanadi.
    final musofirs = spaces.where((s) => s.kind == 'MUSOFIR').toList();
    final targets = _role == 'HOME' ? musofirs : businesses;
    final view = _view;
    final p = context.palette;
    return SectionCard(
      title: context.t('sync.pairing'),
      children: [
        Hint(context.t('sync.pairingHint')),
        ErrorText(error),
        if (view != null) ...[
          const SizedBox(height: 8),
          Text(context.t('sync.pairingSaved', {'file': view.fileName})),
          if (_role != 'FAMILY')
            Text(
              context.t('sync.pairingFor.$_role'),
              key: const Key('pairing-role'),
              style: TextStyle(color: p.accentText),
            ),
          const SizedBox(height: 8),
          Hint(context.t('sync.pairingCode')),
          SelectableText(
            view.code,
            key: const Key('pairing-code'),
            style: const TextStyle(fontSize: 20, letterSpacing: 2, fontFamily: 'monospace'),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => Clipboard.setData(ClipboardData(text: view.code)),
              icon: const Icon(Icons.copy),
              label: Text(context.t('common.copy')),
            ),
          ),
          Hint(context.t('sync.pairingSteps')),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => setState(() => _view = null),
              child: Text(context.t('common.close')),
            ),
          ),
        ] else ...[
          const SizedBox(height: 8),
          for (final r in ['FAMILY', 'HOME', 'SELLER', 'ACCOUNTANT'])
            if (r == 'FAMILY' || (r == 'HOME' ? musofirs : businesses).isNotEmpty)
              ChoiceTile(
                label: context.t('sync.pairRole.$r'),
                hint: context.t('sync.pairRoleHint.$r'),
                selected: _role == r,
                onTap: () => setState(() {
                  _role = r;
                  _space = null;
                }),
              ),
          if (_role != 'FAMILY' && targets.length > 1)
            Select<String>(
              label: context.t('sync.pairSpace'),
              items: [for (final b in targets) (b.id, b.name)],
              value: _space ?? targets.firstOrNull?.id,
              onChanged: (v) => setState(() => _space = v),
            ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: busy
                  ? null
                  : () async {
                      final share = ref.read(shareFileProvider);
                      final v = await act(() async {
                        final o = await ref
                            .read(coreProvider)
                            .pairingOffer(
                              input: _role == 'FAMILY'
                                  ? const PairingInput()
                                  : PairingInput(role: _role, spaceId: _space ?? targets.firstOrNull?.id),
                            );
                        await share(o.bytes, o.fileName, barakaMime);
                        return o;
                      });
                      if (v != null) setState(() => _view = v);
                    },
              child: Text(context.t('sync.pairingStart')),
            ),
          ),
        ],
      ],
    );
  }
}
