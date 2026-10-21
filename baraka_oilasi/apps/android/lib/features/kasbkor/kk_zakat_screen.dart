import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

/// `1448-06-09` → «9 jumodul oxir 1448».
String _hijri(BuildContext context, String s) {
  final p = s.split('-').map((x) => int.tryParse(x) ?? 0).toList();
  if (p.length < 3) return s;
  return context.t('kk.hijri.date', {'day': p[2], 'month': context.t('kk.hijri.m${p[1]}'), 'year': p[0]});
}

/// Zakot hisobi (kasbkor/SPEC 8.3) — **hisob, fatvo emas**. Diniy izoh faqat ulamo tasdiqlagan bo'lsa
/// (yadro `religiousNote` beradi). «Zakot kuni» — hijriy sana, jadvalli kalendar (±1–2 kun).
class KkZakatScreen extends ConsumerStatefulWidget {
  const KkZakatScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkZakatScreen> createState() => _KkZakatScreenState();
}

class _KkZakatScreenState extends ConsumerState<KkZakatScreen> with ActionState {
  final _hopeless = <String>[];
  bool? _hawl;

  KkZakatInput _input() => KkZakatInput(hopelessSaleIds: List.of(_hopeless), hawlComplete: _hawl);

  Future<void> _save() => act(() => ref.read(coreProvider).kkSaveZakat(spaceId: widget.spaceId, input: _input()));

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final pal = context.palette;
    final settings = ref.watch(query(['kkGrowthSettings', id], (c) => c.kkGrowthSettings(spaceId: id))).valueOrNull;
    final input = _input();
    final draft = ref.watch(
      query(['kkZakat', id, ..._hopeless, '|', _hawl], (c) => c.kkZakatDraft(spaceId: id, input: input)),
    );
    final history = ref.watch(query(['kkZakatHistory', id], (c) => c.kkZakatHistory(spaceId: id))).valueOrNull;
    final z = draft.hasError ? null : draft.valueOrNull;
    final note = z?.religiousNote;
    return ScreenBody(
      mentorKey: 'mentor.kkZakat',
      children: [
        Card(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: pal.warn),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(context.t('kk.zakat.disclaimer'), style: TextStyle(color: pal.warn)),
          ),
        ),
        if (note != null) Hint(context.t(note)),
        if (settings != null) _ZakatSettings(key: ValueKey(settings), spaceId: id, s: settings),
        if (draft.hasError) ErrorText(draft.error),
        if (z != null) ...[
          _Calculation(z),
          SectionCard(
            title: context.t('kk.zakat.adjust'),
            children: [
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                value: z.hawlComplete,
                title: Text(context.t('kk.zakat.hawl')),
                subtitle: Text(
                  z.hawlSince != null
                      ? context.t(z.hawlSuggested ? 'kk.zakat.hawlYes' : 'kk.zakat.hawlNo', {
                          'date': showDate(z.hawlSince!),
                        })
                      : context.t('kk.zakat.hawlNoData'),
                ),
                onChanged: (v) => setState(() => _hawl = v ?? false),
              ),
              if (z.receivableLines.any((r) => r.d90Plus)) ...[
                const SizedBox(height: 8),
                Text(context.t('kk.zakat.hopeless')),
                for (final r in z.receivableLines.where((r) => r.d90Plus))
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    value: _hopeless.contains(r.saleId),
                    title: Text(
                      context.t('kk.zakat.hopelessLine', {
                        'customer': r.customer,
                        'item': r.item,
                        'amount': r.outstanding.formatted,
                        'days': r.overdueDays,
                      }),
                    ),
                    onChanged: (v) => setState(() => v ?? false ? _hopeless.add(r.saleId) : _hopeless.remove(r.saleId)),
                  ),
              ],
              ErrorText(error),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(
                  onPressed: busy || z.goldPrice == null ? null : _save,
                  child: Text(context.t('kk.zakat.save')),
                ),
              ),
            ],
          ),
        ],
        if (history != null && history.isNotEmpty)
          SectionCard(
            title: context.t('kk.zakat.history'),
            children: [
              for (final h in history)
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  decoration: BoxDecoration(
                    border: Border(top: BorderSide(color: pal.line)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text.rich(
                        TextSpan(
                          children: [
                            TextSpan(
                              text: showDate(h.calculatedOn),
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                            TextSpan(
                              text: ' (${_hijri(context, h.hijriDate)})',
                              style: TextStyle(color: pal.inkMuted),
                            ),
                          ],
                        ),
                      ),
                      ValueRow(context.t('kk.zakat.base'), h.base.formatted),
                      ValueRow(context.t('kk.zakat.nisab'), h.nisab.formatted),
                      ValueRow(
                        context.t('kk.zakat.amount'),
                        h.reason != null ? context.t('kk.zakat.reason.${h.reason}') : h.zakat.formatted,
                        strong: true,
                      ),
                    ],
                  ),
                ),
            ],
          ),
      ],
    );
  }
}

