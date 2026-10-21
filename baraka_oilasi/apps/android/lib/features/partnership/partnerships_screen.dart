import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/debt_widgets.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/json.dart';
import '../../shared/signature_pad.dart';
import '../../shared/widgets.dart';
import '../governance/governance_view.dart';
import '../venture/ideas_screen.dart' show percentToBp;
import '../venture/ledger_view.dart';

const partnershipKinds = ['MUDARABA', 'MUSHARAKA'];
const partyRoles = ['CAPITAL_PROVIDER', 'WORKER', 'BOTH'];
const capitalKinds = ['MONEY', 'EQUIPMENT'];

/// Kunlar, oylar, birliklar — butun son (pul emas).
int _count(String v, String field) {
  if (!RegExp(r'^\d{1,4}$').hasMatch(v.trim())) throw AppError(code: 'INVALID_NUMBER', field: field);
  return int.parse(v.trim());
}

String _bpText(int bp) {
  final frac = bp % 100;
  if (frac == 0) return '${bp ~/ 100}';
  return '${bp ~/ 100},${frac.toString().padLeft(2, '0').replaceAll(RegExp(r'0$'), '')}';
}

bool _empty(List<String> v) => v.every((x) => x.trim().isEmpty);

// ---- Forma holati (desktop `Form` bilan bir xil) ----

class _Ans<T> {
  _Ans(this.value, {this.mode = 'ANSWERED', this.reason = ''});

  String mode;
  T value;
  String reason;

  bool get na => mode == 'NOT_APPLICABLE';

  /// `Answer<T>` JSON: javob, asosli «tegishli emas» yoki javobsiz.
  Js toJson(bool Function(T v) isEmpty, Object? Function(T v) build) {
    if (na) return {'status': 'NOT_APPLICABLE', 'reason': reason};
    return isEmpty(value) ? {'status': 'UNANSWERED'} : {'status': 'ANSWERED', 'value': build(value)};
  }

  static _Ans<F> from<F>(Js a, F fallback, F Function(Object? v) map) => switch (a.s('status')) {
    'ANSWERED' => _Ans(map(a['value'])),
    'NOT_APPLICABLE' => _Ans(fallback, mode: 'NOT_APPLICABLE', reason: a.s('reason')),
    _ => _Ans(fallback),
  };
}

class _Capital {
  _Capital({this.kind = 'MONEY', this.description = '', this.amount = ''});

  String kind;
  String description;
  String amount;
}

class _Party {
  _Party(this.id, this.role, {this.isMe = false});

  final String id;
  String fullName = '';
  String role;
  String share = '50';
  bool isMe;
  List<_Capital> capital = [];
}

class _Duty {
  _Duty(this.id);

  final String id;
  String title = '';
  String owner = '';
  String breach = '';
}

class _Buyout {
  String seller = '';
  String buyer = '';
  String units = '10';
  String per = '1';
  String period = '1';
  String? start;
  String profit = '';
}

class _Form {
  String kind = 'MUDARABA';
  String title = '';
  List<_Party> parties = [_Party('P1', 'CAPITAL_PROVIDER'), _Party('P2', 'WORKER', isMe: true)];
  String profitMode = 'SHARE';
  String fixed = '';
  _Ans<List<_Duty>> duties = _Ans([_Duty('d1')]);
  String negligence = '';
  _Ans<({String location, String keeper, String review})> custody = _Ans((location: '', keeper: '', review: '30'));
  _Ans<({String notice, String valuation, String payout, String assets})> exit = _Ans((
    notice: '30',
    valuation: '',
    payout: '',
    assets: '',
  ));
  _Ans<({String name, String role})> arbiter = _Ans((name: '', role: ''));
  _Ans<({String? from, String months, String? review})> term = _Ans((from: null, months: '12', review: null));
  List<String> witnesses = [''];
  _Buyout? buyout;

  String _input() => jsonEncode({
    'kind': kind,
    'title': title,
    'parties': [
      for (final p in parties)
        {
          'id': p.id,
          'fullName': p.fullName,
          'role': p.role,
          'profitShareBp': percentToBp(p.share, field: 'profitShareBp'),
          'isMe': p.isMe,
          'capital': p.role == 'WORKER'
              ? <Js>[]
              : [
                  for (final c in p.capital) {'kind': c.kind, 'description': c.description, 'amount': c.amount},
                ],
        },
    ],
    'fixedReturn': profitMode == 'FIXED' ? fixed : null,
    'duties': duties.toJson(
      (d) => d.every((x) => _empty([x.title, x.breach])),
      (d) => [
        for (final x in d)
          if (!_empty([x.title, x.breach]))
            {
              'id': x.id,
              'title': x.title,
              'ownerPartyId': x.owner.isEmpty ? null : x.owner,
              'breachClause': x.breach.isEmpty ? null : x.breach,
            },
      ],
    ),
    'negligenceClause': negligence.trim().isEmpty ? null : negligence,
    'custody': custody.toJson(
      (c) => _empty([c.location, c.keeper]),
      (c) => {
        'location': c.location,
        'keeperPartyId': c.keeper,
        'reviewEveryDays': _count(c.review, 'reviewEveryDays'),
        'keeperDeviceId': null,
      },
    ),
    'exitClause': exit.toJson(
      (e) => _empty([e.valuation, e.payout]),
      (e) => {
        'noticeDays': _count(e.notice, 'noticeDays'),
        'valuationMethod': e.valuation,
        'payoutTerms': e.payout,
        'assetSplit': e.assets.isEmpty ? null : e.assets,
      },
    ),
    'arbiter': arbiter.toJson(
      (a) => _empty([a.name]),
      (a) => {'fullName': a.name, 'role': a.role.isEmpty ? null : a.role, 'partyId': null},
    ),
    'term': term.toJson(
      (x) => x.from == null && x.review == null,
      (x) => {
        'effectiveFrom': x.from ?? '',
        'durationMonths': x.months.trim().isEmpty ? null : _count(x.months, 'durationMonths'),
        'reviewDate': x.review ?? '',
      },
    ),
    'witnesses': witnesses,
    'buyout': buyout == null
        ? null
        : {
            'sellerPartyId': buyout!.seller,
            'buyerPartyId': buyout!.buyer,
            'units': _count(buyout!.units, 'units'),
            'unitsPerPeriod': _count(buyout!.per, 'unitsPerPeriod'),
            'periodMonths': _count(buyout!.period, 'periodMonths'),
            'start': buyout!.start ?? '',
            'expectedProfit': buyout!.profit.trim().isEmpty ? null : buyout!.profit,
          },
  });

