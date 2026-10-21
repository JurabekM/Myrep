import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'mf_entry_sheet.dart';
import 'purpose_shares.dart';

/// Kelishuv matni ulushlardan (foydalanuvchi o'zgartirishi mumkin). Faqat matn — hisob yadroda.
List<String> _itemsFrom(BuildContext context, SharesDraft d, String? receiver) {
  final parts = [
    for (final p in mfPurposes)
      if (d.text(p).isNotEmpty)
        context.t('mf.terms.part', {'percent': d.text(p), 'purpose': context.t('mf.purpose.$p').toLowerCase()}),
  ];
  return [
    context.t('mf.terms.item1', {'parts': parts.join(', ')}),
    if (receiver != null) context.t('mf.terms.item2', {'name': receiver}) else context.t('mf.terms.item2Any'),
    context.t('mf.terms.item3'),
    context.t('mf.terms.item4'),
  ];
}

/// «Ikki qirg'oq» shartlari (musofir/SPEC 5): standart maqsad ulushlari, kim qabul qiladi va oila
/// bilan kelishuv matni — Uy makonidagi oilaviy kelishuv (kattalar PIN bilan tasdiqlaydi).
class MfTermsCard extends ConsumerStatefulWidget {
  const MfTermsCard({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<MfTermsCard> createState() => _MfTermsCardState();
}

class _MfTermsCardState extends ConsumerState<MfTermsCard> {
  bool _editing = false;

  @override
  Widget build(BuildContext context) {
    final terms = ref.watch(mfTermsQuery(widget.spaceId));
    final members = ref.watch(query(['household'], (c) => c.household())).valueOrNull?.members ?? const [];
    final d = terms.valueOrNull;
    return SectionCard(
      title: context.t('mf.terms.title'),
      children: [
        Hint(context.t('mf.terms.intro')),
        if (terms.hasError) ErrorText(terms.error),
        if (d != null && !_editing) ...[
          const SizedBox(height: 8),
          _TermsView(d: d, members: members),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton(
              onPressed: () => setState(() => _editing = true),
              child: Text(context.t(d.shares.isEmpty ? 'mf.terms.set' : 'mf.terms.change')),
            ),
          ),
        ],
        if (d != null && _editing)
          _TermsForm(
            spaceId: widget.spaceId,
            d: d,
            members: members,
            onDone: () => setState(() => _editing = false),
          ),
      ],
    );
  }
}

class _TermsView extends StatelessWidget {
  const _TermsView({required this.d, required this.members});

  final MfTermsDto d;
  final List<MemberDto> members;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    if (d.shares.isEmpty) return Text(context.t('mf.terms.none'));
    final receiver = members.where((m) => m.id == d.receiverMemberId).firstOrNull?.displayName;
    final a = d.agreement;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          d.shares.map((s) => '${context.t('mf.purpose.${s.purpose}')} ${s.percent} %').join(' · '),
          key: const Key('mf-terms-shares'),
        ),
        if (receiver != null) Hint(context.t('mf.terms.receiverLine', {'name': receiver})),
        if (a != null) ...[
          const SizedBox(height: 6),
          Text(
            context.t('mf.terms.status.${a.status}'),
            key: const Key('mf-terms-agreement'),
            style: TextStyle(color: a.status == 'ACTIVE' ? pal.accentText : pal.warn),
          ),
          for (final x in a.adults)
            Hint('${x.name}: ${x.agreedOn != null ? '✓ ${showDate(x.agreedOn!)}' : context.t('mf.terms.notYet')}'),
          if (a.status != 'ACTIVE') Hint(context.t('mf.terms.confirmWhere')),
        ],
      ],
    );
  }
}

class _TermsForm extends ConsumerStatefulWidget {
  const _TermsForm({required this.spaceId, required this.d, required this.members, required this.onDone});

  final String spaceId;
  final MfTermsDto d;
  final List<MemberDto> members;
  final VoidCallback onDone;

  @override
  ConsumerState<_TermsForm> createState() => _TermsFormState();
}

class _TermsFormState extends ConsumerState<_TermsForm> with ActionState {
  late final _shares = SharesDraft.from(widget.d.shares);
  late String _receiverId = widget.d.receiverMemberId ?? '';
  late final _title = TextEditingController(text: widget.d.agreement?.title);

  /// Matn qo'lda o'zgartirilmagan bo'lsa (`null`) — ulushlar va qabul qiluvchidan qayta tuziladi.
  late final TextEditingController _items = TextEditingController(text: widget.d.agreement?.items.join('\n'));
  late bool _manual = widget.d.agreement != null;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_title.text.isEmpty) _title.text = context.t('mf.terms.defaultTitle');
    if (!_manual) _items.text = _generated();
  }

  @override
  void dispose() {
    _shares.dispose();
    _title.dispose();
    _items.dispose();
    super.dispose();
  }

  String? get _receiverName => widget.members.where((m) => m.id == _receiverId).firstOrNull?.displayName;

  String _generated() => _itemsFrom(context, _shares, _receiverName).join('\n');

  void _regenerate() => setState(() {
    _manual = false;
    _items.text = _generated();
  });

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfSetTerms(
            spaceId: widget.spaceId,
            input: MfTermsInput(
              shares: _shares.input(),
              receiverMemberId: _receiverId.isEmpty ? null : _receiverId,
              title: _title.text,
              items: _items.text.split('\n'),
            ),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const SizedBox(height: 8),
      PurposeShares(
        draft: _shares,
        legend: context.t('mf.purposesLegend'),
        onChanged: () {
          if (!_manual) setState(() => _items.text = _generated());
        },
      ),
      const SizedBox(height: 12),
      Select<String>(
        label: context.t('mf.terms.receiver'),
        items: [('', context.t('mf.terms.anyone')), for (final m in widget.members) (m.id, m.displayName)],
        value: _receiverId,
        onChanged: (v) => setState(() {
          _receiverId = v ?? '';
          if (!_manual) _items.text = _generated();
        }),
      ),
      const SizedBox(height: 12),
      Field(label: context.t('family.titleField'), controller: _title),
      const SizedBox(height: 12),
      Field(
        label: context.t('mf.terms.text'),
        controller: _items,
        maxLines: 8,
        onChanged: (_) => _manual = true,
      ),
      if (_manual)
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(onPressed: _regenerate, child: Text(context.t('mf.terms.regenerate'))),
        ),
      Hint(context.t('mf.terms.resetHint')),
      ErrorText(error),
      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        children: [
          FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
          TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
        ],
      ),
    ],
  );
}
