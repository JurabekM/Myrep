import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../home/home_screen.dart' show ReminderText;

const _reasons = ['SCHEDULED', 'PROFIT_SPIKE', 'EXTRA'];
const _clauses = [1, 2, 3, 4, 5, 6, 7, 8, 9];

String? _optional(String v) => v.trim().isEmpty ? null : v;

ProviderListenable<AsyncValue<GovernanceDto>> _gov(String sid, String id) =>
    query(['governance', sid, id], (c) => c.governance(spaceId: sid, partnershipId: id));

/// Chegarali blok (forma yoki ogohlantirish).
Widget _boxed(BuildContext context, Color color, List<Widget> children) => Container(
  margin: const EdgeInsets.only(top: 8),
  padding: const EdgeInsets.all(12),
  decoration: BoxDecoration(
    border: Border.all(color: color),
    borderRadius: BorderRadius.circular(8),
  ),
  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
);

/// 6-qonun ijrosi (uy/SPEC 2F): vazifalar va «bajara olmayapman», oylik ochiq hisob ko'rigi,
/// nizo va hakam, yillik yangilash. Hamma qoida yadroda — bu yerda faqat ko'rsatish va kiritish.
class GovernanceView extends ConsumerWidget {
  const GovernanceView({required this.spaceId, required this.partnershipId, required this.onOpenContract, super.key});

  final String spaceId;
  final String partnershipId;
  final VoidCallback onOpenContract;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final q = ref.watch(_gov(spaceId, partnershipId));
    final g = q.valueOrNull;
    if (g == null) {
      return q.hasError
          ? Padding(padding: const EdgeInsets.all(16), child: ErrorText(q.error))
          : const Center(child: CircularProgressIndicator());
    }
    final pal = context.palette;
    return ScreenBody(
      children: [
        if (g.inDispute) _boxed(context, pal.danger, [Text(context.t('gov.inDispute'))]),
        if (!g.writable)
          _boxed(context, pal.line, [
            Hint(context.t('venture.readOnly.${g.readOnlyReason ?? 'NOT_ACTIVE'}', {'name': ''})),
          ]),
        _Schedule(spaceId: spaceId, g: g, onOpenContract: onOpenContract),
        _Duties(spaceId: spaceId, g: g),
        SectionCard(
          title: context.t('gov.reviews'),
          children: [
            Hint(context.t('gov.reviewHint')),
            if (g.writable) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(
                  onPressed: () => pushScreen(
                    context,
                    context.t('gov.session'),
                    (_) => _ReviewSession(spaceId: spaceId, partnershipId: partnershipId),
                  ),
                  child: Text(context.t('gov.startReview')),
                ),
              ),
            ],
            const SizedBox(height: 8),
            if (g.reviews.isEmpty) Hint(context.t('gov.noReviews')) else _Reviews(spaceId: spaceId, g: g),
          ],
        ),
        _Disputes(spaceId: spaceId, g: g, onOpenContract: onOpenContract),
      ],
    );
  }
}

class _Schedule extends ConsumerStatefulWidget {
  const _Schedule({required this.spaceId, required this.g, required this.onOpenContract});

  final String spaceId;
  final GovernanceDto g;
  final VoidCallback onOpenContract;

  @override
  ConsumerState<_Schedule> createState() => _ScheduleState();
}

class _ScheduleState extends ConsumerState<_Schedule> with ActionState {
  bool _renewed = false;

