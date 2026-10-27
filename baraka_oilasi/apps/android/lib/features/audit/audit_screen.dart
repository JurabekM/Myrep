import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

/// Oylik audit: daromad → majburiyatlar → xarajatlar → izohsiz qolgan summa (ayblovsiz).
class AuditScreen extends ConsumerStatefulWidget {
  const AuditScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  ConsumerState<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends ConsumerState<AuditScreen> {
  final _delta = TextEditingController();

  /// Har harfda yangi so'rov: javob kelguncha oldingi natija ko'rinib turadi.
  MonthlySummaryDto? _last;

  @override
  void dispose() {
    _delta.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final id = widget.spaceId;
    final applied = _delta.text.trim().isEmpty ? null : _delta.text;
    final s = ref.watch(query(['summary', id, applied], (c) => c.monthlySummary(spaceId: id, balanceDelta: applied)));
    final d = _last = s.valueOrNull ?? _last;
    return ScreenBody(
      mentorKey: 'mentor.audit',
      children: [
        if (d != null) Hint('${showDate(d.periodStart)} — ${showDate(d.periodEnd)}'),
        if (d != null)
          SectionCard(
            children: [
              ValueRow(context.t('audit.income'), d.income.formatted),
              ValueRow(context.t('audit.obligations'), d.obligationsPaid.formatted),
              ValueRow(context.t('audit.expenses'), d.expenses.formatted),
              ValueRow(context.t('audit.vaultNet'), d.vaultNet.formatted),
              ValueRow(context.t('audit.balanceDelta'), d.balanceDelta.formatted),
              // «O'zimga sarmoya: X — daromadning Y %» (uy/SPEC 2G.3); foiz yadrodan.
              ValueRow(
                context.t('audit.selfInvestment'),
                d.selfInvestment.sharePercent == null
                    ? d.selfInvestment.total.formatted
                    : context.t('learn.selfInvestment.line', {
                        'total': d.selfInvestment.total.formatted,
                        'percent': d.selfInvestment.sharePercent,
                      }),
              ),
            ],
          ),
        AmountField(label: context.t('audit.balanceDelta'), controller: _delta),
        if (s.hasError) ErrorText(s.error),
        if (d != null)
          Kpi(
            key: const Key('gap'),
            label: context.t('audit.gap'),
            value: d.unexplainedGap.formatted,
            hint: context.t('audit.gapHint'),
          ),
      ],
    );
  }

  @override
  void initState() {
    super.initState();
    _delta.addListener(() => setState(() {}));
  }
}
