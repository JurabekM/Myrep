import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../home/home_screen.dart' show ReminderText;
import '../partnership/partnerships_screen.dart' show PartnershipView;

/// To'rtta shablon (uy/SPEC 2F.10) va erkin kelishuv. Bandlar matni — i18n'dan boshlang'ich qiymat.
const _templates = ['CHORES', 'MONEY_PLACE', 'WANT_LIMIT', 'COUNCIL', 'OTHER'];
const _templateItems = 3;
const _types = ['ALL', 'PARTNERSHIP', 'FAMILY', 'LOAN'];
const _sorts = ['title', 'nextReview', 'openIncidents', 'openDisputes'];

/// Kelishuvlar markazi (D13A): barcha kelishuvlar — turi, holati, keyingi ko'rik, ochiq hodisa va
/// nizolar; filtr, qidiruv va saralash. Oilaviy kelishuvlar shu yerda yaratiladi va kattalar
/// tasdiqlaydi.
class AgreementsScreen extends StatefulWidget {
  const AgreementsScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  State<AgreementsScreen> createState() => _AgreementsScreenState();
}

class _AgreementsScreenState extends State<AgreementsScreen> {
  String _view = 'center';

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
        child: SegmentedChoice<String>(
          label: '',
          options: [
            for (final x in ['center', 'family']) (x, context.t('agreements.tab.$x')),
          ],
          value: _view,
          onChanged: (v) => setState(() => _view = v),
        ),
      ),
      Expanded(
        child: _view == 'center'
            ? _Center(spaceId: widget.spaceId, onFamily: () => setState(() => _view = 'family'))
            : _Family(spaceId: widget.spaceId),
      ),
    ],
  );
}

class _Center extends ConsumerStatefulWidget {
  const _Center({required this.spaceId, required this.onFamily});

  final String spaceId;
  final VoidCallback onFamily;

  @override
  ConsumerState<_Center> createState() => _CenterState();
}

class _CenterState extends ConsumerState<_Center> {
  String _type = 'ALL';
  String _sort = 'title';
  final _search = TextEditingController();

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _open(AgreementSummaryDto a) {
    if (a.agreementType == 'PARTNERSHIP') {
      final tab = a.status == 'DRAFT' || a.status == 'SIGNED' ? 'contract' : 'governance';
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => PartnershipView(spaceId: widget.spaceId, id: a.refId, initialTab: tab),
        ),
      );
    } else if (a.agreementType == 'FAMILY') {
      widget.onFamily();
    }
  }

  /// Saralash — faqat ko'rsatish tartibi (matn, sana, son); pul hisoblanmaydi.
  int _compare(AgreementSummaryDto a, AgreementSummaryDto b) => switch (_sort) {
    // Sanasizlari oxirida.
    'nextReview' => (a.nextReview ?? '9999').compareTo(b.nextReview ?? '9999'),
    'openIncidents' => b.openIncidents.compareTo(a.openIncidents),
    'openDisputes' => b.openDisputes.compareTo(a.openDisputes),
    _ => a.title.toLowerCase().compareTo(b.title.toLowerCase()),
  };

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final q = ref.watch(query(['agreements', sid], (c) => c.agreementsCenter(spaceId: sid)));
    final needle = _search.text.trim().toLowerCase();
    final rows = [
      for (final a in q.valueOrNull ?? const <AgreementSummaryDto>[])
        if ((_type == 'ALL' || a.agreementType == _type) && a.title.toLowerCase().contains(needle)) a,
    ]..sort(_compare);
    return ScreenBody(
      mentorKey: 'mentor.agreements',
      children: [
        Select<String>(
          label: context.t('agreements.filter'),
          items: [for (final x in _types) (x, context.t('agreements.type.$x'))],
          value: _type,
          onChanged: (v) => setState(() => _type = v ?? _type),
        ),
        Field(label: context.t('agreements.search'), controller: _search, onChanged: (_) => setState(() {})),
        Select<String>(
          label: context.t('agreements.sort'),
          items: [
            for (final x in _sorts)
              (
                x,
                context.t(
                  'agreements.col.${x == 'openIncidents'
                      ? 'incidents'
                      : x == 'openDisputes'
                      ? 'disputes'
                      : x}',
                ),
              ),
          ],
          value: _sort,
          onChanged: (v) => setState(() => _sort = v ?? _sort),
        ),
        if (q.hasError) ErrorText(q.error),
        if (q.hasValue && rows.isEmpty) Hint(context.t('agreements.empty')),
        for (final a in rows) _AgreementCard(a, onTap: () => _open(a)),
      ],
    );
  }
}

class _AgreementCard extends StatelessWidget {
  const _AgreementCard(this.a, {required this.onTap});

