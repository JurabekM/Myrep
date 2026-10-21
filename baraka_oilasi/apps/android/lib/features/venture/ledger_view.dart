import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/json.dart';
import '../../shared/widgets.dart';

const _kinds = ['INCOME', 'EXPENSE', 'FORCE_MAJEURE'];
const _categories = {
  'INCOME': ['ORDER', 'OTHER'],
  'EXPENSE': ['MATERIAL', 'WAGE', 'RENT', 'EQUIPMENT', 'TRANSPORT', 'OTHER'],
};

String? _optional(String v) => v.trim().isEmpty ? null : v;

/// Chek / dalil fayllarini tanlash (rasm yoki PDF). Soni va hajmi yadroda tekshiriladi
/// (`MAX_ATTACHMENTS`, `MAX_ATTACHMENT_BYTES`). Testlarda almashtiriladi.
typedef PickAttachments = Future<List<AttachmentInput>> Function();

Future<List<AttachmentInput>> pickAttachments() async {
  final files = await FilePicker.pickFiles(
    type: FileType.custom,
    allowedExtensions: const ['jpg', 'jpeg', 'png', 'webp', 'pdf'],
  );
  return [for (final f in files) AttachmentInput(fileName: f.name, bytes: await f.readAsBytes())];
}

final pickAttachmentsProvider = Provider<PickAttachments>((ref) => pickAttachments);

ProviderListenable<AsyncValue<VentureLedgerDto>> _ledger(String sid, String id) =>
    query(['ledger', sid, id], (c) => c.ventureLedger(spaceId: sid, partnershipId: id));

/// Sheriklik kassa daftari (uy/SPEC 2E.3): biznes puli uy pulidan alohida. Har yozuv kelishuv
/// jurnaliga ham tushadi; yopilgan davr o'zgarmaydi — xato faqat tuzatuvchi yozuv bilan.
class LedgerView extends ConsumerStatefulWidget {
  const LedgerView({required this.spaceId, required this.partnershipId, super.key});

  final String spaceId;
  final String partnershipId;

  @override
  ConsumerState<LedgerView> createState() => _LedgerViewState();
}

class _LedgerViewState extends ConsumerState<LedgerView> {
  VentureEntryDto? _correcting;

  Future<void> _open(VentureEntryDto e, AttachmentMetaDto meta) async {
    final a = await ref
        .read(coreProvider)
        .ventureAttachment(spaceId: widget.spaceId, partnershipId: widget.partnershipId, attachmentId: meta.id);
    if (!mounted) return;
    if (!a.mime.startsWith('image/')) {
      await ref.read(shareFileProvider)(a.bytes, a.fileName, a.mime);
      return;
    }
    await showBarakaDialog<void>(
      context,
      (ctx) => AlertDialog(
        title: Text(a.fileName),
        content: InteractiveViewer(
          child: Image.memory(a.bytes, semanticLabel: a.fileName, fit: BoxFit.contain),
        ),
        actions: [TextButton(onPressed: () => Navigator.of(ctx).pop(), child: Text(ctx.t('common.close')))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final q = ref.watch(_ledger(widget.spaceId, widget.partnershipId));
    final l = q.valueOrNull;
    if (l == null) {
      return q.hasError
          ? Padding(padding: const EdgeInsets.all(16), child: ErrorText(q.error))
          : const Center(child: CircularProgressIndicator());
    }
    return ScreenBody(
      children: [
        _Balances(l),
        if (l.writable)
          _EntryForm(
            key: ValueKey(_correcting?.id),
            spaceId: widget.spaceId,
            l: l,
            correcting: _correcting,
            onDone: () => setState(() => _correcting = null),
          )
        else
          SectionCard(
            children: [
              Hint(context.t('venture.readOnly.${l.readOnlyReason ?? 'NOT_ACTIVE'}', {'name': l.keeperName ?? ''})),
            ],
          ),
        _OpenPeriod(spaceId: widget.spaceId, l: l),
        _Entries(
          l,
          onCorrect: l.writable ? (e) => setState(() => _correcting = e) : null,
          onOpen: _open,
        ),
        for (final p in l.periods) _ClosedPeriod(spaceId: widget.spaceId, l: l, p: p),
      ],
    );
  }
}

class _Balances extends StatelessWidget {
  const _Balances(this.l);

  final VentureLedgerDto l;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    final b = l.buyout;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final x in l.balances)
          Kpi(
            label:
                '${x.name} · ${context.t('partnership.role.${x.role}')}'
                '${x.isMe ? ' · ${context.t('venture.we')}' : ''}',
            value: x.capital.formatted,
            hint: [
              context.t('venture.capital'),
              if (x.carriedLoss.minor != '0') context.t('venture.carriedLoss', {'amount': x.carriedLoss.formatted}),
            ].join(' · '),
          ),
        if (b != null)
          SectionCard(
            children: [
              Text(
                context.t('venture.buyoutProgress', {
                  'buyer': b.buyerName,
                  'seller': b.sellerName,
                  'paid': b.paid,
                  'total': b.total,
                }),
              ),
              if (b.nextNo != null)
                Hint(
                  context.t('venture.buyoutNext', {
                    'n': b.nextNo,
                    'date': showDate(b.nextDate ?? ''),
                    'amount': b.nextPayment?.formatted ?? '',
                  }),
                ),
              if (b.overdue.isNotEmpty)
                Text(
                  context.t('venture.buyoutOverdue', {'list': b.overdue.join(', ')}),
                  style: TextStyle(color: pal.warn),
                ),
            ],
          ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Hint(
            context.t(l.chainOk ? 'venture.chainOk' : 'venture.chainBroken', {'code': l.chainCode}),
            color: l.chainOk ? null : pal.danger,
          ),
        ),
      ],
    );
  }
}

