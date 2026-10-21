import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

const _spaces = ['UY', 'KASBKOR', 'MUSOFIR'];
const rhythms = ['DAILY', 'ORDERS', 'MONTHLY'];

/// Onboarding qadamlari (≤ 5): til va yo'l → oila → daromad → qarzlar → PIN; keyin tiklash kodi.
enum _Step { language, family, income, debts, pin }

class _Member {
  _Member(this.key) : name = TextEditingController();
  final int key;
  final TextEditingController name;
  String role = 'ADULT';
}

/// Fayl tanlash (`.baraka`): testlarda almashtiriladi.
typedef PickFile = Future<({String name, Uint8List bytes})?> Function();

Future<({String name, Uint8List bytes})?> pickBarakaFile() async {
  final files = await FilePicker.pickFiles();
  if (files.isEmpty) return null;
  final f = files.single;
  return (name: f.name, bytes: await f.readAsBytes());
}

final pickFileProvider = Provider<PickFile>((ref) => pickBarakaFile);

class SetupScreen extends ConsumerStatefulWidget {
  const SetupScreen({super.key});

  @override
  ConsumerState<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends ConsumerState<SetupScreen> with ActionState {
  _Step _step = _Step.language;
  bool _joining = false;
  final _household = TextEditingController();
  final _name = TextEditingController();
  final _members = <_Member>[];
  final _chosen = <String>{'UY'};
  String? _rhythm;
  int _monthStartDay = 1;
  bool? _debts;
  final _pin = TextEditingController();
  final _pin2 = TextEditingController();
  bool _mismatch = false;
  SetupResult? _result;
  ({String name, Uint8List bytes})? _file;
  final _secret = TextEditingController();
  final _deviceName = TextEditingController(text: 'Telefon');

  @override
  void dispose() {
    for (final c in [_household, _name, _pin, _pin2, _secret, _deviceName, ..._members.map((m) => m.name)]) {
      c.dispose();
    }
    super.dispose();
  }

  bool get _canNext => switch (_step) {
    _Step.language => true,
    _Step.family =>
      _household.text.trim().isNotEmpty &&
          _name.text.trim().isNotEmpty &&
          _chosen.isNotEmpty &&
          _members.every((m) => m.name.text.trim().isNotEmpty),
    _Step.income => _rhythm != null,
    _Step.debts => _debts != null,
    _Step.pin => _pin.text.length == 6 && _pin2.text.length == 6,
  };

  Future<void> _submit() async {
    if (_step != _Step.pin && !_joining) {
      if (_canNext) setState(() => _step = _Step.values[_step.index + 1]);
      return;
    }
    setState(() => _mismatch = _pin.text != _pin2.text);
    if (_mismatch) return;
    final actions = ref.read(sessionActionsProvider);
    final locale = ref.read(localeProvider);
    final SetupResult? r;
    if (_joining) {
      final file = _file;
      if (file == null) return;
      r = await act(
        () => actions.join(
          _pin.text,
          file.bytes,
          JoinInput(secret: _secret.text.trim(), deviceName: _deviceName.text.trim(), platform: 'android'),
        ),
      );
    } else {
      r = await act(
        () => actions.setup(
          _pin.text,
          BootstrapInput(
            householdName: _household.text.trim(),
            deviceName: _deviceName.text.trim(),
            platform: 'android',
            locale: locale,
            baseCurrency: 'UZS',
            monthStartDay: _rhythm == 'MONTHLY' ? _monthStartDay : 1,
            spaces: [
              for (final s in _spaces)
                if (_chosen.contains(s)) s,
            ],
            members: [
              NewMemberInput(displayName: _name.text.trim(), role: 'ADULT'),
              for (final m in _members) NewMemberInput(displayName: m.name.text.trim(), role: m.role),
            ],
            incomeRhythm: _rhythm,
            debtsDeclared: _debts ?? false,
          ),
        ),
      );
    }
    if (r != null) setState(() => _result = r);
  }

  void _finish() {
    // «Qarzim bor» degan bo'lsa — birinchi ish: qarzlarni yozib chiqish.
    if (!_joining && (_debts ?? false)) ref.read(shellProvider.notifier).go('inventory');
    ref.read(sessionActionsProvider).finishSetup();
  }

  Future<void> _pick() async {
    final f = await act(() => ref.read(pickFileProvider)());
    if (f != null) setState(() => _file = f);
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final result = _result;
    if (result != null) return _recovery(context, result);
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            if (!_joining) ...[
              Text(
                context.t('setup.stepOf', {'n': _step.index + 1, 'total': _Step.values.length}),
                key: const Key('setup-progress'),
                style: TextStyle(color: p.inkMuted, fontSize: 14),
              ),
              const SizedBox(height: 4),
            ],
            Semantics(
              header: true,
              child: Text(
                _joining ? context.t('setup.join') : context.t('setup.step.${_step.name}'),
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
              ),
            ),
            if (!_joining) ...[
              const SizedBox(height: 8),
              ExcludeSemantics(
                child: Row(
                  children: [
                    for (final s in _Step.values)
                      Expanded(
                        child: Container(
                          height: 4,
                          margin: const EdgeInsets.symmetric(horizontal: 2),
                          decoration: BoxDecoration(
                            color: s.index <= _step.index ? p.accent : p.surface,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 20),
            ..._body(context),
            if (_mismatch)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(context.t('setup.pinMismatch'), style: TextStyle(color: p.danger)),
              ),
            ErrorText(error),
            const SizedBox(height: 16),
            Row(
              children: [
                if (_step.index > 0 || _joining) ...[
                  OutlinedButton(
                    onPressed: () => setState(() {
                      if (_joining) {
                        _joining = false;
                      } else {
                        _step = _Step.values[_step.index - 1];
                      }
                    }),
                    child: Text(context.t('setup.back')),
                  ),
                  const SizedBox(width: 8),
                ],
                Expanded(
                  child: FilledButton(
                    onPressed: busy || (_joining ? _file == null : !_canNext) ? null : _submit,
                    child: Text(
                      _joining
                          ? context.t('setup.joinSubmit')
                          : _step == _Step.pin
                          ? context.t('setup.submit')
                          : context.t('setup.next'),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(context.t('app.disclaimer'), style: TextStyle(color: p.inkMuted, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  List<Widget> _pinFields(BuildContext context) => [
    PinField(label: context.t('setup.pin'), controller: _pin, onChanged: (_) => setState(() {})),
    const SizedBox(height: 12),
    PinField(label: context.t('setup.pinRepeat'), controller: _pin2, onChanged: (_) => setState(() {})),
  ];

  List<Widget> _body(BuildContext context) {
    final p = context.palette;
    if (_joining) {
      return [
        Text(context.t('setup.joinHint'), style: TextStyle(color: p.inkMuted)),
        const SizedBox(height: 12),
        Row(
          children: [
            OutlinedButton(onPressed: busy ? null : _pick, child: Text(context.t('sync.pickFile'))),
            const SizedBox(width: 12),
            Expanded(
              child: Text(_file?.name ?? context.t('sync.noFile'), style: TextStyle(color: p.inkMuted)),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Field(label: context.t('setup.joinSecret'), controller: _secret),
        const SizedBox(height: 12),
        Field(label: context.t('setup.deviceName'), controller: _deviceName),
        const SizedBox(height: 12),
        ..._pinFields(context),
      ];
    }
    switch (_step) {
      case _Step.language:
        final locale = ref.watch(localeProvider);
        return [
          Text(context.t('setup.title'), style: const TextStyle(height: 1.4)),
          const SizedBox(height: 16),
          _legend(context.t('setup.language')),
          for (final l in locales)
            ChoiceTile(
              label: context.t('locale.$l'),
              selected: locale == l,
              onTap: () {
                ref.read(localeProvider.notifier).state = l;
                final prefs = ref.read(servicesProvider).prefs;
                prefs.write(prefs.read().copyWith(locale: l));
              },
            ),
          const SizedBox(height: 8),
          _legend(context.t('setup.path')),
          ChoiceTile(
            label: context.t('setup.create'),
            hint: context.t('setup.createHint'),
            selected: !_joining,
            onTap: () => setState(() => _joining = false),
          ),
          ChoiceTile(
            label: context.t('setup.join'),
            hint: context.t('setup.joinHint'),
            selected: _joining,
            onTap: () => setState(() => _joining = true),
          ),
        ];
      case _Step.family:
        return [
          Field(label: context.t('setup.household'), controller: _household, onChanged: (_) => setState(() {})),
          const SizedBox(height: 12),
          Field(label: context.t('setup.yourName'), controller: _name, onChanged: (_) => setState(() {})),
          const SizedBox(height: 16),
          _legend(context.t('setup.members')),
          Text(context.t('setup.membersHint'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
          const SizedBox(height: 8),
          for (final (i, m) in _members.indexed)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    child: Field(
                      label: context.t('setup.memberName', {'n': i + 2}),
                      controller: m.name,
                      onChanged: (_) => setState(() {}),
                    ),
                  ),
                  const SizedBox(width: 8),
                  DropdownButton<String>(
                    value: m.role,
                    items: [
                      for (final r in ['ADULT', 'CHILD']) DropdownMenuItem(value: r, child: Text(context.t('role.$r'))),
                    ],
                    onChanged: (v) => setState(() => m.role = v ?? 'ADULT'),
                  ),
                  IconButton(
                    tooltip: context.t('setup.memberRemove', {'name': m.name.text.isEmpty ? i + 2 : m.name.text}),
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(() {
                      _members.remove(m);
                      m.name.dispose();
                    }),
                  ),
                ],
              ),
            ),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => setState(() => _members.add(_Member(DateTime.now().microsecondsSinceEpoch))),
              child: Text('+ ${context.t('setup.memberAdd')}'),
            ),
          ),
          const SizedBox(height: 16),
          _legend(context.t('setup.spaces')),
          for (final s in _spaces)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: _chosen.contains(s),
              title: Text(context.t('space.$s')),
              onChanged: (v) => setState(() => v ?? false ? _chosen.add(s) : _chosen.remove(s)),
            ),
        ];
      case _Step.income:
        return [
          _legend(context.t('setup.rhythm')),
          for (final r in rhythms)
            ChoiceTile(
              label: context.t('rhythm.$r'),
              hint: context.t('rhythmHint.$r'),
              selected: _rhythm == r,
              onTap: () => setState(() => _rhythm = r),
            ),
          if (_rhythm == 'MONTHLY')
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: DropdownButtonFormField<int>(
                initialValue: _monthStartDay,
                decoration: InputDecoration(labelText: context.t('setup.payday')),
                items: [for (var d = 1; d <= 28; d++) DropdownMenuItem(value: d, child: Text('$d'))],
                onChanged: (v) => setState(() => _monthStartDay = v ?? 1),
              ),
            ),
        ];
      case _Step.debts:
        return [
          _legend(context.t('setup.debtsQuestion')),
          ChoiceTile(
            label: context.t('setup.debtsYes'),
            hint: context.t('setup.debtsYesHint'),
            selected: _debts ?? false,
            onTap: () => setState(() => _debts = true),
          ),
          ChoiceTile(
            label: context.t('setup.debtsNo'),
            selected: _debts == false,
            onTap: () => setState(() => _debts = false),
          ),
          const SizedBox(height: 8),
          Text(context.t('setup.debtsPrivacy'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
        ];
      case _Step.pin:
        return [
          Text(context.t('setup.pinHint'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
          const SizedBox(height: 12),
          ..._pinFields(context),
        ];
    }
  }

  Widget _legend(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(text, style: const TextStyle(fontWeight: FontWeight.w700)),
  );

  Widget _recovery(BuildContext context, SetupResult result) {
    final p = context.palette;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Semantics(
              header: true,
              child: Text(
                context.t('setup.recoveryTitle'),
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(height: 16),
            Text(context.t('setup.recoveryHint'), style: const TextStyle(height: 1.4)),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: SelectableText(
                  result.recoveryCode,
                  key: const Key('recovery-code'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 20, letterSpacing: 2, fontFamily: 'monospace'),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => Clipboard.setData(ClipboardData(text: result.recoveryCode)),
                icon: const Icon(Icons.copy),
                label: Text(context.t('common.copy')),
              ),
            ),
            Text(context.t('setup.backupHint'), style: TextStyle(color: p.inkMuted, fontSize: 14)),
            const SizedBox(height: 20),
            FilledButton(onPressed: _finish, child: Text(context.t('setup.recoveryDone'))),
          ],
        ),
      ),
    );
  }
}
