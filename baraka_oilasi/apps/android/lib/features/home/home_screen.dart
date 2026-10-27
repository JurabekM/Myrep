import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/shell_state.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../core/query.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../income/income_sheet.dart';

/// Bosh sahifa: 1-raqam — «O'zingizga to'langan (shu oy)», keyin odat va oy yakuni.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({required this.spaceId, super.key});

  final String spaceId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(query(['summary', spaceId, null], (c) => c.monthlySummary(spaceId: spaceId))).valueOrNull;
    final vault = ref.watch(query(['vault', spaceId], (c) => c.vault(spaceId: spaceId))).valueOrNull;
    final debts = ref.watch(query(['debts', spaceId], (c) => c.debtsOverview(spaceId: spaceId))).valueOrNull;
    final nudges = ref.watch(nudgesQuery(spaceId)).valueOrNull ?? [];
    final reminders =
        ref.watch(query(['reminders', spaceId], (c) => c.agreementReminders(spaceId: spaceId))).valueOrNull ?? [];
    final shell = ref.read(shellProvider.notifier);
    final free = debts?.debtFreeDate;
    return ScreenBody(
      mentorKey: 'mentor.home',
      children: [
        if (nudges.isNotEmpty) Nudges(spaceId: spaceId, items: nudges),
        Kpi(
          key: const Key('kpi-paid-to-self'),
          label: context.t('home.paidToSelf'),
          value: summary?.paidToSelf.formatted ?? '…',
          accent: true,
        ),
        Kpi(
          label: context.t('home.vault'),
          value: vault?.balance.formatted ?? '…',
          hint: vault == null ? null : context.t('home.streak', {'count': vault.streak.currentWeeks}),
        ),
        Kpi(label: context.t('home.monthResult'), value: summary?.monthResult.formatted ?? '…'),
        if (free != null)
          InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => shell.go('debts'),
            child: Kpi(
              key: const Key('kpi-debt-free'),
              label: context.t('home.debtFree'),
              value: showDate(free),
              accent: true,
              hint: [
                context.t('payoff.months', {'count': debts?.debtFreeMonths ?? 0}),
                if (debts?.debtFreeDateWithPlan != null)
                  context.t('home.withPlan', {'date': showDate(debts!.debtFreeDateWithPlan!)}),
              ].join(' · '),
            ),
          ),
        if (reminders.isNotEmpty)
          SectionCard(
            title: context.t('home.reminders'),
            children: [
              for (final r in reminders)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${context.t('home.reminder.${r.agreementType}.${r.kind}')} · ${r.title}'),
                  subtitle: ReminderText(r),
                  onTap: () => r.agreementType == 'PARTNERSHIP'
                      ? shell.go('partnerships', focus: {'id': r.refId, 'tab': 'governance'})
                      : shell.go('agreements'),
                ),
            ],
          ),
        // Pastki tugma (FAB) ostida ham o'qilsin.
        const SizedBox(height: 56),
      ],
    );
  }
}

/// Kelishuv eslatmasi holati: yaqinlashmoqda (sariq) yoki o'tib ketgan (qizil).
class ReminderText extends StatelessWidget {
  const ReminderText(this.r, {super.key});

  final ReminderDto r;

  @override
  Widget build(BuildContext context) => Text(
    context.t('gov.reminder.${r.state}', {'count': r.days, 'date': showDate(r.dueOn)}),
    style: TextStyle(color: r.state == 'UPCOMING' ? context.palette.warn : context.palette.danger),
  );
}

/// Bosh sahifa eslatmalari (Uy, Kasb-kor, Musofir — turlari yadroda tanlanadi).
ProviderListenable<AsyncValue<List<NudgeDto>>> nudgesQuery(String spaceId) =>
    query(['nudges', spaceId], (c) => c.homeNudges(spaceId: spaceId));

/// Yumshoq eslatmalar (U15): daromad ritmi, qarzlarni yozish, oylik zaxira nusxa; 8-tamoyilning juma
/// ritmi (o'qish vaqti, «Ilm zakoti») — tugma shu makonning «O'zimga sarmoya» ekranini ochadi.
class Nudges extends ConsumerWidget {
  const Nudges({required this.spaceId, required this.items, super.key});

  final String spaceId;
  final List<NudgeDto> items;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shell = ref.read(shellProvider.notifier);
    final settings = ref.watch(query(['settings'], (c) => c.settings())).valueOrNull;
    void action(String kind) => switch (kind) {
      'DEBT_INVENTORY' => shell.go('inventory'),
      'BACKUP' => shell.go('sync'),
      'STUDY_WEEK' || 'TEACH_WEEK' => shell.go('learning'),
      'KK_TEACH_WEEK' => shell.go('kkLearning'),
      'MF_TEACH_WEEK' => shell.go('mfLearning'),
      _ => openIncome(context, spaceId),
    };
    return Semantics(
      container: true,
      label: context.t('nudge.title'),
      child: Column(
        children: [
          for (final n in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Card(
                key: Key('nudge-${n.kind}'),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                  side: BorderSide(color: context.palette.accent.withValues(alpha: 0.6)),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        context.t(
                          n.kind == 'INCOME_QUIET' && n.days == null ? 'nudge.INCOME_NONE' : 'nudge.${n.kind}',
                          {'count': n.days ?? 0},
                        ),
                      ),
                      if (n.members.isNotEmpty) Hint(context.t('nudge.members', {'names': n.members.join(', ')})),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        children: [
                          FilledButton(
                            onPressed: () => action(n.kind),
                            child: Text(context.t('nudge.action.${n.kind}')),
                          ),
                          if (n.kind == 'DEBT_INVENTORY' && settings != null)
                            OutlinedButton(
                              onPressed: () => ref
                                  .read(coreProvider)
                                  .updateSettings(
                                    input: SettingsInput(
                                      locale: settings.deviceLocale,
                                      incomeRhythm: settings.incomeRhythm,
                                      debtsDeclared: false,
                                    ),
                                  ),
                              child: Text(context.t('nudge.dismiss')),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
