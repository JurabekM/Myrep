import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/scam_math.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

String offerQuestionText(AppLocalizations l10n, OfferQuestion q) => switch (q) {
  OfferQuestion.guaranteed => l10n.offerQGuaranteed,
  OfferQuestion.lossShared => l10n.offerQLoss,
  OfferQuestion.realGoods => l10n.offerQReal,
  OfferQuestion.recruitment => l10n.offerQRecruit,
  OfferQuestion.pressure => l10n.offerQPressure,
  OfferQuestion.writtenContract => l10n.offerQContract,
  OfferQuestion.exitEasy => l10n.offerQExit,
  OfferQuestion.license => l10n.offerQLicense,
  OfferQuestion.verifiedInPerson => l10n.offerQVerified,
};

String offerFlagText(
  AppLocalizations l10n,
  OfferFlag f,
  OfferAnswer answer,
) => answer == OfferAnswer.unknown
    ? l10n.offerFlagUnknown(offerQuestionText(l10n, f.question))
    : switch (f.question) {
        OfferQuestion.guaranteed => l10n.offerFlagGuaranteed,
        OfferQuestion.lossShared => l10n.offerFlagLoss,
        OfferQuestion.realGoods => l10n.offerFlagReal,
        OfferQuestion.recruitment => l10n.offerFlagRecruit,
        OfferQuestion.pressure => l10n.offerFlagPressure,
        OfferQuestion.writtenContract => l10n.offerFlagContract,
        OfferQuestion.exitEasy => l10n.offerFlagExit,
        OfferQuestion.license => l10n.offerFlagLicense,
        OfferQuestion.verifiedInPerson => l10n.offerFlagVerified,
      };

String offerVerdictLabel(AppLocalizations l10n, OfferVerdict v) => switch (v) {
  OfferVerdict.green => l10n.offerVerdictGreen,
  OfferVerdict.yellow => l10n.offerVerdictYellow,
  OfferVerdict.red => l10n.offerVerdictRed,
};

String offerSignText(AppLocalizations l10n, ScamSign s) => switch (s) {
  ScamSign.guaranteedHighReturn => l10n.offerSignGuaranteed,
  ScamSign.urgency => l10n.offerSignUrgency,
  ScamSign.recruitmentIncome => l10n.offerSignRecruit,
  ScamSign.noRealBusiness => l10n.offerSignNoBusiness,
  ScamSign.hardExit => l10n.offerSignHardExit,
};

String offerCategoryText(AppLocalizations l10n, OfferCategory c) => switch (c) {
  OfferCategory.ribo => l10n.offerCatRibo,
  OfferCategory.gharar => l10n.offerCatGharar,
  OfferCategory.qimor => l10n.offerCatQimor,
};

String offerDecisionLabel(AppLocalizations l10n, OfferDecision d) =>
    switch (d) {
      OfferDecision.declined => l10n.offerDecisionDeclined,
      OfferDecision.postponed => l10n.offerDecisionPostponed,
      OfferDecision.accepted => l10n.offerDecisionAccepted,
    };

String offerError(AppLocalizations l10n, String code) => switch (code) {
  OfferCheckService.errAdvisorRequired => l10n.offerErrAdvisor,
  OfferCheckService.errCoolingOff => l10n.offerErrCoolingOff,
  OfferCheckService.errDecided => l10n.offerErrDecided,
  OfferCheckService.errBadRate => l10n.offerErrRate,
  _ => l10n.genericError,
};

/// bp ko'paytma → «5,2» (barobar).
String _multiple(int bp) => percentLabel(MoneyRounding.divide(bp, 100));

/// Toshkent vaqti: «20.10.2026 14:05».
String _tashkentTime(DateTime instant) {
  final local = instant.toUtc().add(Tashkent.utcOffset);
  String two(int n) => n.toString().padLeft(2, '0');
  return '${formatDate(Tashkent.dateOf(instant))} '
      '${two(local.hour)}:${two(local.minute)}';
}

/// «Kafolatlangan foyda» detektori (SPEC 2E.5) va 7-qonun: besh xavf
/// belgisi, «o'z ko'zim bilan ko'raman», va'da qilingan foyda, piramida,
/// «to'xta, maslahatlash» (SPEC 2G).
class OfferCheckScreen extends ConsumerStatefulWidget {
  const OfferCheckScreen({super.key});

  @override
  ConsumerState<OfferCheckScreen> createState() => _OfferCheckScreenState();
}

