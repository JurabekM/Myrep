import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import 'mf_entry_sheet.dart';
import 'mf_terms_card.dart';
import 'purpose_shares.dart';
import 'reserve_card.dart';
import 'return_card.dart';
import 'startup_card.dart';
import 'travel_debt_card.dart';
import 'two_shores_screen.dart';

const _actions = ['SALARY', 'EXPENSE', 'SENT_HOME', 'FUND_IN', 'FUND_OUT', 'OTHER_INCOME', 'OPENING', 'FUND_OPENING'];

/// Musofir bosh sahifasi (musofir/SPEC 1–4): 1-raqam — «Qaytish jamg'armasi» (ish valyutasida va
/// kurs bilan uy valyutasida), 2-raqam — «Shu oy o'z ulushi». Hamma summa va prognoz yadrodan tayyor.
class MfHomeScreen extends ConsumerWidget {
  const MfHomeScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(mfOverviewQuery(spaceId));
    final d = o.hasError ? null : o.valueOrNull;
    final s = d?.settings;
    return ScreenBody(
      mentorKey: 'mentor.mf',
      children: [
        if (o.hasError) ErrorText(o.error),
        if (d == null && !o.hasError) const Center(child: CircularProgressIndicator()),
        if (d != null && s == null)
          SectionCard(
            children: [_SetupForm(spaceId: spaceId, overview: d)],
          ),
        if (d != null && s != null) _Dashboard(spaceId: spaceId, d: d, s: s),
      ],
    );
  }
}

/// Sozlash formasi: mamlakat, ish valyutasi, o'z ulushi, maqsad va qaytish sanasi.
class _SetupForm extends ConsumerStatefulWidget {
  const _SetupForm({required this.spaceId, required this.overview, this.current, this.onDone});

  final String spaceId;
  final MfOverviewDto overview;
  final MfSettingsDto? current;
  final VoidCallback? onDone;

  @override
  ConsumerState<_SetupForm> createState() => _SetupFormState();
}

class _SetupFormState extends ConsumerState<_SetupForm> with ActionState {
  late final _country = TextEditingController(text: widget.current?.country);
  late String _currency = widget.current?.workCurrency ?? 'KRW';
  late final _share = TextEditingController(text: widget.current?.sharePercent ?? widget.overview.defaultSharePercent);
  late final _target = TextEditingController(text: widget.current?.target?.plain);
  late String? _returnOn = widget.current?.returnOn;

  @override
  void dispose() {
    for (final c in [_country, _share, _target]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfSetSettings(
            spaceId: widget.spaceId,
            input: MfSettingsInput(
              country: _country.text.trim().isEmpty ? null : _country.text.trim(),
              workCurrency: _currency,
              sharePercent: _share.text,
              target: _target.text.trim().isEmpty ? null : _target.text.trim(),
              returnOn: _returnOn,
            ),
          ),
    );
    if (r != null) widget.onDone?.call();
  }

  @override
  Widget build(BuildContext context) {
    final current = widget.current;
    final currencies = {...mfWorkCurrencies, _currency}.toList();
    return Semantics(
      container: true,
      label: context.t('mf.setup.title'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            header: true,
            child: Text(context.t('mf.setup.title'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          ),
          if (current == null) Hint(context.t('mf.setup.intro')),
          const SizedBox(height: 12),
          Field(label: context.t('mf.setup.country'), controller: _country),
          const SizedBox(height: 12),
          Select<String>(
            label: context.t('mf.setup.currency'),
            items: [for (final c in currencies) (c, context.t('mf.currency.$c'))],
            value: _currency,
            onChanged: current?.currencyLocked ?? false ? null : (v) => setState(() => _currency = v ?? _currency),
          ),
          const SizedBox(height: 12),
          Field(
            label: context.t('mf.setup.share'),
            controller: _share,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),
          Hint(context.t('mf.setup.shareHint')),
          const SizedBox(height: 12),
          AmountField(label: context.t('mf.setup.target'), controller: _target),
          Hint(context.t('mf.setup.targetHint')),
          const SizedBox(height: 12),
          DateField(
            label: context.t('mf.setup.returnOn'),
            value: _returnOn,
            onChanged: (v) => setState(() => _returnOn = v),
          ),
          ErrorText(error),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              FilledButton(onPressed: busy ? null : _save, child: Text(context.t('common.save'))),
              if (widget.onDone != null && current != null)
                TextButton(onPressed: widget.onDone, child: Text(context.t('common.cancel'))),
            ],
          ),
        ],
      ),
    );
  }
}

