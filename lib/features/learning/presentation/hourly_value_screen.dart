import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:baraka_daftari/features/learning/data/learning_providers.dart';
import 'package:baraka_daftari/features/learning/domain/learning_math.dart';
import 'package:baraka_daftari/features/learning/presentation/learning_widgets.dart';
import 'package:baraka_daftari/features/onboarding/data/onboarding_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// «Bir soatim qancha turadi?» kalkulyatori (SPEC 2H.1).
class HourlyValueScreen extends ConsumerStatefulWidget {
  const HourlyValueScreen({super.key});

  @override
  ConsumerState<HourlyValueScreen> createState() => _HourlyValueScreenState();
}

class _HourlyValueScreenState extends ConsumerState<HourlyValueScreen> {
  final _hours = TextEditingController();
  final _days = TextEditingController(text: '26');
  final _max = TextEditingController(
    text: hoursLabel(LearningMath.defaultMaxMinutesPerDay),
  );
  Money? _income;
  bool _suggested = false;
  HourlyValue? _result;
  Money? _previous;
  String? _error;

  @override
  void initState() {
    super.initState();
    _prefill();
  }

  /// Oxirgi hisob kirishlari yoki o'tgan oy daromadi.
  Future<void> _prefill() async {
    try {
      final s = await ref.read(learningServiceProvider.future);
      final latest = await s.latestSnapshot();
      final lastMonth = latest == null ? await s.lastMonthIncome() : null;
      if (!mounted) return;
      setState(() {
        if (latest != null) {
          _income ??= latest.income;
          _previous = latest.hourly;
          if (_hours.text.isEmpty) {
            _hours.text = hoursLabel(latest.minutesPerDay);
          }
          _days.text = '${latest.daysPerMonth}';
          _max.text = hoursLabel(latest.maxMinutesPerDay);
        } else if (lastMonth != null && _income == null) {
          _income = lastMonth;
          _suggested = true;
        }
      });
    } on Object {
      AppLog.event('hourly_prefill_failed');
    }
  }

  Future<void> _pickIncome() async {
    final household = ref.read(currentHouseholdProvider).valueOrNull;
    final a = await showAmountSheet(
      context,
      currency:
          _income?.currency ?? household?.baseCurrency ?? CurrencyCode.uzs,
      title: context.l10n.lnIncome,
      initial: _income,
    );
    if (a != null && mounted) {
      setState(() {
        _income = a;
        _suggested = false;
        _result = null;
      });
    }
  }

  Future<void> _calculate() async {
    final l10n = context.l10n;
    final minutes = parseHoursToMinutes(_hours.text);
    final max = parseHoursToMinutes(_max.text);
    final days = int.tryParse(_days.text.trim());
    final income = _income;
    if (minutes == null || max == null || days == null || income == null) {
      setState(() => _error = l10n.lnErrHours);
      return;
    }
    try {
      final (_, value) =
          await (await ref.read(
            learningServiceProvider.future,
          )).calculate(
            income: income,
            minutesPerDay: minutes,
            daysPerMonth: days,
            maxMinutesPerDay: max,
          );
      ref.invalidate(learningOverviewProvider);
      if (mounted) {
        setState(() {
          _result = value;
          _error = null;
        });
      }
      await recordTaskEvent(ref, TaskTrigger.hourlyValueCalculated);
    } on Object catch (e) {
      AppLog.event('hourly_calculate_failed');
      if (mounted) setState(() => _error = learningError(l10n, e));
    }
  }

  @override
  void dispose() {
    _hours.dispose();
    _days.dispose();
    _max.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final money = context.money;
    final theme = Theme.of(context);
    final result = _result;
    void reset(String _) => setState(() => _result = null);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.lnHourlyTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          const ContentDisclaimer(),
          ListTile(
            key: const Key('ln-income'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.lnIncome),
            subtitle: Text(
              [
                if (_income case final i?) money(i) else '—',
                if (_suggested) l10n.lnIncomeSuggested,
              ].join(' · '),
            ),
            trailing: const Icon(Icons.edit_outlined),
            onTap: _pickIncome,
          ),
          TextField(
            key: const Key('ln-hours'),
            controller: _hours,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: l10n.lnHoursPerDay),
            onChanged: reset,
          ),
          TextField(
            key: const Key('ln-days'),
            controller: _days,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: l10n.lnDaysPerMonth),
            onChanged: reset,
          ),
          TextField(
            key: const Key('ln-max'),
            controller: _max,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: l10n.lnMaxHours,
              helperText: l10n.lnMaxHoursHint,
              helperMaxLines: 3,
            ),
            onChanged: reset,
          ),
          const SizedBox(height: 12),
          FilledButton(
            key: const Key('ln-hourly-submit'),
            onPressed: _income == null ? null : _calculate,
            child: Text(l10n.lnHourlyCalc),
          ),
          if (_error case final e?)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                e,
                key: const Key('ln-hourly-error'),
                style: TextStyle(color: theme.colorScheme.error),
              ),
            ),
          if (result != null) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: HourlyResultView(value: result, previous: _previous),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