class _EntryForm extends ConsumerStatefulWidget {
  const _EntryForm({required this.spaceId, required this.l, required this.correcting, required this.onDone, super.key});

  final String spaceId;
  final VentureLedgerDto l;
  final VentureEntryDto? correcting;
  final VoidCallback onDone;

  @override
  ConsumerState<_EntryForm> createState() => _EntryFormState();
}

class _EntryFormState extends ConsumerState<_EntryForm> with ActionState {
  String _kind = 'INCOME';
  String _category = 'ORDER';
  String _date = todayIso();
  final _amount = TextEditingController();
  final _note = TextEditingController();
  List<AttachmentInput> _files = const [];

  @override
  void dispose() {
    _amount.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _pick() async {
    final files = await act(() => ref.read(pickAttachmentsProvider)());
    if (files != null && files.isNotEmpty) setState(() => _files = files);
  }

  Future<void> _save() async {
    final c = widget.correcting;
    final r = await act(
      () => ref
          .read(coreProvider)
          .addVentureEntry(
            spaceId: widget.spaceId,
            partnershipId: widget.l.partnershipId,
            input: VentureEntryInput(
              kind: c != null ? 'CORRECTION' : _kind,
              category: c != null || _kind == 'FORCE_MAJEURE' ? null : _category,
              amount: _amount.text,
              occurredOn: _date,
              note: _optional(_note.text),
              correctsEntryId: c?.id,
              attachments: _files,
            ),
          ),
    );
    if (r == null) return;
    setState(() {
      _amount.clear();
      _note.clear();
      _files = const [];
    });
    widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.correcting;
    final cats = c == null ? _categories[_kind] : null;
    final fm = _kind == 'FORCE_MAJEURE' && c == null;
    return SectionCard(
      title: context.t(c != null ? 'venture.correctTitle' : 'venture.addEntry'),
      semanticLabel: context.t('venture.addEntry'),
      children: [
        if (c != null)
          Text(
            context.t('venture.correctHint', {
              'date': showDate(c.occurredOn),
              'kind': context.t('venture.kind.${c.kind}'),
              'amount': c.amount.formatted,
            }),
          )
        else
          SegmentedChoice<String>(
            label: '',
            options: [for (final k in _kinds) (k, context.t('venture.kind.$k'))],
            value: _kind,
            onChanged: (k) => setState(() {
              _kind = k;
              _category = _categories[k]?.first ?? 'OTHER';
            }),
          ),
        if (cats != null) ...[
          const SizedBox(height: 12),
          Select<String>(
            label: context.t('venture.category'),
            items: [for (final x in cats) (x, context.t('venture.cat.$x'))],
            value: _category,
            onChanged: (v) => setState(() => _category = v ?? _category),
          ),
        ],
        const SizedBox(height: 12),
        AmountField(label: context.t(c != null ? 'venture.correctAmount' : 'common.amount'), controller: _amount),
        const SizedBox(height: 12),
        DateField(
          label: context.t('venture.date'),
          value: _date,
          allowClear: false,
          onChanged: (v) => setState(() => _date = v ?? _date),
        ),
        const SizedBox(height: 12),
        Field(
          label: context.t(c != null || _kind == 'FORCE_MAJEURE' ? 'venture.noteRequired' : 'common.note'),
          controller: _note,
        ),
        const SizedBox(height: 12),
        Text(context.t(_kind == 'FORCE_MAJEURE' ? 'venture.evidence' : 'venture.receipt')),
        const SizedBox(height: 6),
        Wrap(
          spacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            OutlinedButton.icon(
              onPressed: busy ? null : _pick,
              icon: const Icon(Icons.attach_file),
              label: Text(context.t('venture.pickFiles')),
            ),
            Hint(_files.isEmpty ? context.t('venture.noFiles') : _files.map((f) => f.fileName).join(', ')),
          ],
        ),
        if (fm) ...[const SizedBox(height: 8), Hint(context.t('venture.forceMajeureHint'))],
        ErrorText(error),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(onPressed: busy ? null : _save, child: Text(context.t('venture.save'))),
            if (c != null) TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
          ],
        ),
      ],
    );
  }
}