  Future<void> _renew() async {
    final r = await act(
      () => ref.read(coreProvider).renewPartnership(spaceId: widget.spaceId, partnershipId: widget.g.partnershipId),
    );
    if (r != null) setState(() => _renewed = true);
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.g;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionCard(
          children: [
            Hint(context.t('gov.nextReview')),
            Text(
              g.nextReviewDue == null ? '—' : showDate(g.nextReviewDue!),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            Hint(context.t('gov.every', {'count': g.reviewEveryDays})),
            if (g.reviewReminder != null) ReminderText(g.reviewReminder!),
          ],
        ),
        SectionCard(
          children: [
            Hint(context.t('gov.renewal')),
            Text(
              g.reviewDate == null ? '—' : showDate(g.reviewDate!),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            if (g.renewalReminder != null) ReminderText(g.renewalReminder!),
            Hint(context.t('gov.renewalHint')),
            ErrorText(error),
            const SizedBox(height: 8),
            if (_renewed) ...[
              Semantics(
                liveRegion: true,
                child: Text(context.t('gov.renewed'), style: TextStyle(color: context.palette.accentText)),
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(onPressed: widget.onOpenContract, child: Text(context.t('gov.openContract'))),
              ),
            ] else if (g.status == 'ACTIVE' && g.reviewDate != null)
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(onPressed: busy ? null : _renew, child: Text(context.t('gov.renew'))),
              ),
          ],
        ),
      ],
    );
  }
}

class _Duties extends ConsumerStatefulWidget {
  const _Duties({required this.spaceId, required this.g});

  final String spaceId;
  final GovernanceDto g;

  @override
  ConsumerState<_Duties> createState() => _DutiesState();
}

class _DutiesState extends ConsumerState<_Duties> with ActionState {
  String? _dutyId;
  String _partyId = '';
  String _date = todayIso();
  final _reason = TextEditingController();
  final _solution = TextEditingController();
  IncidentDto? _reported;

  @override
  void dispose() {
    _reason.dispose();
    _solution.dispose();
    super.dispose();
  }

  void _start(DutyDto d) => setState(() {
    _reported = null;
    _dutyId = d.id;
    _partyId = d.ownerPartyId ?? widget.g.parties.firstOrNull?.partyId ?? '';
    _date = todayIso();
    _reason.clear();
    _solution.clear();
    error = null;
  });

  Future<void> _report() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .reportDutyIncident(
            spaceId: widget.spaceId,
            partnershipId: widget.g.partnershipId,
            input: IncidentInput(
              dutyId: _dutyId ?? '',
              partyId: _partyId,
              reason: _reason.text,
              occurredOn: _date,
              proposedSolution: _optional(_solution.text),
            ),
          ),
    );
    if (r == null) return;
    setState(() {
      _dutyId = null;
      _reported = r.incidents.firstOrNull;
    });
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.g;
    final pal = context.palette;
    final duty = g.duties.where((d) => d.id == _dutyId).firstOrNull;
    final reported = _reported;
    return SectionCard(
      title: context.t('gov.duties'),
      children: [
        if (g.duties.isEmpty) Hint(context.t('gov.noDuties')),
        for (final d in g.duties)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: pal.line)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(d.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                Hint('${context.t('gov.owner')}: ${d.ownerName ?? '—'}'),
                if (d.breachClause != null) Text('${context.t('gov.breachClause')}: ${d.breachClause}'),
                if (g.writable) TextButton(onPressed: () => _start(d), child: Text(context.t('gov.cannotDo'))),
              ],
            ),
          ),
        if (duty != null)
          _boxed(context, pal.warn, [
            Text(duty.title, style: const TextStyle(fontWeight: FontWeight.w700)),
            if (duty.breachClause != null)
              Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: '${context.t('gov.breachClause')}: ',
                      style: TextStyle(color: pal.warn),
                    ),
                    TextSpan(text: duty.breachClause),
                  ],
                ),
              ),
            const SizedBox(height: 12),
            Select<String>(
              label: context.t('gov.party'),
              items: [for (final p in g.parties) (p.partyId, p.name)],
              value: _partyId,
              onChanged: (v) => setState(() => _partyId = v ?? _partyId),
            ),
            const SizedBox(height: 12),
            DateField(
              label: context.t('gov.date'),
              value: _date,
              allowClear: false,
              onChanged: (v) => setState(() => _date = v ?? _date),
            ),
            const SizedBox(height: 12),
            Field(label: context.t('gov.reason'), controller: _reason),
            const SizedBox(height: 12),
            Field(label: context.t('gov.solution'), controller: _solution),
            ErrorText(error),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilledButton(onPressed: busy ? null : _report, child: Text(context.t('gov.report'))),
                TextButton(
                  onPressed: () => setState(() => _dutyId = null),
                  child: Text(context.t('common.cancel')),
                ),
              ],
            ),
          ]),
        if (reported != null)
          Semantics(
            liveRegion: true,
            child: _boxed(context, pal.accent, [
              Text(
                context.t('gov.reported', {'code': reported.chainCode}),
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              if (reported.breachClause != null)
                Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(text: '${context.t('gov.nowClause')} '),
                      TextSpan(
                        text: reported.breachClause,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                )
              else
                Hint(context.t('gov.noClause')),
            ]),
          ),
        if (g.incidents.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(context.t('gov.incidents'), style: const TextStyle(fontWeight: FontWeight.w700)),
          for (final i in g.incidents) _Incident(key: ValueKey(i.id), spaceId: widget.spaceId, g: g, i: i),
        ],
      ],
    );
  }
}