class _Dashboard extends ConsumerStatefulWidget {
  const _Dashboard({required this.spaceId, required this.d, required this.s});

  final String spaceId;
  final MfOverviewDto d;
  final MfSettingsDto s;

  @override
  ConsumerState<_Dashboard> createState() => _DashboardState();
}

class _DashboardState extends ConsumerState<_Dashboard> {
  bool _editing = false;

  /// Taklifning zaxira pul qismi qabul qilingan (shu natija uchun) — endi faqat jamg'arma qismi.
  MfIncomeRecordedDto? _reserveTaken;

  void _entry(String kind, {String? amount}) => openMfEntry(context, widget.spaceId, kind, initialAmount: amount);

  Widget? _offer(BuildContext context) {
    final r = ref.watch(mfOfferProvider);
    if (r == null || r.suggestedShare.minor == '0') return null;
    final reserve = !identical(_reserveTaken, r) && r.suggestedReserve.minor != '0' ? r.suggestedReserve : null;
    final fund = r.suggestedFund.minor != '0' ? r.suggestedFund : null;
    final notifier = ref.read(mfOfferProvider.notifier);
    return Container(
      key: const Key('mf-offer'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: context.palette.accent),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Semantics(
        liveRegion: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              reserve != null
                  ? context.t('mf.offerSplit', {
                      'share': r.suggestedShare.formatted,
                      'reserve': reserve.formatted,
                      'fund': fund?.formatted ?? '0',
                    })
                  : context.t('mf.offer', {'amount': (fund ?? r.suggestedShare).formatted}),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilledButton(
                  onPressed: () {
                    if (reserve != null) {
                      if (fund == null) {
                        notifier.state = null;
                      } else {
                        setState(() => _reserveTaken = r);
                      }
                      _entry('RESERVE_IN', amount: reserve.plain);
                    } else {
                      notifier.state = null;
                      _entry('FUND_IN', amount: (fund ?? r.suggestedShare).plain);
                    }
                  },
                  child: Text(context.t(reserve != null ? 'mf.offerReserve' : 'mf.offerAccept')),
                ),
                TextButton(onPressed: () => notifier.state = null, child: Text(context.t('mf.offerLater'))),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final s = widget.s;
    final m = d.month;
    final f = d.fund;
    final pal = context.palette;
    final rate = d.rate;
    final rateLine = rate != null && !rate.identity
        ? context.t('mf.rateLine', {
            'from': rate.fromCurrency,
            'rate': rate.rate,
            'to': rate.toCurrency,
            'date': showDate(rate.rateOn),
          })
        : null;
    String? pct(String? p) => p == null ? null : '$p %';
    final offer = _offer(context);
    final kpi = TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      color: pal.accent,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionCard(
          children: [
            Hint(context.t('mf.fund.title')),
            Text(f?.balance.formatted ?? '…', key: const Key('mf-fund'), style: kpi),
            if (f?.balanceHome != null) ...[
              Text('≈ ${f!.balanceHome!.formatted}', key: const Key('mf-fund-home')),
              if (rateLine != null) Hint(rateLine),
            ] else
              Hint(context.t('mf.noRateHome')),
          ],
        ),
        SectionCard(
          children: [
            Hint(context.t('mf.share.title', {'percent': s.sharePercent})),
            Text(m?.savedNet.formatted ?? '…', key: const Key('mf-share'), style: kpi),
            if (m != null) ...[
              Hint(context.t('mf.share.target', {'amount': m.shareTarget.formatted})),
              if (m.shareGap.minor != '0')
                Text(
                  context.t('mf.share.gap', {'amount': m.shareGap.formatted}),
                  key: const Key('mf-share-gap'),
                  style: TextStyle(color: pal.warn),
                ),
            ],
          ],
        ),
        if (offer != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: offer),
        if (m != null)
          for (final w in m.warnings)
            Container(
              key: Key('mf-warning-$w'),
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: pal.warn),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(context.t('mf.warning.$w', {'amount': m.shareGap.formatted})),
            ),
        if (f != null) _Prognosis(f: f, s: s),
        if (m != null) _Flow(d: d, m: m, pct: pct),
        _ShoresSummary(spaceId: widget.spaceId),
        MfTermsCard(spaceId: widget.spaceId),
        if (d.reserve != null) ReserveCard(spaceId: widget.spaceId, d: d, r: d.reserve!, onAction: _entry),
        StartupCard(spaceId: widget.spaceId, d: d, homeCurrency: s.homeCurrency),
        TravelDebtCard(spaceId: widget.spaceId),
        ReturnCard(spaceId: widget.spaceId, d: d, homeCurrency: s.homeCurrency),
        _RateCard(spaceId: widget.spaceId, d: d, s: s),
        SectionCard(
          title: context.t('mf.setup.summary'),
          children: [
            if (_editing)
              _SetupForm(
                spaceId: widget.spaceId,
                overview: d,
                current: s,
                onDone: () => setState(() => _editing = false),
              )
            else ...[
              Text([?s.country, context.t('mf.currency.${s.workCurrency}')].join(' · ')),
              Hint(context.t('mf.setup.summaryLine', {'percent': s.sharePercent})),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  onPressed: () => setState(() => _editing = true),
                  child: Text(context.t('mf.setup.edit')),
                ),
              ),
            ],
          ],
        ),
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Semantics(
            container: true,
            label: context.t('kk.actions'),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final (i, a) in _actions.indexed)
                  if (i == 0)
                    FilledButton(onPressed: () => _entry(a), child: Text(context.t('mf.action.$a')))
                  else
                    OutlinedButton(onPressed: () => _entry(a), child: Text(context.t('mf.action.$a'))),
              ],
            ),
          ),
        ),
        _Entries(spaceId: widget.spaceId, d: d),
      ],
    );
  }
}