class _OpenPeriod extends ConsumerStatefulWidget {
  const _OpenPeriod({required this.spaceId, required this.l});

  final String spaceId;
  final VentureLedgerDto l;

  @override
  ConsumerState<_OpenPeriod> createState() => _OpenPeriodState();
}

class _OpenPeriodState extends ConsumerState<_OpenPeriod> with ActionState {
  String _end = todayIso();
  String _channel = 'CASH';
  String? _negParty;
  final _negNote = TextEditingController();
  final _prices = <int, TextEditingController>{};
  VenturePeriodDto? _pv;

  @override
  void dispose() {
    _negNote.dispose();
    for (final c in _prices.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _price(int n) => _prices.putIfAbsent(n, TextEditingController.new);

  ClosePeriodInput _input() => ClosePeriodInput(
    endOn: _end,
    channel: _channel,
    negligence: _negParty == null ? null : NegligenceInput(partyId: _negParty!, note: _negNote.text),
    buyoutPrices: [
      for (final e in _prices.entries)
        if (e.value.text.trim().isNotEmpty) InstallmentPriceInput(no: e.key, price: e.value.text),
    ],
  );

  BarakaCore get _core => ref.read(coreProvider);

  Future<void> _preview() async {
    final r = await act(
      () => _core.venturePeriodPreview(spaceId: widget.spaceId, partnershipId: widget.l.partnershipId, input: _input()),
    );
    if (r != null) setState(() => _pv = r);
  }

  Future<void> _close() async {
    final r = await act(
      () => _core.closeVenturePeriod(spaceId: widget.spaceId, partnershipId: widget.l.partnershipId, input: _input()),
    );
    if (r == null) return;
    setState(() {
      _pv = null;
      _negParty = null;
      _negNote.clear();
      for (final c in _prices.values) {
        c.clear();
      }
    });
  }

  Future<void> _reread(String partyId) async {
    final r = await act(
      () => _core.acknowledgeSpikeReread(
        spaceId: widget.spaceId,
        partnershipId: widget.l.partnershipId,
        partyId: partyId,
      ),
    );
    if (r != null) await _preview();
  }

  @override
  Widget build(BuildContext context) {
    final l = widget.l;
    final o = l.open;
    final pal = context.palette;
    final workers = l.balances.where((b) => b.role == 'WORKER').toList();
    final pv = _pv;
    final spikePending = pv != null && pv.profitSpike && l.balances.any((b) => !pv.spikeRereads.contains(b.partyId));
    final nos = pv?.buyout == null ? const <int>[] : [...pv!.buyout!.paid, ...pv.buyout!.unpaid];
    return SectionCard(
      title: context.t('venture.openPeriod', {'n': o.no, 'from': showDate(o.from)}),
      children: [
        ValueRow(context.t('venture.total.income'), o.income.formatted),
        ValueRow(context.t('venture.total.expense'), o.expense.formatted),
        if (o.forceMajeure.minor != '0') ValueRow(context.t('venture.total.forceMajeure'), o.forceMajeure.formatted),
        if (o.corrections.minor != '0') ValueRow(context.t('venture.total.corrections'), o.corrections.formatted),
        ValueRow(context.t('venture.total.result'), o.result.formatted, strong: true, valueColor: pal.accentText),
        if (l.writable && o.entries > 0) ...[
          const Divider(height: 24),
          DateField(
            label: context.t('venture.endOn'),
            value: _end,
            allowClear: false,
            onChanged: (v) => setState(() => _end = v ?? _end),
          ),
          const SizedBox(height: 12),
          Select<String>(
            label: context.t('venture.channel'),
            items: [('CASH', context.t('venture.channelCash')), ('CARD', context.t('venture.channelCard'))],
            value: _channel,
            onChanged: (v) => setState(() => _channel = v ?? _channel),
          ),
          if (l.kind == 'MUDARABA' && workers.isNotEmpty) ...[
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _negParty != null,
              title: Text(context.t('venture.negligence')),
              onChanged: (v) => setState(() => _negParty = v ?? false ? workers.first.partyId : null),
            ),
            if (_negParty != null) Field(label: context.t('venture.negligenceNote'), controller: _negNote),
          ],
          if (nos.isNotEmpty) ...[
            const SizedBox(height: 12),
            Hint(context.t('venture.priceHint')),
            for (final n in nos)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: AmountField(
                  label: context.t('venture.priceOf', {'n': n}),
                  hint: context.t('venture.pricePlaceholder'),
                  controller: _price(n),
                ),
              ),
          ],
          if (l.inDispute)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: pal.danger),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Semantics(liveRegion: true, child: Text(context.t('venture.disputeBlocks'))),
              ),
            ),
          if (pv != null && pv.profitSpike)
            _SpikeAlert(spaceId: widget.spaceId, l: l, p: pv, busy: busy, onReread: _reread),
          ErrorText(error),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              OutlinedButton(onPressed: busy ? null : _preview, child: Text(context.t('venture.preview'))),
              if (pv != null)
                FilledButton(
                  onPressed: busy || l.inDispute || spikePending ? null : _close,
                  child: Text(context.t('venture.closePeriod')),
                ),
            ],
          ),
          if (pv != null) ...[
            const SizedBox(height: 12),
            _Distribution(pv),
            const SizedBox(height: 8),
            Hint(context.t('venture.closeWarning')),
          ],
        ],
      ],
    );
  }
}

