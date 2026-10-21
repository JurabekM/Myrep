import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_agreement_parts.dart';

/// Uskunalar (kasbkor/SPEC 3.3): narx, foydali muddat, qoldiq qiymati. Eskirish oyma-oy avtomatik
/// (pul harakati emas); sotilsa yoki yaroqsiz bo'lsa — qolgan balans bir martalik xarajat.
class KkEquipmentScreen extends ConsumerStatefulWidget {
  const KkEquipmentScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkEquipmentScreen> createState() => _KkEquipmentScreenState();
}

class _KkEquipmentScreenState extends ConsumerState<KkEquipmentScreen> {
  String? _disposing;

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final list = ref.watch(query(['kkEquipment', sid], (c) => c.kkEquipment(spaceId: sid)));
    final rows = list.valueOrNull;
    return ScreenBody(
      mentorKey: 'mentor.kkEquipment',
      children: [
        Hint(context.t('kk.eq.intro')),
        _AddForm(spaceId: sid),
        SectionCard(
          title: context.t('kk.eq.list'),
          semanticLabel: context.t('kk.eq.list'),
          children: [
            if (list.hasError) ErrorText(list.error),
            if (rows != null && rows.isEmpty) Hint(context.t('kk.eq.empty')),
            for (final e in rows ?? const <KkEquipmentDto>[])
              _Row(
                key: ValueKey(e.id),
                spaceId: sid,
                e: e,
                disposing: _disposing == e.id,
                onDispose: () => setState(() => _disposing = _disposing == e.id ? null : e.id),
              ),
          ],
        ),
      ],
    );
  }
}

class _Row extends ConsumerStatefulWidget {
  const _Row({required this.spaceId, required this.e, required this.disposing, required this.onDispose, super.key});

  final String spaceId;
  final KkEquipmentDto e;
  final bool disposing;
  final VoidCallback onDispose;

  @override
  ConsumerState<_Row> createState() => _RowState();
}

class _RowState extends ConsumerState<_Row> with ActionState {
  Future<void> _delete() =>
      act(() => ref.read(coreProvider).kkDeleteEquipment(spaceId: widget.spaceId, id: widget.e.id));

  @override
  Widget build(BuildContext context) {
    final e = widget.e;
    final pal = context.palette;
    final state = switch (e.status) {
      'DISPOSED' => context.t('kk.eq.disposed', {
        'date': showDate(e.disposedOn ?? ''),
        'amount': e.disposalProceeds?.formatted ?? '',
      }),
      'DEPRECIATED' => context.t('kk.eq.depreciated'),
      _ => context.t('kk.eq.monthsLeft', {'n': e.monthsLeft}),
    };
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: pal.line)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(e.name, style: const TextStyle(fontWeight: FontWeight.w700)),
          Hint(
            '${context.t('kk.eq.since', {'date': showDate(e.acquiredOn), 'months': e.usefulMonths})} · '
            '${e.wallet != null ? context.t('kk.wallet.${e.wallet}') : context.t('kk.eq.paidBefore')}',
          ),
          ValueRow(context.t('kk.eq.cost'), e.cost.formatted),
          ValueRow(context.t('kk.eq.monthDep'), e.monthDepreciation.formatted, key: Key('kk-eq-dep-${e.name}')),
          ValueRow(context.t('kk.eq.bookValue'), e.bookValue.formatted),
          ValueRow(context.t('kk.eq.state'), state),
          Wrap(
            spacing: 8,
            children: [
              if (e.status != 'DISPOSED')
                KkActionButton(
                  label: context.t('kk.eq.dispose'),
                  active: widget.disposing,
                  onPressed: widget.onDispose,
                ),
              Semantics(
                label: context.t('kk.eq.deleteNamed', {'name': e.name}),
                child: TextButton(onPressed: busy ? null : _delete, child: Text(context.t('kk.eq.delete'))),
              ),
            ],
          ),
          ErrorText(error),
          if (widget.disposing) _DisposeForm(spaceId: widget.spaceId, e: e, onDone: widget.onDispose),
        ],
      ),
    );
  }
}

