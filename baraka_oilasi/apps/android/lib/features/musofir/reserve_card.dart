import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

const _actions = ['RESERVE_IN', 'RESERVE_OUT', 'RESERVE_OPENING'];

/// Bajarilish chizig'i — foiz yadro bergan `bp` dan (hisob yo'q, faqat chizish).
class BpProgress extends StatelessWidget {
  const BpProgress({required this.bp, required this.label, super.key});

  final int bp;
  final String label;

  @override
  Widget build(BuildContext context) => Semantics(
    label: label,
    value: '${bp ~/ 100} %',
    child: ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: LinearProgressIndicator(
        value: bp.clamp(0, 10000) / 10000,
        minHeight: 8,
        backgroundColor: context.palette.line,
        color: context.palette.accent,
      ),
    ),
  );
}

Color _tone(BuildContext context, String status) => switch (status) {
  'FULL' => context.palette.accentText,
  'PARTIAL' || 'EMPTY' => context.palette.warn,
  _ => context.palette.inkMuted,
};

/// Qorovul pul (musofir/SPEC 6.4): chet eldagi kutilmagan xarajat uchun alohida pul. Maqsad — oxirgi
/// oylardagi o'rtacha xarajat × N oy; hammasi yadrodan. O'z ulushi avval shu yerga, keyin jamg'armaga.
class ReserveCard extends ConsumerStatefulWidget {
  const ReserveCard({required this.spaceId, required this.d, required this.r, required this.onAction, super.key});

  final String spaceId;
  final MfOverviewDto d;
  final MfReserveDto r;

  /// Yozuv oynasini ochish (`RESERVE_IN` va h.k.).
  final ValueChanged<String> onAction;

  @override
  ConsumerState<ReserveCard> createState() => _ReserveCardState();
}

class _ReserveCardState extends ConsumerState<ReserveCard> with ActionState {
  Future<void> _months(int n) => act(
    () => ref
        .read(coreProvider)
        .mfSetPlan(
          spaceId: widget.spaceId,
          input: MfPlanInput(
            reserveMonths: n,
            startup: widget.d.startup?.startup.plain,
            startupIdeaId: widget.d.startup?.ideaId,
          ),
        ),
  );

  @override
  Widget build(BuildContext context) {
    final r = widget.r;
    final pal = context.palette;
    return SectionCard(
      title: context.t('mf.reserve.title'),
      children: [
        Text(
          r.balance.formatted,
          key: const Key('mf-reserve'),
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w700,
            color: pal.accent,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
        Text(
          context.t('mf.reserve.status.${r.status}', {'gap': r.gap?.formatted ?? '', 'count': r.months}),
          key: const Key('mf-reserve-status'),
          style: TextStyle(color: _tone(context, r.status)),
        ),
        if (r.target != null && r.progressBp != null) ...[
          const SizedBox(height: 8),
          BpProgress(bp: r.progressBp!, label: context.t('mf.reserve.progress')),
          const SizedBox(height: 4),
          Hint(context.t('mf.reserve.progressLine', {'percent': r.progressPercent, 'target': r.target!.formatted})),
        ],
        if (r.avgMonthly != null)
          Hint(context.t('mf.reserve.avg', {'amount': r.avgMonthly!.formatted, 'count': r.monthsUsed})),
        const SizedBox(height: 12),
        Select<int>(
          label: context.t('mf.reserve.months'),
          items: [
            for (final n in [1, 2, 3]) (n, context.t('mf.months', {'count': n})),
          ],
          value: r.months,
          onChanged: busy ? null : (v) => v == null ? null : _months(v),
        ),
        ErrorText(error),
        const SizedBox(height: 8),
        Semantics(
          container: true,
          label: context.t('mf.reserve.actions'),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final a in _actions)
                OutlinedButton(onPressed: () => widget.onAction(a), child: Text(context.t('mf.action.$a'))),
            ],
          ),
        ),
        const SizedBox(height: 6),
        Hint(context.t('mf.reserve.hint')),
      ],
    );
  }
}