/// «Katta foyda» (uy/SPEC 2F.7): taqsimotdan oldin har bir tomon 4–5-bandlarni (foyda va zarar
/// qoidasi) qayta o'qiydi; navbatdan tashqari ko'rik tavsiya etiladi. Chegara qoidasi yadroda.
class _SpikeAlert extends ConsumerWidget {
  const _SpikeAlert({
    required this.spaceId,
    required this.l,
    required this.p,
    required this.busy,
    required this.onReread,
  });

  final String spaceId;
  final VentureLedgerDto l;
  final VenturePeriodDto p;
  final bool busy;
  final ValueChanged<String> onReread;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pal = context.palette;
    final id = l.partnershipId;
    // Kalit sheriklik oynasidagi bilan bir xil — natija ham `Js`.
    final c = ref
        .watch(
          query([
            'partnership',
            spaceId,
            id,
          ], (c) async => decodeJs(await c.partnership(spaceId: spaceId, partnershipId: id))),
        )
        .valueOrNull;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Semantics(
        liveRegion: true,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            border: Border.all(color: pal.warn),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                context.t('venture.spike.title', {'result': p.result.formatted}),
                style: TextStyle(color: pal.warn, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text(context.t('venture.spike.body')),
              if (c != null)
                Container(
                  margin: const EdgeInsets.only(top: 8),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: pal.surface, borderRadius: BorderRadius.circular(6)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('4. ${context.t('partnership.q.4')}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      for (final x in c.l('parties')) Text('${x.s('fullName')}: ${x.s('profitShare')}'),
                      const SizedBox(height: 4),
                      Text('5. ${context.t('partnership.q.5')}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      for (final x in c.l('parties')) Text('${x.s('fullName')}: ${x.so('lossShare') ?? '—'}'),
                      if (c.so('negligenceClause') != null) Hint(c.s('negligenceClause')),
                    ],
                  ),
                ),
              const SizedBox(height: 6),
              for (final b in l.balances)
                if (p.spikeRereads.contains(b.partyId))
                  Text(
                    '✓ ${context.t('venture.spike.done', {'name': b.name})}',
                    style: TextStyle(color: pal.accentText),
                  )
                else
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton(
                      onPressed: busy || !l.writable ? null : () => onReread(b.partyId),
                      child: Text(context.t('venture.spike.ack', {'name': b.name})),
                    ),
                  ),
              const SizedBox(height: 6),
              Hint(context.t('venture.spike.extraReview')),
            ],
          ),
        ),
      ),
    );
  }
}