  static _Form fromDto(Js p) {
    final b = _Form()
      ..kind = p.s('kind')
      ..title = p.s('title')
      ..parties = [
        for (final x in p.l('parties'))
          _Party(x.s('id'), x.s('role'), isMe: x.b('isMe'))
            ..fullName = x.s('fullName')
            ..share = _bpText(x.i('profitShareBp'))
            ..capital = [
              for (final c in x.l('capitalItems'))
                _Capital(kind: c.s('kind'), description: c.s('description'), amount: c.plain('amount')),
            ],
      ]
      ..negligence = p.s('negligenceClause')
      ..witnesses = p.ls('witnesses').isEmpty ? [''] : p.ls('witnesses');
    final blank = _Form();
    b
      ..duties = _Ans.from(p.m('duties'), blank.duties.value, (v) {
        return [
          for (final x in (v! as List).cast<Js>())
            _Duty(x.s('id'))
              ..title = x.s('title')
              ..owner = x.s('ownerPartyId')
              ..breach = x.s('breachClause'),
        ];
      })
      ..custody = _Ans.from(p.m('custody'), blank.custody.value, (v) {
        final c = v! as Js;
        return (location: c.s('location'), keeper: c.s('keeperPartyId'), review: '${c.i('reviewEveryDays')}');
      })
      ..exit = _Ans.from(p.m('exitClause'), blank.exit.value, (v) {
        final e = v! as Js;
        return (
          notice: '${e.i('noticeDays')}',
          valuation: e.s('valuationMethod'),
          payout: e.s('payoutTerms'),
          assets: e.s('assetSplit'),
        );
      })
      ..arbiter = _Ans.from(p.m('arbiter'), blank.arbiter.value, (v) {
        final a = v! as Js;
        return (name: a.s('fullName'), role: a.s('role'));
      })
      ..term = _Ans.from(p.m('term'), blank.term.value, (v) {
        final x = v! as Js;
        final months = x.io('durationMonths');
        return (from: x.so('effectiveFrom'), months: months == null ? '' : '$months', review: x.so('reviewDate'));
      });
    final bo = p.mo('buyout');
    if (bo != null) {
      b.buyout = _Buyout()
        ..seller = bo.s('sellerPartyId')
        ..buyer = bo.s('buyerPartyId')
        ..units = '${bo.i('units')}'
        ..per = '${bo.i('unitsPerPeriod')}'
        ..period = '${bo.i('periodMonths')}'
        ..start = bo.so('start')
        ..profit = bo.mo('expectedProfit')?.s('plain') ?? '';
    }
    return b;
  }
}

// ---- Ro'yxat ----

/// 5-qonun: «Pulni halol ishga sol» (uy/SPEC 2E). Sheriklik — qarz ham, sadaqa ham emas: teng
/// huquqli kelishuv. Shartnoma 9 savol bo'yicha yoziladi, shu qurilmada imzolanadi.
class PartnershipsScreen extends ConsumerStatefulWidget {
  const PartnershipsScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<PartnershipsScreen> createState() => _PartnershipsScreenState();
}

class _PartnershipsScreenState extends ConsumerState<PartnershipsScreen> {
  @override
  void initState() {
    super.initState();
    // Eslatma yoki «Hunardan ishga»dan kelgan bo'lsa — darhol shu sheriklik ochiladi.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final focus = ref.read(shellProvider).focus;
      if (focus != null && mounted) {
        ref.read(shellProvider.notifier).clearFocus();
        _open(focus['id'], focus['tab'] ?? 'contract');
      }
    });
  }

  void _open(String? id, [String tab = 'contract']) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => PartnershipView(spaceId: widget.spaceId, id: id, initialTab: tab),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final list = ref.watch(query(['partnerships', id], (c) => c.partnerships(spaceId: id)));
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.partnerships',
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: () => _open(null), child: Text(context.t('partnership.new'))),
        ),
        Card(
          color: p.sidebar,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(context.t('partnership.intro')),
                const SizedBox(height: 6),
                Hint(context.t('partnership.regulatory')),
              ],
            ),
          ),
        ),
        if (list.hasError) ErrorText(list.error),
        if (list.valueOrNull?.isEmpty ?? false) Hint(context.t('partnership.empty')),
        for (final x in list.valueOrNull ?? <PartnershipSummaryDto>[])
          Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              title: Text(x.title, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Hint(
                      '${context.t('partnership.kind.${x.kind}')}${x.myRole == null ? '' : ' · ${context.t('partnership.myRole.${x.myRole}')}'}',
                    ),
                    Hint(context.t('partnership.progress', {'n': x.answered})),
                    _StatusTag(x.status),
                    if (x.inDispute) Tag(context.t('partnership.inDispute'), tone: 'danger'),
                  ],
                ),
              ),
              trailing: Text(
                x.capitalTotal.formatted,
                style: TextStyle(color: p.accentText, fontWeight: FontWeight.w700),
              ),
              onTap: () => _open(x.id),
            ),
          ),
      ],
    );
  }
}

