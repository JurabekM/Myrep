import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../venture/offer_check.dart' show offerQuestions, offerReplies, verdictColor;

const _kinds = ['LEND', 'PARTNERSHIP', 'INVEST', 'PURCHASE', 'OTHER'];
const _choices = ['WAIT', 'PROCEED', 'DECLINE'];

/// Musofirga xos bayroqlar (qolganlari — U12 «Taklifni tekshirish» matnlari `offer.flag.*`).
const _mfFlags = {
  'FRESH_RETURN_APPROACH',
  'UPFRONT_BEFORE_DOCUMENTS',
  'UPFRONT_UNKNOWN',
  'ABROAD_JOB_FEE',
  'NO_REPAYMENT_DATE',
  'REPAYMENT_DATE_UNKNOWN',
  'NOT_DISCUSSED',
  'COOLING_PERIOD',
  'COOLING_BIG_DECISION',
  'LARGE_SHARE',
  'FORTRESS_WALL',
};

/// Katta qaror oldidan tekshiruv — to'liq ekran sahifa.
Future<void> openDecisionCheck(BuildContext context, String spaceId, String homeCurrency) => pushScreen(
  context,
  context.t('mf.decision.title'),
  (_) => DecisionScreen(spaceId: spaceId, homeCurrency: homeCurrency),
);

/// Katta qaror oldidan tekshiruv (musofir/SPEC 6.3): kengaytirilgan taklif detektori va sovutish
/// qoidasi. Natija va bayroqlar — yadrodan; qaror taqiqlanmaydi, musofir o'zi tanlaydi.
class DecisionScreen extends ConsumerStatefulWidget {
  const DecisionScreen({required this.spaceId, required this.homeCurrency, super.key});

  final String spaceId;
  final String homeCurrency;

  @override
  ConsumerState<DecisionScreen> createState() => _DecisionScreenState();
}

class _DecisionScreenState extends ConsumerState<DecisionScreen> with ActionState {
  String _kind = 'LEND';
  final _title = TextEditingController();
  final _amount = TextEditingController();
  final _promised = TextEditingController();
  final _note = TextEditingController();
  final _a = <String, String>{};
  MfDecisionCheckDto? _r;

  @override
  void dispose() {
    for (final c in [_title, _amount, _promised, _note]) {
      c.dispose();
    }
    super.dispose();
  }

  void _changed() => setState(() {
    _r = null;
    error = null;
  });

  MfDecisionInput _input(List<String> asked, String? choice) => MfDecisionInput(
    kind: _kind,
    title: _title.text,
    amount: _amount.text,
    answers: [
      for (final q in asked)
        if (_a[q] != null) MfAnswerInput(key: q, reply: _a[q]!),
    ],
    choice: choice,
    note: _note.text.trim().isEmpty ? null : _note.text.trim(),
    promisedPercent: _promised.text.trim().isEmpty ? null : _promised.text.trim(),
  );

  Future<void> _check(List<String> asked) async {
    final r = await act(
      () => ref.read(coreProvider).mfCheckDecision(spaceId: widget.spaceId, input: _input(asked, null)),
    );
    if (r != null) setState(() => _r = r);
  }

  Future<void> _record(List<String> asked, String choice) async {
    final r = await act(
      () => ref.read(coreProvider).mfRecordDecision(spaceId: widget.spaceId, input: _input(asked, choice)),
    );
    if (r != null && mounted) Navigator.of(context).pop();
  }

  String _flagText(MfDecisionCheckDto r, String code) =>
      context.t(_mfFlags.contains(code) ? 'mf.flag.$code' : 'offer.flag.$code', {
        'percent': r.sharePercent ?? '',
        'date': r.endsOn == null ? '' : showDate(r.endsOn!),
        'days': r.daysLeft,
        'free': r.free?.formatted ?? '',
      });