class _AddForm extends ConsumerStatefulWidget {
  const _AddForm({required this.spaceId});

  final String spaceId;

  @override
  ConsumerState<_AddForm> createState() => _AddFormState();
}

class _AddFormState extends ConsumerState<_AddForm> with ActionState {
  final _name = TextEditingController();
  final _cost = TextEditingController();
  final _salvage = TextEditingController();
  final _months = TextEditingController(text: '60');
  String? _acquiredOn;
  String _paid = 'CARD';

  @override
  void dispose() {
    for (final c in [_name, _cost, _salvage, _months]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkAddEquipment(
            spaceId: widget.spaceId,
            input: KkEquipmentInput(
              name: _name.text,
              cost: _cost.text,
              salvage: kkOpt(_salvage.text),
              usefulMonths: int.tryParse(_months.text.trim()) ?? 0,
              acquiredOn: _acquiredOn,
              wallet: _paid == 'BEFORE' ? null : _paid,
            ),
          ),
    );
    if (r != null) {
      setState(() {
        _name.clear();
        _cost.clear();
        _salvage.clear();
        _months.text = '60';
        _acquiredOn = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    const gap = SizedBox(height: 12);
    return SectionCard(
      title: context.t('kk.eq.add'),
      semanticLabel: context.t('kk.eq.add'),
      children: [
        Field(label: context.t('kk.eq.name'), controller: _name),
        gap,
        AmountField(label: context.t('kk.eq.cost'), controller: _cost),
        gap,
        Field(label: context.t('kk.eq.months'), controller: _months, keyboardType: TextInputType.number),
        gap,
        AmountField(label: context.t('kk.eq.salvage'), controller: _salvage),
        gap,
        DateField(
          label: context.t('kk.eq.acquiredOn'),
          value: _acquiredOn,
          onChanged: (v) => setState(() => _acquiredOn = v),
        ),
        gap,
        KkToggleRow<String>(
          label: context.t('kk.eq.paidFrom'),
          options: [
            for (final w in ['CASH', 'CARD', 'BEFORE'])
              (w, w == 'BEFORE' ? context.t('kk.eq.paidBefore') : context.t('kk.wallet.$w')),
          ],
          value: _paid,
          onChanged: (w) => setState(() => _paid = w),
        ),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.eq.addButton'))),
        ),
      ],
    );
  }
}

class _DisposeForm extends ConsumerStatefulWidget {
  const _DisposeForm({required this.spaceId, required this.e, required this.onDone});

  final String spaceId;
  final KkEquipmentDto e;
  final VoidCallback onDone;

  @override
  ConsumerState<_DisposeForm> createState() => _DisposeFormState();
}

class _DisposeFormState extends ConsumerState<_DisposeForm> with ActionState {
  final _proceeds = TextEditingController();
  String _wallet = 'CASH';
  String? _on;

  @override
  void dispose() {
    _proceeds.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final proceeds = kkOpt(_proceeds.text);
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkDisposeEquipment(
            spaceId: widget.spaceId,
            id: widget.e.id,
            input: KkDisposeInput(proceeds: proceeds, wallet: proceeds == null ? null : _wallet, disposedOn: _on),
          ),
    );
    if (r != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: context.t('kk.eq.disposeTitle', {'name': widget.e.name}),
    child: KkBox(
      children: [
        Hint(context.t('kk.eq.disposeHint', {'amount': widget.e.bookValue.formatted})),
        const SizedBox(height: 12),
        AmountField(label: context.t('kk.eq.proceeds'), controller: _proceeds),
        const SizedBox(height: 12),
        KkToggleRow<String>(
          label: context.t('kk.eq.proceedsWallet'),
          options: [
            for (final w in ['CASH', 'CARD']) (w, context.t('kk.wallet.$w')),
          ],
          value: _wallet,
          onChanged: (w) => setState(() => _wallet = w),
        ),
        const SizedBox(height: 12),
        DateField(label: context.t('kk.date'), value: _on, onChanged: (v) => setState(() => _on = v)),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.eq.disposeSave'))),
        ),
      ],
    ),
  );
}
