import 'dart:async';

import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/features/agreements/data/renewal_reminders.dart';
import 'package:baraka_daftari/features/audit/data/audit_providers.dart';
import 'package:baraka_daftari/features/audit/domain/ledger_service.dart';
import 'package:baraka_daftari/features/budget/presentation/havas_screen.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_views.dart';
import 'package:baraka_daftari/features/home/presentation/home_slots.dart';
import 'package:baraka_daftari/features/home/presentation/widget_sync.dart';
import 'package:baraka_daftari/features/lock/domain/lock_status.dart';
import 'package:baraka_daftari/features/lock/presentation/app_lock_controller.dart';
import 'package:baraka_daftari/features/obligations/presentation/obligation_views.dart';
import 'package:baraka_daftari/features/onboarding/data/onboarding_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Bosh ekran (SPEC 9): 1-raqam «O'zingizga to'langan», keyin «Kelajagim»
/// balansi, streak, oy yakuni va shu haftaning vazifalari.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    // Vidjetda bosilganlar ilovaga qaytganda (qulf ochiq bo'lsa) yoziladi.
    _lifecycle = AppLifecycleListener(
      onResume: () => unawaited(_drainWidget()),
    );
    // Qulf ochilgach eslatmalar WorkManager bilan sinxronlanadi.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final l10n = context.l10n;
      unawaited(syncObligationReminders(ref, l10n));
      unawaited(syncAgreementRenewals(ref, l10n));
      unawaited(scheduleWeeklyChapterNotification(ref, l10n));
      unawaited(syncTreatReminders(ref, l10n));
      unawaited(syncIncomeReminder(ref, l10n));
      unawaited(_drainWidget());
      final templates = ref.read(expenseTemplatesProvider).valueOrNull;
      if (templates != null) {
        unawaited(pushWidgetTemplates(ref, l10n, context.money, templates));
      }
    });
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  Future<void> _drainWidget() async {
    if (ref.read(appLockControllerProvider) != LockStatus.unlocked) return;
    final messenger = ScaffoldMessenger.of(context);
    final l10n = context.l10n;
    final count = await drainWidgetQueue(ref);
    if (count > 0) {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.widgetRecorded(count))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final kpis = ref.watch(homeKpisProvider);
    // Daromad turiga qarab asosiy tugma (Vazifa 15 onboarding).
    final incomeKind = ref
        .watch(currentHouseholdProvider)
        .valueOrNull
        ?.incomeKind;
    ref
      ..listen(expenseTemplatesProvider, (_, next) {
        final list = next.valueOrNull;
        if (list != null) {
          unawaited(
            pushWidgetTemplates(ref, context.l10n, context.money, list),
          );
        }
      })
      ..listen(appLockControllerProvider, (_, next) {
        if (next == LockStatus.unlocked) unawaited(_drainWidget());
      });
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.homeTitle),
        actions: [
          IconButton(
            key: const Key('nav-settings'),
            tooltip: l10n.sectionSettings,
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => context.push(AppRoutes.settings),
          ),
          const SettingsActions(),
        ],
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          children: [
            Expanded(
              child: FloatingActionButton.extended(
                heroTag: 'income',
                key: const Key('home-add-income'),
                icon: const Icon(Icons.add),
                label: Text(switch (incomeKind) {
                  IncomeKind.dailyCash => l10n.homeAddIncomeDaily,
                  IncomeKind.orders => l10n.homeAddIncomeOrders,
                  IncomeKind.salary => l10n.homeAddIncomeSalary,
                  null => l10n.homeAddIncome,
                }),
                onPressed: () => context.push(AppRoutes.incomeNew),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FloatingActionButton.extended(
                heroTag: 'expense',
                key: const Key('home-add-expense'),
                backgroundColor: Theme.of(
                  context,
                ).colorScheme.surfaceContainerLow,
                icon: const Icon(Icons.remove),
                label: Text(l10n.homeAddExpense),
                onPressed: () => context.push(AppRoutes.expenseNew),
              ),
            ),
          ],
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: RefreshIndicator(
            onRefresh: () async => ref.invalidate(homeKpisProvider),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 112),
              children: [
                switch (kpis) {
                  AsyncData(:final value) => _Kpis(value),
                  AsyncError() => Text(l10n.genericError),
                  _ => const Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                },
                for (final slot
                    in [...ref.watch(homeCardSlotsProvider)]
                      // Override qilingan roʻyxat ham tartibga keltiriladi.
                      ..sort((a, b) => a.order.compareTo(b.order)))
                  Padding(
                    key: Key('home-card-${slot.id}'),
                    padding: const EdgeInsets.only(top: 8),
                    child: Builder(builder: slot.builder),
                  ),
                const SizedBox(height: 16),
                Text(
                  l10n.homeSectionsHeader,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                const _Sections(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Kpis extends StatelessWidget {
  const _Kpis(this.k);

  final HomeKpis k;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final result = k.monthResult;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 1-raqam.
        Card(
          color: scheme.primaryContainer,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Text(
                  l10n.homePaidToSelf,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: scheme.onPrimaryContainer,
                  ),
                ),
                const SizedBox(height: 4),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    context.money(k.paidToSelf),
                    key: const Key('kpi-paid-to-self'),
                    style: theme.textTheme.displaySmall?.copyWith(
                      color: scheme.onPrimaryContainer,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                Text(
                  periodLabel(context, k.period),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: scheme.onPrimaryContainer,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _Tile(
                key: const Key('kpi-vault'),
                label: l10n.homeVaultBalance,
                value: context.money(k.vaultBalance),
                caption: l10n.homeStreak(k.habit.currentStreakWeeks),
                onTap: () => context.push(AppRoutes.vault),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _Tile(
                key: const Key('kpi-month-result'),
                label: l10n.homeMonthResult,
                value: result.isNegative
                    ? '−${context.money(result.abs())}'
                    : '+${context.money(result)}',
                caption: result.isNegative
                    ? l10n.homeMonthResultMinus
                    : l10n.homeMonthResultPlus,
                onTap: () => context.push(AppRoutes.whoseMoney),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.label,
    required this.value,
    required this.caption,
    required this.onTap,
    super.key,
  });

  final String label;
  final String value;
  final String caption;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: theme.textTheme.labelLarge),
              const SizedBox(height: 4),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(value, style: theme.textTheme.titleLarge),
              ),
              const SizedBox(height: 2),
              Text(
                caption,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Sections extends ConsumerWidget {
  const _Sections();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final sections = ref.watch(homeSectionsProvider);
    return Card(
      child: Column(
        children: [
          for (final (index, section) in sections.indexed) ...[
            if (index > 0) const Divider(height: 1),
            ListTile(
              key: Key('nav-${section.route}'),
              leading: Icon(section.icon),
              title: Text(section.label(l10n)),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(section.route),
            ),
          ],
        ],
      ),
    );
  }
}