class _Prognosis extends StatelessWidget {
  const _Prognosis({required this.f, required this.s});

  final MfFundDto f;
  final MfSettingsDto s;

  @override
  Widget build(BuildContext context) {
    final pal = context.palette;
    final tone = switch (f.status) {
      'BEHIND' || 'NO_SAVING' => pal.warn,
      'REACHED' || 'ON_TRACK' => pal.accentText,
      _ => pal.inkMuted,
    };
    final target = f.target;
    return SectionCard(
      title: context.t('mf.prognosis.title'),
      children: [
        Text(
          context.t('mf.fund.status.${f.status}', {
            'months': f.monthsToTarget ?? 0,
            'shortfall': f.shortfallAtReturn?.formatted ?? '',
          }),
          key: const Key('mf-fund-status'),
          style: TextStyle(color: tone),
        ),
        if (target != null && f.progressBp != null) ...[
          const SizedBox(height: 8),
          BpProgress(bp: f.progressBp!, label: context.t('mf.prognosis.progress')),
          const SizedBox(height: 4),
          Hint(context.t('mf.prognosis.progressLine', {'percent': f.progressPercent, 'target': target.formatted})),
        ],
        const SizedBox(height: 4),
        if (target != null) ValueRow(context.t('mf.prognosis.target'), target.formatted),
        if (f.remainingHome != null) ValueRow(context.t('mf.prognosis.remaining'), f.remainingHome!.formatted),
        ValueRow(
          context.t('mf.prognosis.avg', {'count': f.monthsUsed}),
          f.avgMonthly?.formatted ?? context.t('mf.prognosis.noHistory'),
        ),
        if (f.avgMonthlyHome != null) Hint('≈ ${f.avgMonthlyHome!.formatted}'),
        if ((f.monthsToTarget ?? 0) > 0)
          ValueRow(
            context.t('mf.prognosis.monthsToTarget'),
            context.t('mf.months', {'count': f.monthsToTarget}),
            key: const Key('mf-months-to-target'),
          ),
        if (s.returnOn != null)
          ValueRow(
            context.t('mf.prognosis.returnOn', {'date': showDate(s.returnOn!)}),
            context.t('mf.months', {'count': f.monthsUntilReturn ?? 0}),
          ),
        if (f.projectedHome != null)
          ValueRow(
            context.t('mf.prognosis.projected'),
            f.projectedHome!.formatted,
            strong: true,
            key: const Key('mf-projected'),
          ),
        if (f.shortfallAtReturn != null && f.shortfallAtReturn!.minor != '0')
          ValueRow(
            context.t('mf.prognosis.shortfall'),
            f.shortfallAtReturn!.formatted,
            key: const Key('mf-shortfall'),
          ),
      ],
    );
  }
}