class _Calculation extends StatelessWidget {
  const _Calculation(this.z);

  final KkZakatDto z;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    return SectionCard(
      title: context.t('kk.zakat.calc'),
      children: [
        Hint('${showDate(z.calculatedOn)} · ${_hijri(context, z.hijriDate)}'),
        const SizedBox(height: 4),
        ValueRow(context.t('kk.zakat.stock.${z.valuation}'), z.stock.formatted),
        ValueRow(context.t('kk.zakat.cash'), '+ ${z.cash.formatted}'),
        ValueRow(context.t('kk.zakat.receivables'), '+ ${z.receivables.formatted}'),
        ValueRow(context.t('kk.zakat.payables'), '− ${z.payables.formatted}'),
        ValueRow(context.t('kk.zakat.wages'), '− ${z.wagesDue.formatted}'),
        const Divider(),
        ValueRow(context.t('kk.zakat.base'), z.base.formatted, strong: true, key: const Key('kk-zakat-base')),
        ValueRow(
          context.t('kk.zakat.nisabLine', {'grams': z.nisabGrams, 'price': z.goldPrice?.formatted ?? '—'}),
          z.nisab?.formatted ?? '—',
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            border: Border.all(color: pal.line),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Hint(context.t('kk.zakat.amountLong')),
              Text(
                z.zakat.formatted,
                key: const Key('kk-zakat-amount'),
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: pal.accent,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
              if (z.reason != null) Text(context.t('kk.zakat.reason.${z.reason}'), style: TextStyle(color: pal.warn)),
            ],
          ),
        ),
      ],
    );
  }
}

class _ZakatSettings extends ConsumerStatefulWidget {
  const _ZakatSettings({required this.spaceId, required this.s, super.key});

  final String spaceId;
  final KkGrowthSettingsDto s;

  @override
  ConsumerState<_ZakatSettings> createState() => _ZakatSettingsState();
}

class _ZakatSettingsState extends ConsumerState<_ZakatSettings> with ActionState {
  late int? _month = widget.s.zakatMonth;
  late final _day = TextEditingController(text: widget.s.zakatDay == null ? '' : '${widget.s.zakatDay}');
  late final _gold = TextEditingController(text: widget.s.goldPrice?.plain ?? '');
  late final _grams = TextEditingController(text: '${widget.s.nisabGrams}');
  late String _valuation = widget.s.stockValuation;

  @override
  void dispose() {
    for (final c in [_day, _gold, _grams]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() {
    final s = widget.s;
    return act(
      () => ref
          .read(coreProvider)
          .kkSetGrowthSettings(
            spaceId: widget.spaceId,
            input: KkGrowthSettingsInput(
              reserveMonths: s.reserveMonths,
              maxBadPercent: s.maxBadPercent,
              zakatMonth: _month,
              zakatDay: _month == null ? null : (int.tryParse(_day.text.trim()) ?? 1),
              goldPrice: _gold.text.trim().isEmpty ? null : _gold.text.trim(),
              nisabGrams: int.tryParse(_grams.text.trim()) ?? 0,
              stockValuation: _valuation,
              scaleReminder: s.scaleReminder,
            ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final next = s.nextZakatDay;
    return SectionCard(
      title: context.t('kk.zakat.settings'),
      children: [
        Hint(context.t('kk.zakat.today', {'date': _hijri(context, s.todayHijri)})),
        const SizedBox(height: 12),
        Text(context.t('kk.zakat.day')),
        const SizedBox(height: 8),
        Select<int?>(
          label: context.t('kk.zakat.month'),
          items: [
            (null, context.t('kk.zakat.notSet')),
            for (var m = 1; m <= 12; m++) (m, context.t('kk.hijri.m$m')),
          ],
          value: _month,
          onChanged: (v) => setState(() => _month = v),
        ),
        const SizedBox(height: 12),
        Field(label: context.t('kk.zakat.dayOfMonth'), controller: _day, keyboardType: TextInputType.number),
        const SizedBox(height: 4),
        Hint(next != null ? context.t('kk.zakat.next', {'date': showDate(next)}) : context.t('kk.zakat.dayHint')),
        const SizedBox(height: 12),
        AmountField(label: context.t('kk.zakat.gold'), controller: _gold),
        const SizedBox(height: 12),
        Field(label: context.t('kk.zakat.grams'), controller: _grams, keyboardType: TextInputType.number),
        const SizedBox(height: 12),
        Select<String>(
          label: context.t('kk.zakat.valuation'),
          items: [
            for (final v in ['REPLACEMENT', 'BOOK']) (v, context.t('kk.zakat.stock.$v')),
          ],
          value: _valuation,
          onChanged: (v) => setState(() => _valuation = v ?? _valuation),
        ),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
        ),
      ],
    );
  }
}