/// Taqsimot — barcha summalar yadrodan (UI hisoblamaydi). Telefon uchun jadval o'rniga har tomon
/// alohida blok.
class _Distribution extends StatelessWidget {
  const _Distribution(this.p);

  final VenturePeriodDto p;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    final liable = p.parties.where((x) => x.liability.minor != '0').firstOrNull;
    final b = p.buyout;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (p.recovered.minor != '0') Text(context.t('venture.recoveredNote', {'amount': p.recovered.formatted})),
        for (final x in p.parties)
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              border: Border.all(color: pal.line),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    '${x.name}${x.isMe ? ' (${context.t('venture.we')})' : ''}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                ValueRow(
                  context.t('venture.col.share'),
                  x.share.formatted,
                  valueColor: x.share.minor.startsWith('-') ? pal.danger : null,
                ),
                ValueRow(context.t('venture.col.recovered'), x.recovered.formatted),
                ValueRow(context.t('venture.col.payout'), x.payout.formatted, strong: true),
                ValueRow(context.t('venture.col.capital'), x.capitalAfter.formatted),
              ],
            ),
          ),
        if (liable != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              context.t('venture.liability', {'name': p.negligentParty ?? '', 'amount': liable.liability.formatted}),
              style: TextStyle(color: pal.warn),
            ),
          ),
        if (b != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              [
                if (b.paid.isNotEmpty)
                  context.t('venture.buyoutPaid', {'list': b.paid.join(', '), 'amount': b.amount.formatted})
                else
                  context.t('venture.buyoutNone'),
                if (b.unpaid.isNotEmpty) context.t('venture.buyoutUnpaid', {'list': b.unpaid.join(', ')}),
              ].join(' '),
            ),
          ),
        const SizedBox(height: 8),
        Text(
          p.myIncome.minor == '0'
              ? context.t('venture.myIncomeNone')
              : context.t('venture.myIncome', {'amount': p.myIncome.formatted}),
          style: TextStyle(color: pal.accentText),
        ),
        Hint(context.t('venture.policy.${p.lossPolicy}')),
      ],
    );
  }
}

class _Entries extends StatelessWidget {
  const _Entries(this.l, {required this.onCorrect, required this.onOpen});