class _StatusTag extends StatelessWidget {
  const _StatusTag(this.status);

  final String status;

  @override
  Widget build(BuildContext context) =>
      Tag(context.t('partnership.status.$status'), tone: status == 'ACTIVE' ? 'accent' : 'muted');
}

// ---- Bitta sheriklik ----

/// Sheriklik: shartnoma ustasi (9 savol, imzolar, boshlash); faol bo'lsa — kassa daftari va ijro.
class PartnershipView extends ConsumerStatefulWidget {
  const PartnershipView({required this.spaceId, required this.id, this.initialTab = 'contract', super.key});

  final String spaceId;
  final String? id;
  final String initialTab;

  @override
  ConsumerState<PartnershipView> createState() => _PartnershipViewState();
}

class _PartnershipViewState extends ConsumerState<PartnershipView> with ActionState {
  late String? _id = widget.id;
  _Form? _form;
  Js? _dto;
  int _step = 1;
  int _rev = 0;
  late String _tab = widget.initialTab;

  @override
  void initState() {
    super.initState();
    if (_id == null) _form = _Form();
  }

  void _loaded(Js dto) => setState(() {
    _dto = dto;
    _id = dto.s('id');
    _form = _Form.fromDto(dto);
    _rev++;
  });

  Future<bool> _save() async {
    final core = ref.read(coreProvider);
    final f = _form!;
    final r = await act(() async {
      final input = f._input();
      final id = _id;
      return decodeJs(
        id == null
            ? await core.createPartnership(spaceId: widget.spaceId, inputJson: input)
            : await core.updatePartnership(spaceId: widget.spaceId, partnershipId: id, inputJson: input),
      );
    });
    if (r != null) _loaded(r);
    return r != null;
  }

  void _set(VoidCallback f) => setState(f);

  @override
  Widget build(BuildContext context) {
    final id = _id;
    if (id != null) {
      final q = ref.watch(
        query(
          ['partnership', widget.spaceId, id],
          (c) async => decodeJs(await c.partnership(spaceId: widget.spaceId, partnershipId: id)),
        ),
      );
      final fresh = q.valueOrNull;
      if (fresh != null && !identical(fresh, _dto)) {
        _dto = fresh;
        if (_form == null) {
          _form = _Form.fromDto(fresh);
          _rev++;
        }
      }
      if (_form == null) {
        return Scaffold(
          appBar: AppBar(),
          body: AsyncView(value: q, data: (_) => const SizedBox.shrink()),
        );
      }
    }
    final p = _dto;
    final f = _form!;
    final status = p?.s('status');
    final tabs = p != null && (status == 'ACTIVE' || status == 'CLOSED');
    final body = !tabs || _tab == 'contract'
        ? _contract(context, f, p)
        : _tab == 'ledger'
        ? LedgerView(spaceId: widget.spaceId, partnershipId: id!)
        : GovernanceView(
            spaceId: widget.spaceId,
            partnershipId: id!,
            // Yangilash yoki hakam qaroridan keyin — shartnoma yangi versiyadan qayta o'qiladi.
            onOpenContract: () => setState(() {
              _tab = 'contract';
              _step = 10;
              if (_dto != null) _form = _Form.fromDto(_dto!);
              _rev++;
            }),
          );
    return Scaffold(
      appBar: AppBar(
        title: Text(f.title.isEmpty ? context.t('partnership.new') : f.title),
        bottom: tabs
            ? PreferredSize(
                preferredSize: const Size.fromHeight(48),
                child: Row(
                  children: [
                    for (final t in ['contract', 'ledger', 'governance'])
                      Expanded(
                        child: InkWell(
                          onTap: () => setState(() => _tab = t),
                          child: Container(
                            height: 48,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              border: Border(
                                bottom: BorderSide(
                                  color: _tab == t ? context.palette.accent : context.palette.line,
                                  width: _tab == t ? 2 : 1,
                                ),
                              ),
                            ),
                            child: Semantics(
                              selected: _tab == t,
                              child: Text(context.t('partnership.tab.$t')),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              )
            : null,
      ),
      body: body,
    );
  }

  Widget _contract(BuildContext context, _Form f, Js? p) {
    final pal = context.palette;
    final locked = p?.s('status') == 'CLOSED';
    final fixedBlocked = f.profitMode == 'FIXED';
    final missing = p?.m('check').li('missing');
    return ScreenBody(
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (p != null) _StatusTag(p.s('status')),
            if (p?.io('version') != null) Hint(context.t('partnership.versionNo', {'n': p!.i('version')})),
            Hint(context.t('partnership.progress', {'n': p?.m('check').i('answered') ?? 0})),
          ],
        ),
        if (p != null && p.b('inDispute')) _note(context, pal.danger, context.t('gov.inDispute')),
        if (p?.s('templateReview') == 'PENDING') _note(context, pal.warn, context.t('partnership.reviewPending')),
        if (p != null && p.b('amendmentPending'))
          _note(context, pal.warn, context.t('partnership.amendmentPending', {'n': p.i('signedVersion')})),
        // Qadamlar: gorizontal tanlov (telefon uchun).
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              for (var s = 1; s <= 11; s++)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: ChoiceChip(
                    selected: _step == s,
                    label: Text(
                      '${s <= 9 ? ((missing?.contains(s) ?? true) ? '○ ' : '● ') : ''}$s. ${context.t('partnership.step.$s')}',
                    ),
                    onSelected: (_) => setState(() => _step = s),
                  ),
                ),
            ],
          ),
        ),
        if (_step <= 9)
          SectionCard(
            title: '$_step. ${context.t('partnership.q.$_step')}',
            children: [
              KeyedSubtree(
                key: ValueKey('step-$_step-$_rev'),
                child: _QuestionStep(step: _step, form: f, set: _set, dto: p),
              ),
              if (fixedBlocked && _step == 4)
                Text(context.t('partnership.fixedBlocked'), style: TextStyle(color: pal.danger)),
              ErrorText(error),
              if (!locked) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    FilledButton(
                      onPressed: busy || fixedBlocked ? null : _save,
                      child: Text(context.t('common.save')),
                    ),
                    if (_step < 9)
                      OutlinedButton(
                        onPressed: busy || fixedBlocked
                            ? null
                            : () async {
                                if (await _save()) setState(() => _step++);
                              },
                        child: Text(context.t('partnership.saveNext')),
                      ),
                  ],
                ),
              ],
            ],
          ),
        if (_step == 10 && p == null) Hint(context.t('partnership.saveFirst')),
        if (_step == 10 && p != null) _SignStep(spaceId: widget.spaceId, p: p, onDto: _loaded),
        if (_step == 11 && p == null) Hint(context.t('partnership.saveFirst')),
        if (_step == 11 && p != null) _StartStep(spaceId: widget.spaceId, p: p, onDto: _loaded),
        if (p != null && _step <= 9) _CheckPanel(p),
      ],
    );
  }

  Widget _note(BuildContext context, Color c, String text) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      border: Border.all(color: c),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Text(text),
  );
}