class _Incident extends ConsumerStatefulWidget {
  const _Incident({required this.spaceId, required this.g, required this.i, super.key});

  final String spaceId;
  final GovernanceDto g;
  final IncidentDto i;

  @override
  ConsumerState<_Incident> createState() => _IncidentState();
}

class _IncidentState extends ConsumerState<_Incident> with ActionState {
  TextEditingController? _note;

  @override
  void dispose() {
    _note?.dispose();
    super.dispose();
  }

  Future<void> _resolve() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .resolveDutyIncident(
            spaceId: widget.spaceId,
            partnershipId: widget.g.partnershipId,
            incidentId: widget.i.id,
            note: _note?.text ?? '',
          ),
    );
    if (r != null) setState(() => _note = null);
  }

  @override
  Widget build(BuildContext context) {
    final i = widget.i;
    final pal = context.palette;
    final note = _note;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: pal.line)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: '${showDate(i.occurredOn)} · ',
                  style: TextStyle(color: pal.inkMuted),
                ),
                TextSpan(
                  text: i.dutyTitle,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                TextSpan(text: ' · ${i.partyName} '),
                TextSpan(
                  text: '· ${context.t(i.resolvedOn != null ? 'gov.resolved' : 'gov.open')}',
                  style: TextStyle(color: i.resolvedOn != null ? pal.accentText : pal.warn),
                ),
              ],
            ),
          ),
          Text(i.reason),
          if (i.proposedSolution != null) Hint('${context.t('gov.solution')}: ${i.proposedSolution}'),
          if (i.resolvedOn != null)
            Text('✓ ${showDate(i.resolvedOn!)} — ${i.resolutionNote ?? ''}', style: TextStyle(color: pal.accentText)),
          if (i.resolvedOn == null && widget.g.writable && note == null)
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton(
                onPressed: () => setState(() => _note = TextEditingController()),
                child: Text(context.t('gov.resolve')),
              ),
            ),
          if (note != null) ...[
            const SizedBox(height: 8),
            Field(label: context.t('gov.resolutionNote'), controller: note),
            ErrorText(error),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton(onPressed: busy ? null : _resolve, child: Text(context.t('common.save'))),
            ),
          ],
        ],
      ),
    );
  }
}

class _Reviews extends ConsumerStatefulWidget {
  const _Reviews({required this.spaceId, required this.g});

  final String spaceId;
  final GovernanceDto g;

  @override
  ConsumerState<_Reviews> createState() => _ReviewsState();
}