class _OfferCheckScreenState extends ConsumerState<OfferCheckScreen> {
  final _title = TextEditingController();
  final _rate = TextEditingController();
  final _recruits = TextEditingController(text: '5');
  final _population = TextEditingController(text: '1000000');
  final Map<OfferQuestion, OfferAnswer> _answers = {};
  Money? _amount;
  OfferCheckRecord? _saved;
  bool _shown = false;

  @override
  void dispose() {
    _title.dispose();
    _rate.dispose();
    _recruits.dispose();
    _population.dispose();
    super.dispose();
  }

  /// Oylik stavka (bp); bo'sh — `null`, noto'g'ri — `-1`.
  int? get _rateBp {
    final text = _rate.text.trim();
    if (text.isEmpty) return null;
    return parsePercentBp(text) ?? -1;
  }

  Future<void> _evaluate() async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final rate = _rateBp;
    if (rate == -1) {
      messenger.showSnackBar(SnackBar(content: Text(l10n.offerErrRate)));
      return;
    }
    setState(() => _shown = true);
    try {
      final (record, _) = await (await ref.read(
        offerCheckServiceProvider.future,
      )).save(_title.text, _answers, amount: _amount, promisedMonthlyBp: rate);
      ref.invalidate(offerChecksProvider);
      if (mounted) setState(() => _saved = record);
      await recordTaskEvent(ref, TaskTrigger.offerChecked);
    } on Object {
      AppLog.event('offer_check_save_failed');
    }
  }

  Future<void> _pickAmount() async {
    final a = await showAmountSheet(
      context,
      currency: CurrencyCode.uzs,
      title: context.l10n.offerAmount,
      initial: _amount,
    );
    if (a != null && mounted) {
      setState(() {
        _amount = a;
        _shown = false;
      });
    }
  }

  Color _color(BuildContext context, OfferVerdict v) {
    final scheme = Theme.of(context).colorScheme;
    return switch (v) {
      OfferVerdict.green => scheme.primaryContainer,
      OfferVerdict.yellow => scheme.tertiaryContainer,
      OfferVerdict.red => scheme.errorContainer,
    };
  }

  Future<void> _openDecision(OfferCheckRecord check) =>
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (context) => Padding(
          padding: EdgeInsets.fromLTRB(
            16,
            16,
            16,
            16 + MediaQuery.viewInsetsOf(context).bottom,
          ),
          child: OfferDecisionPanel(
            check: check,
            onDecided: (_) => Navigator.pop(context),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final e = evaluateOffer(_answers);
    final history = ref.watch(offerChecksProvider).valueOrNull ?? const [];
    final allAnswered = _answers.length == OfferQuestion.values.length;
    final rate = _rateBp;
    final promised = rate != null && rate > 0 ? promisedMultiple(rate) : null;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.offerTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(l10n.offerHint, style: theme.textTheme.bodyMedium),
          TextField(
            key: const Key('offer-title'),
            controller: _title,
            decoration: InputDecoration(labelText: l10n.offerName),
          ),
          const SizedBox(height: 12),
          _VerifyCard(),
          const SizedBox(height: 12),
          for (final q in OfferQuestion.values) ...[
            Text(offerQuestionText(l10n, q)),
            const SizedBox(height: 4),
            SegmentedButton<OfferAnswer>(
              key: Key('offer-q-${q.name}'),
              emptySelectionAllowed: true,
              showSelectedIcon: false,
              segments: [
                for (final (a, label) in [
                  (OfferAnswer.yes, l10n.offerYes),
                  (OfferAnswer.no, l10n.offerNo),
                  (OfferAnswer.unknown, l10n.offerUnknown),
                ])
                  ButtonSegment(
                    value: a,
                    label: Text(label, key: Key('offer-${q.name}-${a.name}')),
                  ),
              ],
              selected: {?_answers[q]},
              onSelectionChanged: (s) => setState(() {
                _shown = false;
                if (s.isEmpty) {
                  _answers.remove(q);
                } else {
                  _answers[q] = s.single;
                }
              }),
            ),
            const SizedBox(height: 12),
          ],
          TextField(
            key: const Key('offer-rate'),
            controller: _rate,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: l10n.offerRate),
            onChanged: (_) => setState(() => _shown = false),
          ),
          if (promised != null) ...[
            const SizedBox(height: 8),
            Card(
              key: const Key('offer-rate-yearly'),
              color: theme.colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  l10n.offerRateYearly(
                    percentLabel(rate!),
                    _multiple(promised.simpleBp),
                    _multiple(promised.compoundBp),
                  ),
                ),
              ),
            ),
          ],
          ListTile(
            key: const Key('offer-amount'),
            contentPadding: EdgeInsets.zero,
            title: Text(l10n.offerAmount),
            subtitle: Text(_amount == null ? '—' : money(_amount!)),
            trailing: const Icon(Icons.edit_outlined),
            onTap: _pickAmount,
          ),
          const SizedBox(height: 8),
          FilledButton(
            key: const Key('offer-evaluate'),
            onPressed: allAnswered ? _evaluate : null,
            child: Text(l10n.offerCheck),
          ),
          if (_shown) ...[
            const SizedBox(height: 12),
            _ResultCard(
              evaluation: e,
              answers: _answers,
              color: _color(context, e.verdict),
            ),
            if (_saved case final saved?) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: OfferDecisionPanel(
                    key: ValueKey(saved.meta.id),
                    check: saved,
                    onDecided: (r) => setState(() => _saved = r),
                  ),
                ),
              ),
            ],
          ],
          const SizedBox(height: 12),
          _PyramidCard(recruits: _recruits, population: _population),
          if (history.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(l10n.offerHistory, style: theme.textTheme.titleSmall),
            for (final h in history.take(10))
              ListTile(
                key: Key('offer-history-${h.meta.id}'),
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.circle, color: _color(context, h.verdict)),
                title: Text(h.title.isEmpty ? l10n.offerTitle : h.title),
                subtitle: Text(
                  [
                    offerVerdictLabel(l10n, h.verdict),
                    formatDate(Tashkent.dateOf(h.meta.createdAt)),
                    if (h.decision case final d?) offerDecisionLabel(l10n, d),
                  ].join(' · '),
                ),
                trailing: _isOpen(h) ? const Icon(Icons.chevron_right) : null,
                onTap: _isOpen(h) ? () => _openDecision(h) : null,
              ),
          ],
        ],
      ),
    );
  }

  static bool _isOpen(OfferCheckRecord r) =>
      r.decision == null || r.decision == OfferDecision.postponed;
}