  final AgreementSummaryDto a;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    final statusColor = switch (a.status) {
      'ACTIVE' => pal.accentText,
      'IN_DISPUTE' => pal.danger,
      _ => pal.inkMuted,
    };
    Text count(int n, Color tone) => Text(
      '$n',
      style: TextStyle(color: n > 0 ? tone : pal.inkMuted, fontFeatures: const [FontFeature.tabularFigures()]),
    );
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(a.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: '${context.t('agreements.type.${a.agreementType}')} · ',
                      style: TextStyle(color: pal.inkMuted),
                    ),
                    TextSpan(
                      text: context.t('agreements.status.${a.status}'),
                      style: TextStyle(color: statusColor),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: Hint(
                      '${context.t('agreements.col.nextReview')}: '
                      '${a.nextReview == null ? '—' : showDate(a.nextReview!)}',
                    ),
                  ),
                ],
              ),
              if (a.reminder != null) ReminderText(a.reminder!),
              const SizedBox(height: 4),
              Wrap(
                spacing: 16,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Hint('${context.t('agreements.col.incidents')}: '),
                      count(a.openIncidents, pal.warn),
                    ],
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Hint('${context.t('agreements.col.disputes')}: '),
                      count(a.openDisputes, pal.danger),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Tahrirlanayotgan oilaviy kelishuv.
class _Draft {
  _Draft({
    required this.id,
    required this.templateKey,
    required String title,
    required List<String> items,
    this.reviewDate,
  }) : title = TextEditingController(text: title),
       items = [for (final i in items) TextEditingController(text: i)];

  final String? id;
  final String templateKey;
  final TextEditingController title;
  final List<TextEditingController> items;
  String? reviewDate;

  void dispose() {
    title.dispose();
    for (final c in items) {
      c.dispose();
    }
  }

  FamilyAgreementInput input() => FamilyAgreementInput(
    templateKey: templateKey,
    title: title.text,
    items: [for (final c in items) c.text],
    reviewDate: reviewDate,
  );
}

class _Family extends ConsumerStatefulWidget {
  const _Family({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_Family> createState() => _FamilyState();
}

class _FamilyState extends ConsumerState<_Family> with ActionState {
  _Draft? _draft;

  @override
  void dispose() {
    _draft?.dispose();
    super.dispose();
  }

  void _setDraft(_Draft? d) => setState(() {
    _draft?.dispose();
    _draft = d;
    error = null;
  });

  _Draft _fromTemplate(String k) => _Draft(
    id: null,
    templateKey: k,
    title: context.t('family.tpl.$k.title'),
    items: k == 'OTHER' ? [''] : [for (var i = 1; i <= _templateItems; i++) context.t('family.tpl.$k.item$i')],
  );

  Future<void> _save() async {
    final d = _draft!;
    final core = ref.read(coreProvider);
    final r = await act(
      () => d.id == null
          ? core.createFamilyAgreement(spaceId: widget.spaceId, input: d.input())
          : core.updateFamilyAgreement(spaceId: widget.spaceId, id: d.id!, input: d.input()),
    );
    if (r != null) _setDraft(null);
  }

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final list = ref.watch(query(['family', sid], (c) => c.familyAgreements(spaceId: sid)));
    final d = _draft;
    return ScreenBody(
      children: [
        Hint(context.t('family.intro')),
        if (d == null)
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final k in _templates)
                OutlinedButton(
                  onPressed: () => _setDraft(_fromTemplate(k)),
                  child: Text(context.t('family.tpl.$k.title')),
                ),
            ],
          )
        else
          SectionCard(
            title: context.t('family.edit'),
            children: [
              Field(label: context.t('family.titleField'), controller: d.title),
              const SizedBox(height: 12),
              Text(context.t('family.items')),
              for (final (i, c) in d.items.indexed)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: Field(label: context.t('family.itemN', {'n': i + 1}), controller: c, maxLines: 3),
                      ),
                      IconButton(
                        tooltip: context.t('family.removeItem', {'n': i + 1}),
                        icon: const Icon(Icons.close),
                        onPressed: () => setState(() => d.items.removeAt(i).dispose()),
                      ),
                    ],
                  ),
                ),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => setState(() => d.items.add(TextEditingController())),
                  icon: const Icon(Icons.add),
                  label: Text(context.t('family.addItem')),
                ),
              ),
              const SizedBox(height: 8),
              DateField(
                label: context.t('family.reviewDate'),
                value: d.reviewDate,
                onChanged: (v) => setState(() => d.reviewDate = v),
              ),
              if (d.id != null) ...[
                const SizedBox(height: 8),
                Text(context.t('family.editResets'), style: TextStyle(color: context.palette.warn)),
              ],
              ErrorText(error),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
                  TextButton(onPressed: () => _setDraft(null), child: Text(context.t('common.cancel'))),
                ],
              ),
            ],
          ),
        if (list.hasError) ErrorText(list.error),
        if ((list.valueOrNull?.isEmpty ?? false) && d == null) Hint(context.t('family.empty')),
        for (final f in list.valueOrNull ?? const <FamilyAgreementDto>[])
          _FamilyCard(
            key: ValueKey(f.id),
            spaceId: sid,
            f: f,
            onEdit: () => _setDraft(
              _Draft(id: f.id, templateKey: f.templateKey, title: f.title, items: f.items, reviewDate: f.reviewDate),
            ),
          ),
      ],
    );
  }
}