class _ReviewsState extends ConsumerState<_Reviews> with ActionState {
  Future<void> _pdf(ReviewDto r) => act(() async {
    final bytes = await ref
        .read(coreProvider)
        .reviewPdf(spaceId: widget.spaceId, partnershipId: widget.g.partnershipId, reviewId: r.id);
    await ref.read(shareFileProvider)(bytes, 'korik-${r.no}.pdf', pdfMime);
  });

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ErrorText(error),
        for (final r in widget.g.reviews)
          Semantics(
            container: true,
            label: context.t('gov.reviewNo', {'n': r.no}),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: pal.line)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    '${context.t('gov.reviewNo', {'n': r.no})} · ${showDate(r.fromOn)} — ${showDate(r.toOn)}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  Hint(
                    '${context.t('gov.reason.${r.reason}')} · ${context.t('gov.heldOn')} ${showDate(r.heldOn)}',
                  ),
                  Text(
                    context.t('gov.integrity.${r.integrity}'),
                    style: TextStyle(
                      color: r.integrity == 'INTACT' ? pal.accentText : pal.danger,
                      fontWeight: r.integrity == 'INTACT' ? null : FontWeight.w700,
                    ),
                  ),
                  if (r.entriesAfter > 0) Hint(context.t('gov.entriesAfter', {'count': r.entriesAfter})),
                  Text(
                    r.chainCode,
                    style: TextStyle(fontFamily: 'monospace', fontSize: 12, color: pal.inkMuted),
                  ),
                  for (final a in r.acks)
                    Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(text: '${a.partyName}: '),
                          TextSpan(
                            text: context.t('gov.verdict.${a.verdict}'),
                            style: TextStyle(color: a.verdict == 'AGREE' ? pal.accentText : pal.warn),
                          ),
                          if (a.note != null)
                            TextSpan(
                              text: ' — ${a.note}',
                              style: TextStyle(color: pal.inkMuted),
                            ),
                        ],
                      ),
                    ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton(
                      onPressed: busy ? null : () => _pdf(r),
                      child: Text(context.t('gov.protocolPdf')),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// Oila kengashi uslubidagi to'liq ekran ko'rik sessiyasi (uy/SPEC 2F.5).
class _ReviewSession extends ConsumerStatefulWidget {
  const _ReviewSession({required this.spaceId, required this.partnershipId});

  final String spaceId;
  final String partnershipId;

  @override
  ConsumerState<_ReviewSession> createState() => _ReviewSessionState();
}

class _ReviewSessionState extends ConsumerState<_ReviewSession> with ActionState {
  /// Bo'sh sana — yadro «bugun» deb oladi (UI o'z soatiga tayanmaydi).
  String _to = '';
  String _reason = 'SCHEDULED';
  final _verdicts = <String, String>{};
  final _notes = <String, TextEditingController>{};

  @override
  void dispose() {
    for (final c in _notes.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _note(String partyId) => _notes.putIfAbsent(partyId, TextEditingController.new);

  Future<void> _hold(GovernanceDto g, ReviewDraftDto d) async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .holdReview(
            spaceId: widget.spaceId,
            partnershipId: widget.partnershipId,
            input: HoldReviewInput(
              toOn: d.toOn,
              reason: _reason,
              acks: [
                for (final p in g.parties)
                  ReviewAckInput(
                    partyId: p.partyId,
                    verdict: _verdicts[p.partyId] ?? '',
                    note: _optional(_notes[p.partyId]?.text ?? ''),
                  ),
              ],
            ),
          ),
    );
    if (r != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final pid = widget.partnershipId;
    final g = ref.watch(_gov(sid, pid)).valueOrNull;
    final draftQ = ref.watch(
      query(['reviewDraft', sid, pid, _to], (c) => c.reviewDraft(spaceId: sid, partnershipId: pid, toOn: _to)),
    );
    final d = draftQ.valueOrNull;
    final pal = context.palette;
    if (g == null) return const Center(child: CircularProgressIndicator());
    final complete = g.parties.every((p) {
      final v = _verdicts[p.partyId];
      return v == 'AGREE' || (v == 'OBJECT' && (_notes[p.partyId]?.text.trim() ?? '').isNotEmpty);
    });
    return ScreenBody(
      children: [
        Semantics(
          header: true,
          child: Text(
            '${context.t('gov.session')} ${d == null ? '' : '№${d.no}'} · ${g.title}',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
          ),
        ),
        DateField(
          label: _to.isEmpty ? '${context.t('gov.toOn')} (${context.t('gov.today')})' : context.t('gov.toOn'),
          value: _to.isEmpty ? null : _to,
          onChanged: (v) => setState(() => _to = v ?? ''),
        ),
        Select<String>(
          label: context.t('gov.reasonTitle'),
          items: [for (final r in _reasons) (r, context.t('gov.reason.$r'))],
          value: _reason,
          onChanged: (v) => setState(() => _reason = v ?? _reason),
        ),
        if (draftQ.hasError) ErrorText(draftQ.error),
        if (d != null) ...[
          Hint('${showDate(d.fromOn)} — ${showDate(d.toOn)}'),
          _boxed(context, d.chainOk ? pal.accent : pal.danger, [
            Text(
              context.t(d.chainOk ? 'gov.chainOk' : 'gov.chainBroken'),
              style: TextStyle(
                color: d.chainOk ? pal.accentText : pal.danger,
                fontWeight: d.chainOk ? null : FontWeight.w700,
              ),
            ),
            Hint('${context.t('gov.chainEntries', {'count': d.chainEntries})} · ${d.chainCode}'),
          ]),
          SectionCard(
            children: [
              ValueRow(context.t('venture.total.income'), d.totals.income.formatted),
              ValueRow(context.t('venture.total.expense'), d.totals.expense.formatted),
              if (d.totals.forceMajeure.minor != '0')
                ValueRow(context.t('venture.total.forceMajeure'), d.totals.forceMajeure.formatted),
              if (d.totals.corrections.minor != '0')
                ValueRow(context.t('venture.total.corrections'), d.totals.corrections.formatted),
              ValueRow(
                context.t('venture.total.result'),
                d.totals.result.formatted,
                strong: true,
                valueColor: pal.accentText,
              ),
              ValueRow(context.t('gov.entries'), '${d.totals.entries}'),
              ValueRow(context.t('gov.periodsClosed'), '${d.totals.periodsClosed}'),
            ],
          ),
          SectionCard(
            title: context.t('gov.openIncidents'),
            children: [
              if (d.openIncidents.isEmpty) Hint(context.t('gov.noOpenIncidents')),
              for (final i in d.openIncidents)
                Text('${showDate(i.occurredOn)} · ${i.dutyTitle} · ${i.partyName} — ${i.reason}'),
            ],
          ),
          SectionCard(
            title: context.t('gov.entriesTitle'),
            children: [
              if (d.entries.isEmpty) Hint(context.t('venture.empty')),
              for (final e in d.entries)
                ValueRow(
                  '${showDate(e.occurredOn)} · ${context.t('venture.kind.${e.kind}')}'
                  '${e.note == null ? '' : ' · ${e.note}'}',
                  e.effect.formatted,
                ),
            ],
          ),
          SectionCard(
            title: context.t('gov.acksTitle'),
            children: [
              for (final p in g.parties)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SegmentedChoice<String>(
                        label: p.name,
                        options: [
                          for (final v in ['AGREE', 'OBJECT']) (v, context.t('gov.verdict.$v')),
                        ],
                        value: _verdicts[p.partyId],
                        onChanged: (v) => setState(() => _verdicts[p.partyId] = v),
                      ),
                      if (_verdicts[p.partyId] == 'OBJECT')
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Field(
                            label: context.t('gov.objectionNote', {'name': p.name}),
                            controller: _note(p.partyId),
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                    ],
                  ),
                ),
              ErrorText(error),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(
                  onPressed: !complete || busy ? null : () => _hold(g, d),
                  child: Text(context.t('gov.holdReview')),
                ),
              ),
              const SizedBox(height: 8),
              Hint(context.t('gov.holdHint')),
            ],
          ),
        ],
      ],
    );
  }
}

