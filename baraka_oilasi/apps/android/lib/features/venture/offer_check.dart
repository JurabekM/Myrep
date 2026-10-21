import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

const offerQuestions = [
  'guaranteed',
  'lossShared',
  'realActivity',
  'recruitment',
  'urgency',
  'written',
  'licensed',
  'inspection',
  'exitEasy',
];
const offerReplies = ['YES', 'NO', 'UNKNOWN'];

/// Bayroq yoki xulosa rangi: yashil — aksent, sariq — ogohlantirish, qizil — xavf.
Color verdictColor(BuildContext context, String level) => switch (level) {
  'RED' => context.palette.danger,
  'YELLOW' => context.palette.warn,
  _ => context.palette.accentText,
};

void openOfferCheck(BuildContext context) => showSheet<void>(context, (_) => const OfferCheckSheet());

/// «Kafolatlangan foyda» detektori (uy/SPEC 2E.5): tavakkalsiz, kafolatlangan foyda va'da qilinsa —
/// u yerda yo ribo, yo firibgarlik bor. Qaror jadvali yadroda; hech narsa saqlanmaydi.
class OfferCheckSheet extends ConsumerStatefulWidget {
  const OfferCheckSheet({super.key});

  @override
  ConsumerState<OfferCheckSheet> createState() => _OfferCheckSheetState();
}

class _OfferCheckSheetState extends ConsumerState<OfferCheckSheet> with ActionState {
  final _a = <String, String>{};
  OfferCheckDto? _r;

  Future<void> _check() async {
    String v(String k) => _a[k] ?? '';
    final r = await act(
      () => ref
          .read(coreProvider)
          .checkOffer(
            input: OfferAnswersInput(
              guaranteed: v('guaranteed'),
              lossShared: v('lossShared'),
              realActivity: v('realActivity'),
              recruitment: v('recruitment'),
              urgency: v('urgency'),
              written: v('written'),
              licensed: v('licensed'),
              inspection: v('inspection'),
              exitEasy: v('exitEasy'),
            ),
          ),
    );
    if (r != null) setState(() => _r = r);
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final complete = offerQuestions.every(_a.containsKey);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            header: true,
            child: Text(context.t('offer.title'), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(height: 8),
          Hint(context.t('offer.intro')),
          for (final q in offerQuestions)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: SegmentedChoice<String>(
                label: context.t('offer.q.$q'),
                options: [for (final v in offerReplies) (v, context.t('offer.reply.$v'))],
                value: _a[q],
                onChanged: (v) => setState(() {
                  _a[q] = v;
                  _r = null;
                }),
              ),
            ),
          ErrorText(error),
          if (r != null) ...[const SizedBox(height: 12), OfferResult(r)],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              FilledButton(onPressed: !complete || busy ? null : _check, child: Text(context.t('offer.check'))),
              TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.close'))),
            ],
          ),
        ],
      ),
    );
  }
}

/// Taklif tekshiruvi natijasi: xulosa, belgilar soni, bayroqlar va maslahat.
class OfferResult extends StatelessWidget {
  const OfferResult(this.r, {super.key});

  final OfferCheckDto r;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Container(
      key: const Key('offer-result'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: verdictColor(context, r.verdict), width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            context.t('offer.verdict.${r.verdict}'),
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: verdictColor(context, r.verdict)),
          ),
          if (r.signs > 0)
            Text(context.t('offer.signs', {'count': r.signs}), style: const TextStyle(fontWeight: FontWeight.w700)),
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
                    TextSpan(text: context.t('offer.flag.${f.code}')),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 6),
          Hint(context.t('offer.advice.${r.verdict}')),
        ],
      ),
    ),
  );
}