/// Matn maydoni (forma holati qadam o'zgarganda qayta quriladi).
Widget _tf(
  String label,
  String value,
  ValueChanged<String> onChanged, {
  TextInputType? keyboard,
  String? hint,
  int maxLines = 1,
}) => TextFormField(
  initialValue: value,
  onChanged: onChanged,
  keyboardType: keyboard,
  maxLines: maxLines,
  decoration: InputDecoration(labelText: label, hintText: hint),
);

const _gap = SizedBox(height: 12);

/// «Javob» yoki asosli «Tegishli emas» (izoh majburiy, 2F.2).
class _NaToggle<T> extends StatelessWidget {
  const _NaToggle({required this.a, required this.onChanged});

  final _Ans<T> a;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      SegmentedChoice<String>(
        label: '',
        options: [
          for (final m in ['ANSWERED', 'NOT_APPLICABLE']) (m, context.t('partnership.mode.$m')),
        ],
        value: a.mode,
        onChanged: (m) {
          a.mode = m;
          onChanged();
        },
      ),
      if (a.na) ...[
        _gap,
        _tf(context.t('partnership.naReason'), a.reason, (v) => a.reason = v),
      ],
      _gap,
    ],
  );
}

class _QuestionStep extends StatelessWidget {
  const _QuestionStep({required this.step, required this.form, required this.set, required this.dto});

  final int step;
  final _Form form;
  final void Function(VoidCallback) set;
  final Js? dto;

  Widget _partySelect(BuildContext context, String label, String value, ValueChanged<String> onChanged) =>
      Select<String>(
        label: label,
        items: [
          ('', context.t('partnership.choose')),
          for (final p in form.parties) (p.id, p.fullName.isEmpty ? p.id : p.fullName),
        ],
        value: value,
        onChanged: (v) => set(() => onChanged(v ?? '')),
      );