/// «Ishni o'z ko'zim bilan ko'raman» (SPEC 2G.2).
class _VerifyCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    return Card(
      key: const Key('offer-verify'),
      color: theme.colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.offerVerifyTitle, style: theme.textTheme.titleSmall),
            const SizedBox(height: 4),
            for (final item in [
              l10n.offerVerifyGoods,
              l10n.offerVerifyDocs,
              l10n.offerVerifyLicense,
              l10n.offerVerifySource,
              l10n.offerVerifyExit,
            ])
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.visibility_outlined, size: 18),
                    const SizedBox(width: 6),
                    Expanded(child: Text(item)),
                  ],
                ),
              ),
            const SizedBox(height: 8),
            Text(l10n.offerVerifyHint, style: theme.textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.evaluation,
    required this.answers,
    required this.color,
  });

  final OfferEvaluation evaluation;
  final Map<OfferQuestion, OfferAnswer> answers;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final e = evaluation;
    return Card(
      key: Key('offer-result-${e.verdict.name}'),
      color: color,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              switch (e.verdict) {
                OfferVerdict.green => l10n.offerGreen,
                OfferVerdict.yellow => l10n.offerYellow,
                OfferVerdict.red => l10n.offerRed,
              },
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(l10n.offerSignsTitle, style: theme.textTheme.titleSmall),
            Text(
              switch (e.level) {
                ScamLevel.none => l10n.offerSignsNone,
                ScamLevel.caution => l10n.offerSignsCaution,
                ScamLevel.flee => l10n.offerSignsFlee,
              },
              key: Key('offer-signs-${e.level.name}'),
            ),
            for (final s in e.signs)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.warning_amber_rounded,
                      size: 18,
                      color: theme.colorScheme.error,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        offerSignText(l10n, s),
                        key: Key('offer-sign-${s.name}'),
                      ),
                    ),
                  ],
                ),
              ),
            for (final c in e.categories)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  offerCategoryText(l10n, c),
                  key: Key('offer-cat-${c.name}'),
                  style: theme.textTheme.bodySmall,
                ),
              ),
            for (final f in e.flags)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.flag,
                      size: 18,
                      // «Sariq» bayroq haqiqatan sariq bo'lsin.
                      color: f.level == OfferVerdict.red
                          ? theme.colorScheme.error
                          : Colors.amber.shade800,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        offerFlagText(
                          l10n,
                          f,
                          answers[f.question] ?? OfferAnswer.unknown,
                        ),
                        key: Key('offer-flag-${f.question.name}'),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// «To'xta, maslahatlash» (SPEC 2G.6): «pul qo'yaman» maslahatchi ismidan
