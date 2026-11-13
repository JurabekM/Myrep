import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';
import 'plan_status_chip.dart';

/// Ajratish rejasi (ADR-0013): tasdiqlash (LEAD/ADMIN), qadamlar checklist'i (faqat ketma-ket, har biri qo'lda
/// tasdiq bilan), yakunlash, bekor qilish. Graf o'zgarsa — STALE va hech qanday amal yo'q.
/// "Kuchlanish yo'qligini tekshirish" — ikki alohida tasdiq; hech narsa oldindan belgilanmaydi (CLAUDE.md, 2-qoida).
class PlanScreen extends ConsumerWidget {
  const PlanScreen({super.key, required this.planId});
  final String planId;

  Future<void> _run(BuildContext context, WidgetRef ref, Future<Object?> Function(Repositories r) action) async {
    final l10n = AppLocalizations.of(context);
    try {
      await action(await ref.read(repositoriesProvider.future));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
    ref.invalidate(planProvider(planId));
  }

  Future<bool> _confirm(BuildContext context, String title, String body, String action, Key key) async =>
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(title),
          content: Text(body),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(AppLocalizations.of(ctx).cancel)),
            FilledButton(key: key, onPressed: () => Navigator.pop(ctx, true), child: Text(action)),
          ],
        ),
      ) ??
      false;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final role = ref.watch(profileProvider).value?.role ?? 'VIEWER';
    final field = role != 'VIEWER';
    final editor = SettingsRepository.editorRoles.contains(role);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.isolationPlan)),
      body: AsyncView(
        value: ref.watch(planProvider(planId)),
        builder: (view) {
          if (view == null) return Center(child: Text(l10n.codeNotFound));
          final plan = view.plan;
          String labelOf(String id) => view.labels[id] ?? id;
          final next = nextStepOrder(view.steps, view.done.keys.toSet());
          final approved = plan.status == 'APPROVED';
          return ListView(
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              ListTile(
                title: Text(l10n.planZone(plan.targetNodeIds.map((id) => labelOf('$id')).join(', '))),
                trailing: PlanStatusChip(plan.status),
              ),
              if (plan.status == 'STALE')
                Container(
                  key: const Key('plan.stale'),
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    border: Border.all(color: ZanjirColors.danger),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(l10n.planStaleBanner, style: const TextStyle(color: ZanjirColors.danger)),
                ),
              if (view.warnings.isNotEmpty) ...[
                ListTile(title: Text(l10n.warnings, style: Theme.of(context).textTheme.titleMedium)),
                for (final w in view.warnings)
                  ListTile(
                    leading: const Icon(Icons.warning_amber, color: ZanjirColors.warn),
                    title: Text(l10n.warningText(w, labelOf)),
                  ),
              ],
              ListTile(title: Text(l10n.steps, style: Theme.of(context).textTheme.titleMedium)),
              for (final s in view.steps)
                _StepTile(
                  step: s,
                  title: l10n.stepText(s, labelOf),
                  record: view.done[s.order],
                  userName: view.done[s.order] == null ? null : view.users[view.done[s.order]!.actorId],
                  actionable: approved && field && s.order == next,
                  onMark: () async {
                    final c = await showDialog<StepConfirmation>(
                      context: context,
                      builder: (_) => StepConfirmDialog(step: s, title: l10n.stepText(s, labelOf)),
                    );
                    if (c != null && context.mounted) {
                      await _run(context, ref, (r) => r.isolationPlans.completeStep(planId, s.order, c));
                    }
                  },
                ),
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (plan.status == 'DRAFT' && editor)
                      FilledButton(
                        key: const Key('plan.approve'),
                        onPressed: () async {
                          final ok = await _confirm(
                            context,
                            l10n.approvePlan,
                            l10n.approvePlanConfirm,
                            l10n.approvePlan,
                            const Key('plan.confirmApprove'),
                          );
                          if (ok && context.mounted) await _run(context, ref, (r) => r.isolationPlans.approve(planId));
                        },
                        child: Text(l10n.approvePlan),
                      ),
                    if (approved && field && next == null)
                      FilledButton(
                        key: const Key('plan.execute'),
                        onPressed: () async {
                          final ok = await _confirm(
                            context,
                            l10n.executePlan,
                            l10n.executePlanConfirm,
                            l10n.executePlan,
                            const Key('plan.confirmExecute'),
                          );
                          if (ok && context.mounted) await _run(context, ref, (r) => r.isolationPlans.execute(planId));
                        },
                        child: Text(l10n.executePlan),
                      ),
                    if ((plan.status == 'DRAFT' || approved) && field)
                      TextButton(
                        key: const Key('plan.cancel'),
                        onPressed: () async {
                          final ok = await _confirm(
                            context,
                            l10n.cancelPlan,
                            l10n.cancelPlanConfirm,
                            l10n.cancelPlan,
                            const Key('plan.confirmCancel'),
                          );
                          if (ok && context.mounted) await _run(context, ref, (r) => r.isolationPlans.cancel(planId));
                        },
                        child: Text(l10n.cancelPlan, style: const TextStyle(color: ZanjirColors.danger)),
                      ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}

class _StepTile extends StatelessWidget {
  const _StepTile({
    required this.step,
    required this.title,
    required this.record,
    required this.userName,
    required this.actionable,
    required this.onMark,
  });
  final PlanStep step;
  final String title;
  final StepRecord? record;
  final String? userName;
  final bool actionable;
  final VoidCallback onMark;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final verify = step.kind == StepKind.verifyNoVoltage;
    final done = record != null;
    return ListTile(
      key: Key('step.${step.order}'),
      leading: CircleAvatar(
        backgroundColor: done ? ZanjirColors.success : (verify ? ZanjirColors.accent : ZanjirColors.surface),
        foregroundColor: done || verify ? ZanjirColors.accentInk : ZanjirColors.ink,
        child: done ? const Icon(Icons.check) : Text('${step.order}'),
      ),
      title: Text(title),
      subtitle: Text(
        [
          if (verify) l10n.mandatory,
          if (record case final r?)
            l10n.stepDoneBy(userName ?? r.actorId, r.at.replaceFirst('T', ' ').substring(0, 16)),
        ].join('\n'),
      ),
      isThreeLine: verify && done,
      trailing: actionable
          ? FilledButton.tonal(key: Key('step.${step.order}.mark'), onPressed: onMark, child: Text(l10n.markStep))
          : null,
    );
  }
}

/// Qadam tasdig'i. Hamma belgilar bo'sh boshlanadi; tugma faqat barcha kerakli bandlar belgilangach faol.
class StepConfirmDialog extends StatefulWidget {
  const StepConfirmDialog({super.key, required this.step, required this.title});
  final PlanStep step;
  final String title;

  @override
  State<StepConfirmDialog> createState() => _StepConfirmDialogState();
}

class _StepConfirmDialogState extends State<StepConfirmDialog> {
  var _done = false;
  var _indicator = false;
  var _noVoltage = false;

  bool get _verify => widget.step.kind == StepKind.verifyNoVoltage;
  bool get _complete => _verify ? _indicator && _noVoltage : _done;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.stepConfirmTitle(widget.step.order)),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.title),
            const SizedBox(height: 8),
            if (_verify) ...[
              Text(l10n.verifyStepHint, style: const TextStyle(color: ZanjirColors.warn)),
              CheckboxListTile(
                key: const Key('confirm.indicator'),
                value: _indicator,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text(l10n.confirmIndicatorTested),
                onChanged: (v) => setState(() => _indicator = v ?? false),
              ),
              CheckboxListTile(
                key: const Key('confirm.noVoltage'),
                value: _noVoltage,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text(l10n.confirmNoVoltage),
                onChanged: (v) => setState(() => _noVoltage = v ?? false),
              ),
            ] else
              CheckboxListTile(
                key: const Key('confirm.done'),
                value: _done,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text(l10n.confirmStepDone),
                onChanged: (v) => setState(() => _done = v ?? false),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(
          key: const Key('confirm.submit'),
          onPressed: _complete
              ? () => Navigator.pop(
                  context,
                  StepConfirmation(
                    done: true,
                    indicatorTestedOnLive: _verify && _indicator,
                    noVoltageConfirmed: _verify && _noVoltage,
                  ),
                )
              : null,
          child: Text(l10n.markStep),
        ),
      ],
    );
  }
}