/// Oylik oqim: daromad → xarajat → uyga → jamg'arma → zaxira pul → cho'ntakda.
class _Flow extends StatelessWidget {
  const _Flow({required this.d, required this.m, required this.pct});

  final MfOverviewDto d;
  final MfMonthDto m;
  final String? Function(String?) pct;

  Widget _row(BuildContext context, String label, String value, {String? hint, Key? key, bool strong = false}) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ValueRow(label, value, strong: strong, key: key),
          if (hint != null)
            Align(
              alignment: Alignment.centerRight,
              child: Hint(hint),
            ),
        ],
      );

  @override
  Widget build(BuildContext context) => SectionCard(
    title: context.t('mf.flow.title'),
    children: [
      Hint(context.t('kk.period', {'from': showDate(d.periodStart), 'to': showDate(d.periodEnd)})),
      _row(context, context.t('mf.flow.income'), m.income.formatted, key: const Key('mf-income')),
      _row(context, context.t('mf.flow.expenses'), '− ${m.expenses.formatted}', hint: pct(m.expensesPercent)),
      _row(
        context,
        context.t('mf.flow.sentHome'),
        '− ${m.sentHome.formatted}',
        hint: pct(m.sentPercent),
        key: const Key('mf-sent'),
      ),
      if (m.fees.minor != '0') _row(context, context.t('mf.flow.fees'), '− ${m.fees.formatted}'),
      _row(context, context.t('mf.flow.fund'), '− ${m.fundNet.formatted}', hint: pct(m.fundPercent)),
      if (m.reserveIn.minor != '0')
        _row(
          context,
          context.t('mf.flow.reserveIn'),
          '− ${m.reserveIn.formatted}',
          hint: pct(m.reservePercent),
          key: const Key('mf-reserve-in'),
        ),
      if (m.reserveOut.minor != '0') _row(context, context.t('mf.flow.reserveOut'), '+ ${m.reserveOut.formatted}'),
      _row(context, context.t('mf.flow.pocket'), m.pocket.formatted, strong: true, key: const Key('mf-pocket')),
      Hint(context.t('mf.flow.hint')),
    ],
  );
}

/// «Ikki qirg'oq» xulosasi: uyda maqsadlar qoldig'i (uy tomoni yozuvlari fayl orqali keladi).
class _ShoresSummary extends ConsumerWidget {
  const _ShoresSummary({required this.spaceId});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final v = ref.watch(mfTwoShoresQuery(spaceId));
    final d = v.hasError ? null : v.valueOrNull;
    if (d == null || d.remittances.isEmpty) return const SizedBox.shrink();
    final pal = context.palette;
    return SectionCard(
      title: context.t('mf.shores.summary'),
      trailing: d.pending > 0
          ? Text(context.t('mf.shores.pending', {'count': d.pending}), style: TextStyle(color: pal.warn))
          : null,
      children: [
        PurposesTable(d),
        if (d.overspent) Text(context.t('mf.shores.overspent'), style: TextStyle(color: pal.warn)),
      ],
    );
  }
}