class _Disputes extends ConsumerStatefulWidget {
  const _Disputes({required this.spaceId, required this.g, required this.onOpenContract});

  final String spaceId;
  final GovernanceDto g;
  final VoidCallback onOpenContract;

  @override
  ConsumerState<_Disputes> createState() => _DisputesState();
}

class _DisputesState extends ConsumerState<_Disputes> with ActionState {
  bool _form = false;
  final _subject = TextEditingController();
  final _claim = TextEditingController();
  final _picked = <int>{};
  String _openedBy = '';

  @override
  void dispose() {
    _subject.dispose();
    _claim.dispose();
    super.dispose();
  }

  void _start() => setState(() {
    _form = true;
    _subject.clear();
    _claim.clear();
    _picked.clear();
    _openedBy = widget.g.parties.firstOrNull?.partyId ?? '';
    error = null;
  });

  Future<void> _open() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .openPartnershipDispute(
            spaceId: widget.spaceId,
            partnershipId: widget.g.partnershipId,
            input: OpenDisputeInput(
              subject: _subject.text,
              clauses: Uint8List.fromList(_picked.toList()..sort()),
              openedBy: _openedBy,
              claims: [
                if (_claim.text.trim().isNotEmpty) DisputeClaimInput(partyId: _openedBy, claim: _claim.text),
              ],
            ),
          ),
    );
    if (r != null) setState(() => _form = false);
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.g;
    final pal = context.palette;
    return SectionCard(
      title: context.t('gov.disputes'),
      children: [
        Hint(context.t('gov.disputeHint', {'arbiter': g.arbiterName ?? '—'})),
        if (!g.inDispute && g.status == 'ACTIVE' && !_form)
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(onPressed: _start, child: Text(context.t('gov.openDispute'))),
          ),
        if (_form)
          _boxed(context, pal.danger, [
            Field(label: context.t('gov.subject'), controller: _subject),
            const SizedBox(height: 12),
            Text(context.t('gov.clauses')),
            for (final c in _clauses)
              CheckboxListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                value: _picked.contains(c),
                title: Text('$c. ${context.t('partnership.step.$c')}'),
                onChanged: (v) => setState(() => v ?? false ? _picked.add(c) : _picked.remove(c)),
              ),
            const SizedBox(height: 8),
            Select<String>(
              label: context.t('gov.openedBy'),
              items: [for (final p in g.parties) (p.partyId, p.name)],
              value: _openedBy,
              onChanged: (v) => setState(() => _openedBy = v ?? _openedBy),
            ),
            const SizedBox(height: 12),
            Field(label: context.t('gov.claim'), controller: _claim),
            const SizedBox(height: 8),
            Text(context.t('gov.disputeEffect'), style: TextStyle(color: pal.warn)),
            ErrorText(error),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilledButton(onPressed: busy ? null : _open, child: Text(context.t('gov.openDispute'))),
                TextButton(onPressed: () => setState(() => _form = false), child: Text(context.t('common.cancel'))),
              ],
            ),
          ]),
        if (g.disputes.isEmpty && !_form) Hint(context.t('gov.noDisputes')),
        for (final d in g.disputes)
          _Dispute(
            key: ValueKey(d.id),
            spaceId: widget.spaceId,
            g: g,
            d: d,
            onOpenContract: widget.onOpenContract,
          ),
      ],
    );
  }
}