  final VentureLedgerDto l;
  final ValueChanged<VentureEntryDto>? onCorrect;
  final void Function(VentureEntryDto e, AttachmentMetaDto a) onOpen;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    if (l.entries.isEmpty) return Hint(context.t('venture.empty'));
    return SectionCard(
      title: context.t('venture.entries'),
      children: [
        for (final e in l.entries)
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: pal.line)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text.rich(
                        TextSpan(
                          children: [
                            TextSpan(text: '${showDate(e.occurredOn)} · ${context.t('venture.kind.${e.kind}')}'),
                            if (e.category != null)
                              TextSpan(
                                text: ' · ${context.t('venture.cat.${e.category}')}',
                                style: TextStyle(color: pal.inkMuted),
                              ),
                          ],
                        ),
                      ),
                    ),
                    Text(
                      e.effect.formatted,
                      style: TextStyle(
                        color: e.effect.minor.startsWith('-') ? pal.danger : null,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ],
                ),
                if (e.note != null || e.corrected)
                  Text.rich(
                    TextSpan(
                      children: [
                        if (e.note != null) TextSpan(text: e.note),
                        if (e.corrected)
                          TextSpan(
                            text: ' (${context.t('venture.corrected')})',
                            style: TextStyle(color: pal.warn, fontSize: 13),
                          ),
                      ],
                    ),
                  ),
                Wrap(
                  spacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Tooltip(
                      message: '${context.t('venture.hashTitle')}: ${e.chainCode}',
                      child: Hint(
                        e.periodNo != null
                            ? context.t('venture.closedIn', {'n': e.periodNo})
                            : context.t('venture.open'),
                      ),
                    ),
                    for (final a in e.attachments)
                      TextButton.icon(
                        onPressed: () => onOpen(e, a),
                        icon: const Icon(Icons.attach_file, size: 18),
                        label: Text(a.fileName),
                      ),
                    if (onCorrect != null && e.kind != 'CORRECTION')
                      TextButton(onPressed: () => onCorrect!(e), child: Text(context.t('venture.correct'))),
                  ],
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _ClosedPeriod extends ConsumerStatefulWidget {
  const _ClosedPeriod({required this.spaceId, required this.l, required this.p});

  final String spaceId;
  final VentureLedgerDto l;
  final VenturePeriodDto p;

  @override
  ConsumerState<_ClosedPeriod> createState() => _ClosedPeriodState();
}

class _ClosedPeriodState extends ConsumerState<_ClosedPeriod> with ActionState {
  Future<void> _pdf() => act(() async {
    final bytes = await ref
        .read(coreProvider)
        .venturePeriodPdf(spaceId: widget.spaceId, partnershipId: widget.l.partnershipId, periodId: widget.p.id ?? '');
    await ref.read(shareFileProvider)(bytes, 'davr-${widget.p.no}.pdf', pdfMime);
  });

  @override
  Widget build(BuildContext context) {
    final p = widget.p;
    final pal = context.palette;
    return SectionCard(
      title: context.t('venture.closedPeriod', {'n': p.no, 'from': showDate(p.startOn), 'to': showDate(p.endOn)}),
      trailing: Tooltip(
        message: context.t('venture.locked'),
        child: Icon(Icons.lock_outline, color: pal.inkMuted, semanticLabel: context.t('venture.locked')),
      ),
      children: [
        ValueRow(context.t('venture.total.income'), p.income.formatted),
        ValueRow(context.t('venture.total.expense'), p.expense.formatted),
        if (p.forceMajeure.minor != '0') ValueRow(context.t('venture.total.forceMajeure'), p.forceMajeure.formatted),
        ValueRow(context.t('venture.total.result'), p.result.formatted, strong: true, valueColor: pal.accentText),
        const SizedBox(height: 8),
        _Distribution(p),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            OutlinedButton(onPressed: busy ? null : _pdf, child: Text(context.t('venture.reportPdf'))),
            if (p.chainCode != null) Hint(context.t('venture.chainAt', {'code': p.chainCode})),
          ],
        ),
        ErrorText(error),
      ],
    );
  }
}