class _RateCard extends ConsumerStatefulWidget {
  const _RateCard({required this.spaceId, required this.d, required this.s});

  final String spaceId;
  final MfOverviewDto d;
  final MfSettingsDto s;

  @override
  ConsumerState<_RateCard> createState() => _RateCardState();
}

class _RateCardState extends ConsumerState<_RateCard> with ActionState {
  final _rate = TextEditingController();
  final _source = TextEditingController();
  String? _rateOn;

  @override
  void dispose() {
    _rate.dispose();
    _source.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .mfSetRate(
            spaceId: widget.spaceId,
            input: MfRateInput(
              rate: _rate.text,
              rateOn: _rateOn,
              source: _source.text.trim().isEmpty ? null : _source.text.trim(),
            ),
          ),
    );
    if (r != null) {
      _rate.clear();
      _source.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final rate = widget.d.rate;
    final s = widget.s;
    final pal = context.palette;
    if (rate?.identity ?? false) {
      return SectionCard(title: context.t('mf.rate.title'), children: [Hint(context.t('mf.rate.identity'))]);
    }
    return SectionCard(
      title: context.t('mf.rate.title'),
      children: [
        if (rate != null) ...[
          Text(
            [
              context.t('mf.rateLine', {
                'from': rate.fromCurrency,
                'rate': rate.rate,
                'to': rate.toCurrency,
                'date': showDate(rate.rateOn),
              }),
              ?rate.source,
            ].join(' · '),
            key: const Key('mf-rate'),
            style: TextStyle(color: rate.stale ? pal.warn : null),
          ),
          if (rate.stale) Text(context.t('mf.rate.stale'), style: TextStyle(color: pal.warn)),
        ] else
          Hint(context.t('mf.rate.none')),
        const SizedBox(height: 12),
        Field(
          label: context.t('mf.rate.input', {'from': s.workCurrency, 'to': s.homeCurrency}),
          controller: _rate,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
        ),
        const SizedBox(height: 12),
        DateField(label: context.t('kk.date'), value: _rateOn, onChanged: (v) => setState(() => _rateOn = v)),
        const SizedBox(height: 12),
        Field(label: context.t('mf.rate.source'), controller: _source),
        Hint(context.t('mf.rate.hint')),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(onPressed: busy ? null : _save, child: Text(context.t('mf.rate.save'))),
        ),
      ],
    );
  }
}

class _Entries extends ConsumerWidget {
  const _Entries({required this.spaceId, required this.d});

  final String spaceId;
  final MfOverviewDto d;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(categoriesQuery(spaceId)).valueOrNull ?? const <CategoryDto>[];
    final pal = context.palette;
    return SectionCard(
      title: context.t('kk.entries'),
      children: [
        if (d.entries.isEmpty) Hint(context.t('kk.noEntries')),
        for (final e in d.entries)
          Container(
            key: ValueKey(('mf-entry', e)),
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: pal.line)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${showDate(e.occurredOn)} · ${context.t('mf.kind.${e.kind}')}'),
                      Hint(
                        [
                          categoryName(context, categories, e.categoryId),
                          if (e.fee != null) context.t('mf.feeShort', {'amount': e.fee!.formatted}),
                          if (e.received != null) context.t('mf.receivedShort', {'amount': e.received!.formatted}),
                          ?e.note,
                        ].where((x) => x.isNotEmpty).join(' · '),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  e.amount.formatted,
                  style: TextStyle(
                    color: e.kind == 'SALARY' || e.kind == 'OTHER_INCOME' ? pal.accentText : null,
                    fontFeatures: const [FontFeature.tabularFigures()],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