class _FamilyCard extends ConsumerStatefulWidget {
  const _FamilyCard({required this.spaceId, required this.f, required this.onEdit, super.key});

  final String spaceId;
  final FamilyAgreementDto f;
  final VoidCallback onEdit;

  @override
  ConsumerState<_FamilyCard> createState() => _FamilyCardState();
}

class _FamilyCardState extends ConsumerState<_FamilyCard> with ActionState {
  SignoffDto? _confirming;
  final _pin = TextEditingController();

  @override
  void dispose() {
    _pin.dispose();
    super.dispose();
  }

  Future<void> _confirm() async {
    final secret = await ref.read(sessionActionsProvider).secret();
    final r = await act(
      () => ref
          .read(coreProvider)
          .confirmFamilyAgreement(
            platformSecret: secret,
            spaceId: widget.spaceId,
            pin: _pin.text,
            id: widget.f.id,
            memberId: _confirming?.memberId ?? '',
          ),
    );
    _pin.clear();
    if (r != null) setState(() => _confirming = null);
  }

  Future<void> _remove() =>
      act(() => ref.read(coreProvider).deleteFamilyAgreement(spaceId: widget.spaceId, id: widget.f.id));

  @override
  Widget build(BuildContext context) {
    final f = widget.f;
    final pal = context.palette;
    final active = f.status == 'ACTIVE';
    final c = _confirming;
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: active ? pal.accent : pal.line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Semantics(
                    header: true,
                    child: Text(f.title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  ),
                ),
                Text(
                  context.t('family.status.${f.status}'),
                  style: TextStyle(color: active ? pal.accentText : pal.warn, fontSize: 14),
                ),
              ],
            ),
            const SizedBox(height: 8),
            for (final (i, it) in f.items.indexed)
              Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('${i + 1}. $it')),
            const SizedBox(height: 4),
            Hint(
              '${f.reviewDate == null ? context.t('family.noReview') : context.t('family.reviewOn', {'date': showDate(f.reviewDate!)})}'
              ' · ${context.t('partnership.hashCode', {'code': f.chainCode})}',
            ),
            const SizedBox(height: 8),
            for (final a in f.adults)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 4),
                decoration: BoxDecoration(
                  border: Border(bottom: BorderSide(color: pal.line)),
                ),
                child: Row(
                  children: [
                    Expanded(child: Text(a.name)),
                    if (a.agreedOn != null)
                      Text(
                        '✓ ${context.t('partnership.agreedOn', {'date': showDate(a.agreedOn!)})}',
                        style: TextStyle(color: pal.accentText, fontSize: 14),
                      )
                    else
                      TextButton(
                        onPressed: () => setState(() {
                          _confirming = a;
                          error = null;
                        }),
                        child: Text(context.t('family.confirmAs', {'name': a.name})),
                      ),
                  ],
                ),
              ),
            if (c != null)
              Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: pal.accent),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    PinField(
                      label: context.t('family.pinFor', {'name': c.name}),
                      controller: _pin,
                      onChanged: (_) => setState(() {}),
                    ),
                    Wrap(
                      spacing: 8,
                      children: [
                        FilledButton(
                          onPressed: busy || _pin.text.isEmpty ? null : _confirm,
                          child: Text(context.t('family.confirm')),
                        ),
                        TextButton(
                          onPressed: () => setState(() => _confirming = null),
                          child: Text(context.t('common.cancel')),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ErrorText(error),
            const SizedBox(height: 8),
            // «Ikki qirg'oq» (M2): matn musofirning shartlaridan — o'zgartirish faqat Musofir makonida.
            if (f.templateKey == 'REMITTANCE')
              Hint(context.t('family.remittanceNote'), key: const Key('family-remittance-note'))
            else
              Wrap(
                spacing: 8,
                children: [
                  OutlinedButton(onPressed: widget.onEdit, child: Text(context.t('family.editButton'))),
                  TextButton(onPressed: busy ? null : _remove, child: Text(context.t('family.delete'))),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