class _Dispute extends ConsumerStatefulWidget {
  const _Dispute({
    required this.spaceId,
    required this.g,
    required this.d,
    required this.onOpenContract,
    super.key,
  });

  final String spaceId;
  final GovernanceDto g;
  final DisputeDto d;
  final VoidCallback onOpenContract;

  @override
  ConsumerState<_Dispute> createState() => _DisputeState();
}

class _DisputeState extends ConsumerState<_Dispute> with ActionState {
  String? _claimParty;
  final _claim = TextEditingController();
  String _date = todayIso();
  final _decision = TextEditingController();
  String _outcome = 'RESUME';

  @override
  void dispose() {
    _claim.dispose();
    _decision.dispose();
    super.dispose();
  }

  BarakaCore get _core => ref.read(coreProvider);

  List<PartyRefDto> get _missing =>
      widget.g.parties.where((p) => !widget.d.claims.any((c) => c.partyId == p.partyId)).toList();

  Future<void> _addClaim() async {
    final party = _claimParty ?? _missing.firstOrNull?.partyId ?? '';
    final r = await act(
      () => _core.addDisputeClaim(
        spaceId: widget.spaceId,
        partnershipId: widget.g.partnershipId,
        disputeId: widget.d.id,
        input: DisputeClaimInput(partyId: party, claim: _claim.text),
      ),
    );
    if (r != null) {
      setState(() {
        _claimParty = null;
        _claim.clear();
      });
    }
  }

