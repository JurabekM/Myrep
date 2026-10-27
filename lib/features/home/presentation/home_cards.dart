import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability_service.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/budget/data/budget_providers.dart';
import 'package:baraka_daftari/features/budget/domain/budget_math.dart';
import 'package:baraka_daftari/features/budget/presentation/rescue_screen.dart';
import 'package:baraka_daftari/features/content/data/content_providers.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/presentation/content_widgets.dart';
import 'package:baraka_daftari/features/expenses/data/expense_providers.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/domain/expense_service.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Oy auditi eslatmasi (bosh ekran sloti).
class AuditCard extends ConsumerWidget {
  const AuditCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final k = ref.watch(homeKpisProvider).valueOrNull;
    if (k == null) return const SizedBox.shrink();
    final l10n = context.l10n;
    return Card(
      child: ListTile(
        key: const Key('home-audit'),
        leading: const Icon(Icons.fact_check_outlined),
        title: Text(
          k.auditDone
              ? l10n.homeAuditDone(periodLabel(context, k.auditPeriod))
              : l10n.homeAuditDue(periodLabel(context, k.auditPeriod)),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push(AppRoutes.audit),
        selected: !k.auditDone,
      ),
    );
  }
}

/// Shu haftaning vazifalari (bosh ekran sloti).
class WeeklyTasksSlot extends StatelessWidget {
  const WeeklyTasksSlot({super.key});

  @override
  Widget build(BuildContext context) => WeeklyTasksCard(
    key: const Key('home-weekly-tasks'),
    onOpenChapter: (id) => context.push(AppRoutes.chapter(id)),
  );
}

/// Tez yozish (SPEC 2B.1): shablonlar bir bosishda, «oxirgisini
/// takrorlash». Bekor qilish mumkin.
class QuickExpenseCard extends ConsumerWidget {
  const QuickExpenseCard({super.key});

  Future<void> _record(
    BuildContext context,
    WidgetRef ref,
    Future<Expense> Function(ExpenseService s) action,
    String Function(Expense e) message,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    try {
      final service = await ref.read(expenseServiceProvider.future);
      final e = await action(service);
      refreshMoneyViews(ref);
      await recordTaskEvent(ref, TaskTrigger.expenseRecorded);
      messenger.showSnackBar(
        SnackBar(
          content: Text(message(e)),
          action: SnackBarAction(
            key: const Key('quick-undo'),
            label: l10n.undo,
            onPressed: () async {
              await service.delete(e.meta.id);
              refreshMoneyViews(ref);
            },
          ),
        ),
      );
    } on Object {
      AppLog.event('quick_expense_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final templates =
        ref.watch(expenseTemplatesProvider).valueOrNull ?? const [];
    final latest = ref.watch(latestExpenseProvider).valueOrNull;
    if (templates.isEmpty && latest == null) return const SizedBox.shrink();
    final l10n = context.l10n;
    final money = context.money;
    return Card(
      key: const Key('home-quick'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.quickTitle,
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final t in templates)
                  ActionChip(
                    key: Key('quick-${t.meta.id}'),
                    avatar: const Icon(Icons.bolt, size: 18),
                    label: Text('${t.title} · ${money(t.amount)}'),
                    onPressed: () => _record(
                      context,
                      ref,
                      (s) => s.recordTemplate(t),
                      (e) => l10n.templateRecorded(t.title, money(e.amount)),
                    ),
                  ),
                if (latest != null)
                  ActionChip(
                    key: const Key('quick-repeat'),
                    avatar: const Icon(Icons.replay, size: 18),
                    label: Text(l10n.repeatLast),
                    onPressed: () => _record(
                      context,
                      ref,
                      (s) => s.repeatLast(),
                      (e) => l10n.repeatLastDone(money(e.amount)),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Havas holati (neytral rang). Chegara ham, sarf ham bo'lmasa ko'rinmaydi.
class HavasHomeCard extends ConsumerWidget {
  const HavasHomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(havasOverviewProvider).valueOrNull;
    if (o == null ||
        (o.active == null && o.pending == null && o.spent.isZero)) {
      return const SizedBox.shrink();
    }
    final l10n = context.l10n;
    final money = context.money;
    final usage = o.usage;
    return Card(
      child: ListTile(
        key: const Key('home-havas'),
        leading: const Icon(Icons.local_cafe_outlined),
        title: Text(
          usage == null
              ? l10n.havasSpent(money(o.spent))
              : l10n.havasOfLimit(money(usage.spent), money(usage.limit)),
        ),
        subtitle: switch ((usage, o.pending)) {
          (final u?, _) => Text(switch (u.level) {
            LimitLevel.ok => l10n.havasOk(money(u.remaining)),
            LimitLevel.near => l10n.havasNear(percentLabel(u.basisPoints)),
            LimitLevel.over => l10n.havasOver(money(u.remaining.abs())),
          }),
          (null, final p?) => Text(l10n.havasPending(money(p.limit.amount))),
          _ => Text(l10n.havasNoLimit),
        },
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push(AppRoutes.havas),
      ),
    );
  }
}

/// «Bu hafta qutqarildi» (SPEC 2B.7) — 2-qonunning asosiy raqami va bir
/// bosishda «Kelajagim»ga o'tkazish.
class RescueHomeCard extends ConsumerWidget {
  const RescueHomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(rescueOverviewProvider).valueOrNull;
    if (o == null) return const SizedBox.shrink();
    final l10n = context.l10n;
    final money = context.money;
    return Card(
      key: const Key('home-rescue'),
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.shield_outlined),
            title: Text('${l10n.rescueThisWeek}: ${money(o.week.total)}'),
            subtitle: Text(l10n.rescueQuestion),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push(AppRoutes.rescue),
          ),
          if (o.week.available.isPositive)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  key: const Key('home-rescue-transfer'),
                  onPressed: () => transferRescue(context, ref),
                  child: Text(l10n.rescueTransfer(money(o.week.available))),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// «Yaqinlashayotgan koʻrik / yangilash» (SPEC 2F.5, 6-qonun): 30 kun ichida
/// koʻrik yoki yillik yangilash bo'lsa, yoki ochiq nizo bo'lsa — kelishuvlar
/// markaziga yo'naltiradi.
class AccountabilityHomeCard extends ConsumerWidget {
  const AccountabilityHomeCard({super.key});

  static const _soonDays = 30;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rows = ref.watch(agreementCenterProvider).valueOrNull;
    if (rows == null) return const SizedBox.shrink();
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    final due = [
      for (final r in rows)
        if (_isDueSoon(r, today)) r,
    ];
    final disputes = [for (final r in rows) ...r.openDisputes];
    if (due.isEmpty && disputes.isEmpty) return const SizedBox.shrink();
    final l10n = context.l10n;
    return Card(
      child: ListTile(
        key: const Key('home-accountability'),
        leading: const Icon(Icons.event_note_outlined),
        title: Text(l10n.acHomeTitle),
        subtitle: Text(
          [
            if (due.isNotEmpty) l10n.acHomeBody(due.length),
            if (disputes.isNotEmpty) l10n.acHomeDisputes(disputes.length),
          ].join('\n'),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push(AppRoutes.agreements),
      ),
    );
  }

  static bool _isDueSoon(AccountabilityView r, LocalDate today) {
    final a = r.agreement;
    if (a.status == AgreementStatus.closed) return false;
    if (r.review.isOpen) return true;
    if (!r.review.dueOn.isAfter(today.plusDays(_soonDays))) return true;
    final reviewDate = a.reviewDate;
    return reviewDate != null && renewalDue(reviewDate, today);
  }
}