  @override
  Widget build(BuildContext context) {
    final f = form;
    final p = context.palette;
    final children = <Widget>[];
    switch (step) {
      case 1:
        children
          ..add(_tf(context.t('partnership.name'), f.title, (v) => set(() => f.title = v)))
          ..add(_gap);
        for (final k in partnershipKinds) {
          children.add(
            ChoiceTile(
              label: context.t('partnership.kind.$k'),
              hint: context.t('partnership.kindHint.$k'),
              selected: f.kind == k,
              onTap: dto?.s('status') == 'ACTIVE' ? () {} : () => set(() => f.kind = k),
            ),
          );
        }
        for (final (i, party) in f.parties.indexed) {
          children.add(
            Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: p.line),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _tf(context.t('partnership.partyName', {'id': party.id}), party.fullName, (v) => party.fullName = v),
                  _gap,
                  Select<String>(
                    label: context.t('partnership.role'),
                    items: [for (final r in partyRoles) (r, context.t('partnership.role.$r'))],
                    value: party.role,
                    onChanged: (v) => set(() => party.role = v ?? party.role),
                  ),
                  Row(
                    children: [
                      Expanded(
                        child: CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          value: party.isMe,
                          title: Text(context.t('partnership.isMe')),
                          onChanged: (_) => set(() {
                            for (final (j, x) in f.parties.indexed) {
                              x.isMe = j == i;
                            }
                          }),
                        ),
                      ),
                      if (f.parties.length > 2)
                        TextButton(
                          onPressed: () => set(() => f.parties.removeAt(i)),
                          child: Text(context.t('partnership.remove')),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          );
        }
        children.add(
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              onPressed: () => set(() {
                var n = f.parties.length + 1;
                while (f.parties.any((x) => x.id == 'P$n')) {
                  n++;
                }
                f.parties.add(_Party('P$n', 'BOTH'));
              }),
              child: Text('+ ${context.t('partnership.addParty')}'),
            ),
          ),
        );
      case 2:
        for (final party in f.parties) {
          if (party.role == 'WORKER') {
            children.add(
              Hint(context.t('partnership.laborOnly', {'name': party.fullName.isEmpty ? party.id : party.fullName})),
            );
            continue;
          }
          final total = dto?.l('parties').where((x) => x.s('id') == party.id).firstOrNull;
          children.add(
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: p.line),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    party.fullName.isEmpty ? party.id : party.fullName,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  for (final (k, c) in party.capital.indexed) ...[
                    _gap,
                    Select<String>(
                      label: context.t('partnership.capitalKind'),
                      items: [for (final ck in capitalKinds) (ck, context.t('partnership.capital.$ck'))],
                      value: c.kind,
                      onChanged: (v) => set(() => c.kind = v ?? c.kind),
                    ),
                    _gap,
                    _tf(context.t('partnership.capitalWhat'), c.description, (v) => c.description = v),
                    _gap,
                    _tf(
                      context.t(c.kind == 'EQUIPMENT' ? 'partnership.agreedPrice' : 'common.amount'),
                      c.amount,
                      (v) => c.amount = v,
                      keyboard: const TextInputType.numberWithOptions(decimal: true),
                    ),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => set(() => party.capital.removeAt(k)),
                        child: Text(context.t('partnership.remove')),
                      ),
                    ),
                  ],
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      onPressed: () => set(() => party.capital.add(_Capital())),
                      child: Text('+ ${context.t('partnership.addCapital')}'),
                    ),
                  ),
                  if (total != null) Hint(context.t('partnership.capitalTotal', {'amount': total.money('capital')})),
                ],
              ),
            ),
          );
        }
      case 3:
        children.add(_NaToggle(a: f.duties, onChanged: () => set(() {})));
        if (!f.duties.na) {
          children.add(Hint(context.t('partnership.dutiesHint')));
          for (final d in f.duties.value) {
            children.add(
              Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: p.line),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _tf(context.t('partnership.dutyTitle'), d.title, (v) => d.title = v),
                    _gap,
                    _partySelect(context, context.t('partnership.dutyOwner'), d.owner, (v) => d.owner = v),
                    _gap,
                    _tf(
                      context.t('partnership.breach'),
                      d.breach,
                      (v) => d.breach = v,
                      hint: context.t('partnership.breachPlaceholder'),
                    ),
                  ],
                ),
              ),
            );
          }
          children.add(
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: () => set(() => f.duties.value.add(_Duty('d${f.duties.value.length + 1}'))),
                child: Text('+ ${context.t('partnership.addDuty')}'),
              ),
            ),
          );
        }
      case 4:
        for (final m in ['SHARE', 'FIXED']) {
          children.add(
            ChoiceTile(
              label: context.t('partnership.profitMode.$m'),
              selected: f.profitMode == m,
              onTap: () => set(() => f.profitMode = m),
            ),
          );
        }
        if (f.profitMode == 'FIXED') {
          children.add(
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: p.danger),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    context.t('error.GUARANTEED_RETURN_FORBIDDEN'),
                    style: TextStyle(color: p.danger, fontWeight: FontWeight.w700),
                  ),
                  Text(context.t('partnership.fixedExplain')),
                ],
              ),
            ),
          );
        } else {
          for (final party in f.parties) {
            children
              ..add(
                _tf(
                  context.t('partnership.shareOf', {'name': party.fullName.isEmpty ? party.id : party.fullName}),
                  party.share,
                  (v) => party.share = v,
                  keyboard: const TextInputType.numberWithOptions(decimal: true),
                ),
              )
              ..add(_gap);
          }
        }
        children.add(Hint(context.t('partnership.shareHint')));
      case 5:
        children.add(Text(context.t('partnership.loss.${f.kind}')));
        if (dto != null) {
          for (final x in dto!.l('parties')) {
            children.add(ValueRow(x.s('fullName'), x.so('lossShare') ?? '—'));
          }
        }
        if (f.kind == 'MUDARABA') {
          children
            ..add(_gap)
            ..add(
              _tf(context.t('partnership.negligence'), f.negligence, (v) => f.negligence = v, maxLines: 3),
            );
        }
      case 6:
        final c = f.custody;
        children.add(_NaToggle(a: c, onChanged: () => set(() {})));
        if (!c.na) {
          children.addAll([
            _tf(
              context.t('partnership.custodyWhere'),
              c.value.location,
              (v) => c.value = (location: v, keeper: c.value.keeper, review: c.value.review),
            ),
            _gap,
            _partySelect(
              context,
              context.t('partnership.keeper'),
              c.value.keeper,
              (v) => c.value = (location: c.value.location, keeper: v, review: c.value.review),
            ),
            _gap,
            _tf(
              context.t('partnership.reviewDays'),
              c.value.review,
              (v) => c.value = (location: c.value.location, keeper: c.value.keeper, review: v),
              keyboard: TextInputType.number,
            ),
          ]);
        }
      case 7:
        children.add(_ExitStep(form: f, set: set, dto: dto, partySelect: _partySelect));
      case 8:
        final a = f.arbiter;
        children.add(_NaToggle(a: a, onChanged: () => set(() {})));
        if (!a.na) {
          children.addAll([
            _tf(context.t('partnership.arbiter'), a.value.name, (v) => a.value = (name: v, role: a.value.role)),
            _gap,
            _tf(context.t('partnership.arbiterRole'), a.value.role, (v) => a.value = (name: a.value.name, role: v)),
          ]);
        }
        children.addAll([
          _gap,
          Hint(context.t('partnership.arbiterHint')),
          _gap,
          Text(context.t('partnership.witnesses'), style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final (k, w) in f.witnesses.indexed) ...[
            _gap,
            _tf(context.t('partnership.witnessN', {'n': k + 1}), w, (v) => f.witnesses[k] = v),
          ],
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              onPressed: () => set(() => f.witnesses.add('')),
              child: Text('+ ${context.t('partnership.addWitness')}'),
            ),
          ),
        ]);
      case 9:
        final t = f.term;
        children.add(_NaToggle(a: t, onChanged: () => set(() {})));
        if (!t.na) {
          children.addAll([
            DateField(
              label: context.t('partnership.from'),
              value: t.value.from,
              onChanged: (v) => set(() => t.value = (from: v, months: t.value.months, review: t.value.review)),
            ),
            _gap,
            _tf(
              context.t('partnership.months'),
              t.value.months,
              (v) => t.value = (from: t.value.from, months: v, review: t.value.review),
              keyboard: TextInputType.number,
            ),
            _gap,
            DateField(
              label: context.t('partnership.reviewOn'),
              value: t.value.review,
              onChanged: (v) => set(() => t.value = (from: t.value.from, months: t.value.months, review: v)),
            ),
          ]);
        }
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children);
  }
}