/// va 24 soatdan keyin ochiladi.
class OfferDecisionPanel extends ConsumerStatefulWidget {
  const OfferDecisionPanel({
    required this.check,
    required this.onDecided,
    super.key,
  });

  final OfferCheckRecord check;
  final ValueChanged<OfferCheckRecord> onDecided;

  @override
  ConsumerState<OfferDecisionPanel> createState() => _OfferDecisionPanelState();
}

class _OfferDecisionPanelState extends ConsumerState<OfferDecisionPanel> {
  late final _advisor = TextEditingController(text: widget.check.advisor);
  bool _busy = false;

  @override
  void dispose() {
    _advisor.dispose();
    super.dispose();
  }

  Future<void> _decide(OfferDecision d) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      final r = await (await ref.read(
        offerCheckServiceProvider.future,
      )).decide(widget.check, d, advisor: _advisor.text);
      ref.invalidate(offerChecksProvider);
      messenger.showSnackBar(SnackBar(content: Text(l10n.offerDecisionSaved)));
      widget.onDecided(r);
    } on DomainRuleException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(offerError(l10n, e.code))));
    } on Object {
      AppLog.event('offer_decision_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final check = widget.check;
    final decided =
        check.decision == OfferDecision.declined ||
        check.decision == OfferDecision.accepted;
    final opensAt = acceptOpensAt(check.meta.createdAt);
    final waiting = ref.read(clockProvider).nowUtc().isBefore(opensAt);
    final canAccept = !waiting && _advisor.text.trim().isNotEmpty && !_busy;
    return Column(
      key: const Key('offer-decision'),
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l10n.offerDecisionTitle, style: theme.textTheme.titleSmall),
        if (decided)
          Text(offerDecisionLabel(l10n, check.decision!))
        else ...[
          TextField(
            key: const Key('offer-advisor'),
            controller: _advisor,
            decoration: InputDecoration(labelText: l10n.offerAdvisor),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 4),
          Text(l10n.offerAdviceNote, style: theme.textTheme.bodySmall),
          if (waiting)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                l10n.offerAcceptOpensAt(_tashkentTime(opensAt)),
                key: const Key('offer-accept-wait'),
                style: theme.textTheme.bodySmall,
              ),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.tonal(
                key: const Key('offer-decline'),
                onPressed: _busy ? null : () => _decide(OfferDecision.declined),
                child: Text(l10n.offerDecline),
              ),
              OutlinedButton(
                key: const Key('offer-postpone'),
                onPressed: _busy
                    ? null
                    : () => _decide(OfferDecision.postponed),
                child: Text(l10n.offerPostpone),
              ),
              OutlinedButton(
                key: const Key('offer-accept'),
                onPressed: canAccept
                    ? () => _decide(OfferDecision.accepted)
                    : null,
                child: Text(l10n.offerAccept),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

/// Piramida ta'limiy hisobi (SPEC 2G.4).
class _PyramidCard extends StatefulWidget {
  const _PyramidCard({required this.recruits, required this.population});

  final TextEditingController recruits;
  final TextEditingController population;

  @override
  State<_PyramidCard> createState() => _PyramidCardState();
}

class _PyramidCardState extends State<_PyramidCard> {
  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final k = int.tryParse(widget.recruits.text.trim());
    final n = int.tryParse(widget.population.text.replaceAll(' ', ''));
    final model = k != null && k >= 2 && n != null && n >= 1
        ? pyramidLevels(recruitsPerPerson: k, population: n)
        : null;
    return Card(
      child: ExpansionTile(
        key: const Key('offer-pyramid'),
        leading: const Icon(Icons.change_history),
        title: Text(l10n.offerPyramidTitle),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        expandedCrossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            key: const Key('pyramid-k'),
            controller: widget.recruits,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: l10n.offerPyramidRecruits),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('pyramid-n'),
            controller: widget.population,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: l10n.offerPyramidPopulation,
            ),
            onChanged: (_) => setState(() {}),
          ),
          if (model != null) ...[
            const SizedBox(height: 8),
            Text(
              l10n.offerPyramidResult(
                model.levels,
                percentLabel(model.lastLevelShareBp),
              ),
              key: const Key('pyramid-result'),
            ),
          ],
          const SizedBox(height: 8),
          Text(l10n.offerPyramidBait),
        ],
      ),
    );
  }
}
