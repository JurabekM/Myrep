import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

const _fields = ['material', 'hours', 'hourlyRate', 'travel', 'depreciation', 'reservePercent', 'price', 'advance'];
const _money = {'material', 'hourlyRate', 'travel', 'depreciation', 'price', 'advance'};

/// Buyurtma kalkulyatori (kasbkor/SPEC 3.2): tannarx, narx tannarxdan past bo'lsa — ogohlantirish,
/// avans materialga yetadimi. Hisob yadroda; hech narsa saqlanmaydi.
class KkQuoteScreen extends ConsumerStatefulWidget {
  const KkQuoteScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<KkQuoteScreen> createState() => _KkQuoteScreenState();
}

class _KkQuoteScreenState extends ConsumerState<KkQuoteScreen> with ActionState {
  final Map<String, TextEditingController> _c = {for (final k in _fields) k: TextEditingController()};
  KkQuoteDto? _q;

  @override
  void dispose() {
    for (final c in _c.values) {
      c.dispose();
    }
    super.dispose();
  }

  String? _v(String k) {
    final t = _c[k]!.text.trim();
    return t.isEmpty ? null : t;
  }

  Future<void> _calculate() async {
    final r = await act(
      () => ref
          .read(coreProvider)
          .kkOrderQuote(
            spaceId: widget.spaceId,
            input: KkQuoteInput(
              material: _v('material'),
              hours: _v('hours'),
              hourlyRate: _v('hourlyRate'),
              travel: _v('travel'),
              depreciation: _v('depreciation'),
              reservePercent: _v('reservePercent'),
              price: _v('price'),
              advance: _v('advance'),
            ),
          ),
    );
    if (r != null) setState(() => _q = r);
  }

  @override
  Widget build(BuildContext context) {
    final q = _q;
    final p = context.palette;
    return ScreenBody(
      mentorKey: 'mentor.kkQuote',
      children: [
        Hint(context.t('kk.q.intro')),
        SectionCard(
          title: context.t('kk.q.title'),
          children: [
            for (final k in _fields)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _money.contains(k)
                    ? AmountField(label: context.t('kk.q.$k'), controller: _c[k]!)
                    : Field(
                        label: context.t('kk.q.$k'),
                        controller: _c[k]!,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      ),
              ),
            ErrorText(error),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton(onPressed: busy ? null : _calculate, child: Text(context.t('kk.q.calculate'))),
            ),
          ],
        ),
        if (q != null)
          Semantics(
            liveRegion: true,
            child: SectionCard(
              title: context.t('kk.q.result'),
              children: [
                ValueRow(context.t('kk.q.labor'), q.labor.formatted),
                ValueRow(context.t('kk.q.subtotal'), q.subtotal.formatted),
                ValueRow(context.t('kk.q.reserve'), q.reserve.formatted),
                Container(
                  decoration: BoxDecoration(
                    border: Border(top: BorderSide(color: p.line)),
                  ),
                  child: ValueRow(
                    context.t('kk.q.cost'),
                    q.cost.formatted,
                    strong: true,
                    key: const Key('kk-quote-cost'),
                  ),
                ),
                if (q.margin != null && q.laborPaid != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    context.t(
                      (q.belowCost ?? false)
                          ? (q.effectiveHourlyRate != null ? 'kk.q.belowCost' : 'kk.q.belowCostNoHours')
                          : (q.effectiveHourlyRate != null ? 'kk.q.aboveCost' : 'kk.q.aboveCostNoHours'),
                      {
                        'margin': q.margin!.formatted,
                        'labor': q.laborPaid!.formatted,
                        'hourly': q.effectiveHourlyRate?.formatted ?? '',
                      },
                    ),
                    key: const Key('kk-quote-verdict'),
                    style: TextStyle(color: (q.belowCost ?? false) ? p.warn : null),
                  ),
                ],
                if (q.materialShortfall != null && q.advanceAfterMaterial != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    q.materialShortfall!.minor != '0'
                        ? context.t('kk.q.advanceShort', {'amount': q.materialShortfall!.formatted})
                        : context.t('kk.q.advanceCovers', {'amount': q.advanceAfterMaterial!.formatted}),
                    key: const Key('kk-quote-advance'),
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }
}