class _ExitStep extends StatelessWidget {
  const _ExitStep({required this.form, required this.set, required this.dto, required this.partySelect});

  final _Form form;
  final void Function(VoidCallback) set;
  final Js? dto;
  final Widget Function(BuildContext, String, String, ValueChanged<String>) partySelect;

  @override
  Widget build(BuildContext context) {
    final e = form.exit;
    final b = form.buyout;
    void upd({String? notice, String? valuation, String? payout, String? assets}) => e.value = (
      notice: notice ?? e.value.notice,
      valuation: valuation ?? e.value.valuation,
      payout: payout ?? e.value.payout,
      assets: assets ?? e.value.assets,
    );
    final seller = form.parties.where((p) => p.role != 'WORKER' && !p.isMe).firstOrNull ?? form.parties.first;
    final buyer =
        form.parties.where((p) => p.id != seller.id && p.role != 'CAPITAL_PROVIDER').firstOrNull ??
        form.parties.elementAtOrNull(1);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _NaToggle(a: e, onChanged: () => set(() {})),
        if (!e.na) ...[
          _tf(context.t('partnership.notice'), e.value.notice, (v) => upd(notice: v), keyboard: TextInputType.number),
          _gap,
          _tf(context.t('partnership.valuation'), e.value.valuation, (v) => upd(valuation: v)),
          _gap,
          _tf(context.t('partnership.payout'), e.value.payout, (v) => upd(payout: v)),
          _gap,
          _tf(context.t('partnership.assets'), e.value.assets, (v) => upd(assets: v)),
          _gap,
        ],
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: b != null,
          title: Text(context.t('partnership.buyout'), style: const TextStyle(fontWeight: FontWeight.w700)),
          onChanged: (on) => set(
            () => form.buyout = on ?? false
                ? (_Buyout()
                    ..seller = seller.id
                    ..buyer = buyer?.id ?? '')
                : null,
          ),
        ),
        Hint(context.t('partnership.buyoutHint')),
        if (b != null) ...[
          _gap,
          partySelect(context, context.t('partnership.seller'), b.seller, (v) => b.seller = v),
          _gap,
          partySelect(context, context.t('partnership.buyer'), b.buyer, (v) => b.buyer = v),
          _gap,
          _tf(context.t('partnership.units'), b.units, (v) => b.units = v, keyboard: TextInputType.number),
          _gap,
          _tf(context.t('partnership.unitsPer'), b.per, (v) => b.per = v, keyboard: TextInputType.number),
          _gap,
          _tf(context.t('partnership.periodMonths'), b.period, (v) => b.period = v, keyboard: TextInputType.number),
          _gap,
          DateField(
            label: context.t('partnership.buyoutStart'),
            value: b.start,
            onChanged: (v) => set(() => b.start = v),
          ),
          _gap,
          _tf(
            context.t('partnership.expectedProfit'),
            b.profit,
            (v) => b.profit = v,
            keyboard: const TextInputType.numberWithOptions(decimal: true),
          ),
        ],
        if (dto?.mo('buyout') != null) ...[_gap, _BuyoutTable(dto!)],
      ],
    );
  }
}

/// Buyout jadvali va qolgan ulush (uy/SPEC 2E.2): kenglik yadro bergan bp dan.
class _BuyoutTable extends StatelessWidget {
  const _BuyoutTable(this.dto);

  final Js dto;

