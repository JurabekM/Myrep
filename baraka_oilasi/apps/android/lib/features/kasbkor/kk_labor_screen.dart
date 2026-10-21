import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'kk_agreement_parts.dart';

/// Oilaviy mehnat (kasbkor/SPEC 3.1): pul to'lanmasa ham tannarxga kiradi. To'langan bo'lsa — u chiqimda
/// bor, haqiqiy foydadan qayta ayirilmaydi. Qiymat (soat × baho) yadroda hisoblanadi.
class KkLaborScreen extends ConsumerStatefulWidget {
  const KkLaborScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkLaborScreen> createState() => _KkLaborScreenState();
}

class _KkLaborScreenState extends ConsumerState<KkLaborScreen> with ActionState {
  Future<void> _delete(String id) =>
      act(() => ref.read(coreProvider).kkDeleteFamilyLabor(spaceId: widget.spaceId, id: id));

  @override
  Widget build(BuildContext context) {
    final sid = widget.spaceId;
    final list = ref.watch(query(['kkLabor', sid], (c) => c.kkFamilyLabor(spaceId: sid)));
    final overview = ref.watch(query(['kkOverview', sid], (c) => c.kkOverview(spaceId: sid))).valueOrNull;
    final rows = list.valueOrNull;
    final pal = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.kkLabor',
      children: [
        Hint(context.t('kk.fl.intro')),
        if (overview != null)
          Kpi(
            key: const Key('kk-family-labor'),
            label: context.t('kk.fl.total'),
            value: overview.profit.familyLabor.formatted,
          ),
        _AddForm(spaceId: sid),
        SectionCard(
          title: context.t('kk.fl.list'),
          semanticLabel: context.t('kk.fl.list'),
          children: [
            if (list.hasError) ErrorText(list.error),
            if (rows != null && rows.isEmpty) Hint(context.t('kk.fl.empty')),
            for (final r in rows ?? const <KkFamilyLaborDto>[])
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
                                TextSpan(text: '${showDate(r.workedOn)} · '),
                                TextSpan(
                                  text: r.person,
                                  style: const TextStyle(fontWeight: FontWeight.w600),
                                ),
                                if (r.paid)
                                  TextSpan(
                                    text: '  ${context.t('kk.fl.paidTag')}',
                                    style: TextStyle(color: pal.inkMuted, fontSize: 13),
                                  ),
                              ],
                            ),
                          ),
                        ),
                        Text(
                          r.value.formatted,
                          style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()]),
                        ),
                      ],
                    ),
                    Hint(
                      '${context.t('kk.fl.hours')}: ${r.hours} · ${context.t('kk.fl.rate')}: ${r.hourlyRate.formatted}',
                    ),
                    if (r.note != null) Hint(r.note!),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Semantics(
                        label: context.t('kk.fl.deleteNamed', {'name': r.person, 'date': showDate(r.workedOn)}),
                        child: TextButton(
                          onPressed: busy ? null : () => _delete(r.id),
                          child: Text(context.t('kk.eq.delete')),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ErrorText(error),
          ],
        ),
      ],
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
  final _person = TextEditingController();
  final _hours = TextEditingController();
  final _rate = TextEditingController();
  final _note = TextEditingController();
  String? _on;
  bool _paid = false;

  @override
  void dispose() {
    for (final c in [_person, _hours, _rate, _note]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkAddFamilyLabor(
            spaceId: widget.spaceId,
            input: KkFamilyLaborInput(
              person: _person.text,
              hours: _hours.text,
              hourlyRate: _rate.text,
              paid: _paid,
              workedOn: _on,
              note: kkOpt(_note.text),
            ),
          ),
    );
    // Ism va baho qoladi — ketma-ket kunlarni tez yozish uchun.
    if (r != null) {
      setState(() {
        _hours.clear();
        _note.clear();
        _on = null;
        _paid = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    const gap = SizedBox(height: 12);
    return SectionCard(
      title: context.t('kk.fl.add'),
      semanticLabel: context.t('kk.fl.add'),
      children: [
        Field(label: context.t('kk.fl.person'), controller: _person),
        gap,
        DateField(label: context.t('kk.date'), value: _on, onChanged: (v) => setState(() => _on = v)),
        gap,
        Field(
          label: context.t('kk.fl.hours'),
          controller: _hours,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
        ),
        gap,
        AmountField(label: context.t('kk.fl.rate'), controller: _rate),
        Hint(context.t('kk.fl.rateHint')),
        gap,
        Field(label: context.t('kk.note'), controller: _note),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: _paid,
          title: Text(context.t('kk.fl.paid')),
          onChanged: (v) => setState(() => _paid = v ?? false),
        ),
        ErrorText(error),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.fl.addButton'))),
        ),
      ],
    );
  }
}