  @override
  Widget build(BuildContext context) {
    final kind = _kind;
    final questions = ref.watch(query(['mfQuestions', kind], (c) => c.mfDecisionQuestions(kind: kind)));
    final asked = questions.valueOrNull ?? const <String>[];
    final complete =
        asked.isNotEmpty &&
        asked.every(_a.containsKey) &&
        _title.text.trim().isNotEmpty &&
        _amount.text.trim().isNotEmpty;
    final r = _r;
    return ScreenBody(
      children: [
        Hint(context.t('mf.decision.dialogIntro')),
        Select<String>(
          label: context.t('mf.decision.kind'),
          items: [for (final k in _kinds) (k, context.t('mf.decision.kindName.$k'))],
          value: _kind,
          onChanged: (v) => setState(() {
            _kind = v ?? _kind;
            _r = null;
          }),
        ),
        // Summa — matn sifatida yadroga (AmountField o'zgarishni bildirmaydi — tugma holati uchun Field).
        Field(
          label: context.t('mf.decision.amount', {'currency': widget.homeCurrency}),
          controller: _amount,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          style: const TextStyle(fontSize: 18, fontFeatures: [FontFeature.tabularFigures()]),
          onChanged: (_) => _changed(),
        ),
        Field(
          label: context.t('mf.decision.promised'),
          controller: _promised,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          onChanged: (_) => _changed(),
        ),
        Field(label: context.t('mf.decision.what'), controller: _title, onChanged: (_) => _changed()),
        if (questions.hasError) ErrorText(questions.error),
        for (final q in asked)
          SegmentedChoice<String>(
            label: context.t(offerQuestions.contains(q) ? 'offer.q.$q' : 'mf.q.$q'),
            options: [for (final v in offerReplies) (v, context.t('offer.reply.$v'))],
            value: _a[q],
            onChanged: (v) => setState(() {
              _a[q] = v;
              _r = null;
            }),
          ),
        if (r != null) _result(context, r, asked),
        ErrorText(error),
        Wrap(
          spacing: 8,
          children: [
            if (r == null)
              FilledButton(
                onPressed: !complete || busy ? null : () => _check(asked),
                child: Text(context.t('offer.check')),
              ),
            TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.close'))),
          ],
        ),
      ],
    );
  }

  Widget _result(BuildContext context, MfDecisionCheckDto r, List<String> asked) => Semantics(
    liveRegion: true,
    child: Container(
      key: const Key('mf-decision-result'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: verdictColor(context, r.verdict), width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            context.t('mf.verdict.${r.verdict}'),
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: verdictColor(context, r.verdict)),
          ),
          if (r.signs > 0)
            Text(context.t('offer.signs', {'count': r.signs}), style: const TextStyle(fontWeight: FontWeight.w600)),
          if (r.promisedTimes != null)
            Text(
              context.t('mf.decision.promiseLine', {
                'monthly': _promised.text.trim(),
                'yearly': r.promisedYearlyPercent ?? '',
                'times': r.promisedTimes,
              }),
              key: const Key('mf-decision-promise'),
            ),
          for (final f in r.flags)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: '● ',
                      style: TextStyle(color: verdictColor(context, f.level)),
                    ),
                    TextSpan(text: _flagText(r, f.code)),
                  ],
                ),
              ),
            ),
          if (r.waitUntil != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                context.t('mf.decision.waitUntil', {'date': showDate(r.waitUntil!)}),
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          const SizedBox(height: 6),
          Hint(context.t('mf.decision.advice.${r.verdict}')),
          const SizedBox(height: 8),
          Field(label: context.t('kk.note'), controller: _note),
          const SizedBox(height: 8),
          Semantics(
            container: true,
            label: context.t('mf.decision.choose'),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final c in _choices)
                  if (c == 'WAIT')
                    FilledButton(
                      onPressed: busy ? null : () => _record(asked, c),
                      child: Text(context.t('mf.choice.$c')),
                    )
                  else
                    OutlinedButton(
                      onPressed: busy ? null : () => _record(asked, c),
                      child: Text(context.t('mf.choice.$c')),
                    ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