  @override
  Widget build(BuildContext context) {
    final b = dto.m('buyout');
    final p = context.palette;
    final err = b.so('error');
    if (err != null) {
      return Text(
        context.tr.has('error.$err') ? context.t('error.$err') : context.t('error.GENERIC'),
        style: TextStyle(color: p.danger),
      );
    }
    String name(String id) => dto.l('parties').where((x) => x.s('id') == id).firstOrNull?.s('fullName') ?? id;
    final rows = b.l('rows');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          context.t('partnership.buyoutSummary', {
            'buyer': name(b.s('buyerPartyId')),
            'seller': name(b.s('sellerPartyId')),
            'n': rows.length,
            'end': b.s('endDate'),
          }),
        ),
        if (b.mo('buyerProfit') != null) Hint(context.t('partnership.buyerProfit', {'amount': b.money('buyerProfit')})),
        const SizedBox(height: 6),
        Wrap(
          spacing: 12,
          children: [
            _legend(p.chart2, name(b.s('sellerPartyId')), p),
            _legend(p.chart1, name(b.s('buyerPartyId')), p),
          ],
        ),
        for (final r in rows)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(child: Text('${r.i('period')}. ${r.s('date')}')),
                    Text(
                      '${r.money('payment')}${r.b('exceedsShare') ? ' ⚠' : ''}',
                      style: TextStyle(color: r.b('exceedsShare') ? p.warn : null),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: SizedBox(
                    height: 10,
                    child: Row(
                      children: [
                        Expanded(
                          flex: r.i('sellerBp'),
                          child: ColoredBox(color: p.chart2),
                        ),
                        Expanded(
                          flex: r.i('buyerBp'),
                          child: ColoredBox(color: p.chart1),
                        ),
                      ],
                    ),
                  ),
                ),
                Hint('${r.s('sellerPercent')} / ${r.s('buyerPercent')}'),
              ],
            ),
          ),
        if (rows.any((r) => r.b('exceedsShare')))
          Text(context.t('partnership.exceedsShare'), style: TextStyle(color: p.warn)),
        Hint(context.t('partnership.buyoutPricing')),
      ],
    );
  }

  Widget _legend(Color c, String text, BarakaPalette p) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(width: 10, height: 10, color: c),
      const SizedBox(width: 6),
      Text(text, style: TextStyle(color: p.inkMuted, fontSize: 13)),
    ],
  );
}

class _CheckPanel extends StatelessWidget {
  const _CheckPanel(this.p);

  final Js p;

  @override
  Widget build(BuildContext context) {
    final check = p.m('check');
    final pal = context.palette;
    String label(String code) => context.tr.has('partnership.check.$code')
        ? context.t('partnership.check.$code')
        : (context.tr.has('error.$code') ? context.t('error.$code') : code);
    final errors = check.ls('errors');
    final warnings = check.ls('warnings');
    if (errors.isEmpty && warnings.isEmpty) {
      return check.b('canSign')
          ? Text(context.t('partnership.readyToSign'), style: TextStyle(color: pal.accentText))
          : const SizedBox.shrink();
    }
    return SectionCard(
      children: [
        for (final c in errors) Text('• ${label(c)}', style: TextStyle(color: pal.danger)),
        for (final c in warnings) Text('• ${label(c)}', style: TextStyle(color: pal.warn)),
      ],
    );
  }
}

class _SignStep extends ConsumerStatefulWidget {
  const _SignStep({required this.spaceId, required this.p, required this.onDto});

  final String spaceId;
  final Js p;
  final ValueChanged<Js> onDto;

  @override
  ConsumerState<_SignStep> createState() => _SignStepState();
}

class _SignStepState extends ConsumerState<_SignStep> with ActionState {
  Future<void> _sign(String key, String name) async {
    final strokes = await drawSignature(context, name);
    if (strokes == null) return;
    final r = await act(
      () async => decodeJs(
        await ref
            .read(coreProvider)
            .signPartnership(
              spaceId: widget.spaceId,
              partnershipId: widget.p.s('id'),
              inputJson: jsonEncode({'signerKey': key, 'strokes': strokes}),
            ),
      ),
    );
    if (r != null) widget.onDto(r);
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.p;
    final check = p.m('check');
    final pal = context.palette;
    return SectionCard(
      title: context.t('partnership.step.10'),
      children: [
        Hint(context.t('partnership.signHint')),
        if (!check.b('canSign')) Text(context.t('partnership.signBlocked'), style: TextStyle(color: pal.danger)),
        _CheckPanel(p),
        const SizedBox(height: 6),
        Text(
          '${p.io('version') != null ? context.t('partnership.versionNo', {'n': p.i('version')}) : context.t('partnership.newVersion')} · ${context.t('partnership.hashCode', {'code': p.s('hashCode')})}',
        ),
        for (final s in p.l('signers'))
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Hint(context.t('partnership.signer.${s.s('role')}')),
                      Text(s.s('name')),
                    ],
                  ),
                ),
                if (s.so('signedAt') != null) ...[
                  if (s.so('svg') != null)
                    Semantics(
                      label: context.t('partnership.signatureOf', {'name': s.s('name')}),
                      child: Container(
                        height: 40,
                        width: 100,
                        color: const Color(0xFFFAF9F5),
                        child: SvgPicture.string(s.s('svg')),
                      ),
                    ),
                  const SizedBox(width: 8),
                  Text('✓ ${s.s('signedAt')}', style: TextStyle(color: pal.accentText)),
                ] else if (p.s('status') != 'CLOSED')
                  OutlinedButton(
                    onPressed: !check.b('canSign') || busy ? null : () => _sign(s.s('key'), s.s('name')),
                    child: Text(context.t('partnership.signAs', {'name': s.s('name')})),
                  ),
              ],
            ),
          ),
        if (p.b('allSigned'))
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              context.t('partnership.allSigned', {'n': p.i('version')}),
              style: TextStyle(color: pal.accentText),
            ),
          ),
        ErrorText(error),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(
            onPressed: busy
                ? null
                : () => act(() async {
                    final bytes = await ref
                        .read(coreProvider)
                        .partnershipPdf(spaceId: widget.spaceId, partnershipId: p.s('id'));
                    await ref.read(shareFileProvider)(bytes, 'sheriklik.pdf', pdfMime);
                  }),
            child: Text(context.t('partnership.pdf')),
          ),
        ),
        if (p.l('history').isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(context.t('partnership.history'), style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final h in p.l('history'))
            Hint(
              [
                context.t('partnership.historyRow', {
                  'n': h.i('no'),
                  'date': h.s('createdOn'),
                  'signed': h.i('signed'),
                  'required': h.i('required'),
                }),
                if (h.b('inForce')) context.t('partnership.inForce'),
                if (h.so('changeNote') != null) context.t('partnership.changeNote.${h.s('changeNote')}'),
              ].join(' · '),
            ),
        ],
      ],
    );
  }
}