  Future<void> _decide() => act(
    () => _core.recordArbiterDecision(
      spaceId: widget.spaceId,
      partnershipId: widget.g.partnershipId,
      disputeId: widget.d.id,
      input: DecisionInput(decidedOn: _date, decision: _decision.text, outcome: _outcome),
    ),
  );

  Future<void> _folder() => act(() async {
    final bytes = await _core.disputeFolderPdf(
      spaceId: widget.spaceId,
      partnershipId: widget.g.partnershipId,
      disputeId: widget.d.id,
    );
    await ref.read(shareFileProvider)(bytes, 'hakam-papkasi.pdf', pdfMime);
  });

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final g = widget.g;
    final pal = context.palette;
    final missing = _missing;
    final decision = d.decision;
    return _boxed(context, d.open ? pal.danger : pal.line, [
      Row(
        children: [
          Expanded(
            child: Text(d.subject, style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
          Text(
            context.t(d.open ? 'gov.disputeOpen' : 'gov.disputeClosed'),
            style: TextStyle(color: d.open ? pal.danger : pal.accentText, fontSize: 14),
          ),
        ],
      ),
      Hint(
        '${context.t('gov.openedOn', {'date': showDate(d.openedOn), 'name': d.openedByName})} · '
        '${context.t('gov.clausesList', {'list': d.clauses.join(', ')})}',
      ),
      for (final c in d.claims)
        Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: '${c.partyName}: ',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              TextSpan(text: c.claim),
            ],
          ),
        ),
      if (d.open && missing.isNotEmpty) ...[
        const SizedBox(height: 8),
        Select<String>(
          label: context.t('gov.party'),
          items: [for (final p in missing) (p.partyId, p.name)],
          value: _claimParty ?? missing.first.partyId,
          onChanged: (v) => setState(() => _claimParty = v),
        ),
        const SizedBox(height: 8),
        Field(label: context.t('gov.claim'), controller: _claim),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(onPressed: busy ? null : _addClaim, child: Text(context.t('gov.addClaim'))),
        ),
      ],
      if (decision != null)
        Container(
          margin: const EdgeInsets.only(top: 8),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: pal.surface, borderRadius: BorderRadius.circular(6)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                context.t('gov.decisionOf', {'name': decision.arbiterName, 'date': showDate(decision.decidedOn)}),
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              Text(decision.decision),
              Text(context.t('gov.outcome.${decision.outcome}'), style: TextStyle(color: pal.accentText)),
              if (decision.outcome == 'AMEND')
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton(onPressed: widget.onOpenContract, child: Text(context.t('gov.openContract'))),
                ),
            ],
          ),
        )
      else ...[
        const Divider(height: 24),
        Text(
          context.t('gov.recordDecision', {'name': g.arbiterName ?? '—'}),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        DateField(
          label: context.t('gov.date'),
          value: _date,
          allowClear: false,
          onChanged: (v) => setState(() => _date = v ?? _date),
        ),
        const SizedBox(height: 8),
        Field(label: context.t('gov.decision'), controller: _decision),
        const SizedBox(height: 8),
        SegmentedChoice<String>(
          label: context.t('gov.outcomeTitle'),
          options: [
            for (final o in ['RESUME', 'AMEND']) (o, context.t('gov.outcome.$o')),
          ],
          value: _outcome,
          onChanged: (v) => setState(() => _outcome = v),
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _decide, child: Text(context.t('gov.saveDecision'))),
        ),
      ],
      ErrorText(error),
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton(onPressed: busy ? null : _folder, child: Text(context.t('gov.folderPdf'))),
      ),
    ]);
  }
}