class _StartStep extends ConsumerStatefulWidget {
  const _StartStep({required this.spaceId, required this.p, required this.onDto});

  final String spaceId;
  final Js p;
  final ValueChanged<Js> onDto;

  @override
  ConsumerState<_StartStep> createState() => _StartStepState();
}

class _StartStepState extends ConsumerState<_StartStep> with ActionState {
  Future<void> _run(Future<String> Function(BarakaCore c, String sid, String pid) fn) async {
    final r = await act(() async => decodeJs(await fn(ref.read(coreProvider), widget.spaceId, widget.p.s('id'))));
    if (r != null) widget.onDto(r);
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.p;
    final pal = context.palette;
    final gate = p.mo('gate');
    final consent = p.mo('consent');
    final status = p.s('status');
    return SectionCard(
      title: context.t('partnership.step.11'),
      children: [
        if (p.b('meProvidesCapital')) ...[
          Hint(context.t('partnership.gateHint')),
          if (gate != null) ...[const SizedBox(height: 8), _GateCard(gate)],
        ],
        if (p.b('meReceivesCapital') && consent != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              border: Border.all(color: pal.accent.withValues(alpha: 0.4)),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(context.t('partnership.notDebt.title'), style: const TextStyle(fontWeight: FontWeight.w700)),
                Text(context.t('partnership.notDebt.${p.s('kind')}')),
                const SizedBox(height: 6),
                if (consent.so('notDebtAckOn') != null)
                  Text(
                    '✓ ${context.t('partnership.notDebt.acked', {'date': showDate(consent.s('notDebtAckOn'))})}',
                    style: TextStyle(color: pal.accentText),
                  )
                else
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton(
                      onPressed: busy
                          ? null
                          : () => _run((c, s, i) => c.acknowledgeNotDebt(spaceId: s, partnershipId: i)),
                      child: Text(context.t('partnership.notDebt.ack')),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Hint(context.t('partnership.consentHint')),
          for (final a in consent.l('adults'))
            Row(
              children: [
                Expanded(child: Text(a.s('name'))),
                if (a.so('agreedOn') != null)
                  Text(
                    '✓ ${context.t('partnership.agreedOn', {'date': showDate(a.s('agreedOn'))})}',
                    style: TextStyle(color: pal.accentText),
                  )
                else
                  OutlinedButton(
                    onPressed: status != 'SIGNED' || busy
                        ? null
                        : () => _run(
                            (c, s, i) => c.consentPartnership(spaceId: s, partnershipId: i, memberId: a.s('memberId')),
                          ),
                    child: Text(context.t('partnership.consentAs', {'name': a.s('name')})),
                  ),
              ],
            ),
        ],
        if (p.so('activateBlocker') != null && status != 'ACTIVE' && status != 'CLOSED')
          Text(context.t('partnership.blocker.${p.s('activateBlocker')}'), style: TextStyle(color: pal.warn)),
        ErrorText(error),
        const SizedBox(height: 8),
        if (status == 'SIGNED')
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton(
              onPressed: !p.b('canActivate') || busy
                  ? null
                  : () => _run((c, s, i) => c.activatePartnership(spaceId: s, partnershipId: i)),
              child: Text(context.t('partnership.activate')),
            ),
          ),
        if (status == 'ACTIVE') ...[
          Text(
            context.t('partnership.activeNote', {'n': p.i('signedVersion')}),
            style: TextStyle(color: pal.accentText),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: busy ? null : () => _run((c, s, i) => c.closePartnership(spaceId: s, partnershipId: i)),
              child: Text(context.t('partnership.close')),
            ),
          ),
        ],
      ],
    );
  }
}

class _GateCard extends StatelessWidget {
  const _GateCard(this.g);

  final Js g;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    final open = g.b('open');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: open ? pal.accent : pal.warn),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            context.t(open ? 'partnership.gate.open' : 'partnership.gate.closed'),
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          Text(
            g.so('coverageMonths') != null
                ? context.t('partnership.gate.coverage', {
                    'months': g.s('coverageMonths'),
                    'required': g.i('requiredMonths'),
                    'balance': g.money('balance'),
                    'essentials': g.mo('monthlyEssentials')?.s('formatted') ?? '',
                  })
                : context.t('partnership.gate.noHistory', {'balance': g.money('balance')}),
          ),
          for (final r in g.ls('reasons'))
            Text('• ${context.t('partnership.gate.reason.$r')}', style: TextStyle(color: pal.warn)),
        ],
      ),
    );
  }
}
