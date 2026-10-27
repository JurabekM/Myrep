import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/settings_actions.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/features/home/presentation/native_bridge_card.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/onboarding/data/onboarding_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'settings_screen.g.dart';

@riverpod
Future<int> monthStartDay(Ref ref) async => (await (await ref.watch(
  householdServiceProvider.future,
)).household()).monthStartDay;

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final day = ref.watch(monthStartDayProvider).valueOrNull;
    final kind = ref.watch(currentHouseholdProvider).valueOrNull?.incomeKind;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.sectionSettings),
        actions: const [SettingsActions()],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              key: const Key('settings-month-start'),
              title: Text(l10n.settingsMonthStart),
              subtitle: day == null
                  ? null
                  : Text(l10n.settingsMonthStartHint(day)),
              trailing: day == null
                  ? null
                  : DropdownButton<int>(
                      value: day,
                      items: [
                        for (var d = 1; d <= 31; d++)
                          DropdownMenuItem(value: d, child: Text('$d')),
                      ],
                      onChanged: (d) async {
                        if (d == null) return;
                        try {
                          await (await ref.read(
                            householdServiceProvider.future,
                          )).setMonthStartDay(d);
                          ref
                            ..invalidate(monthStartDayProvider)
                            ..invalidate(currentHouseholdProvider);
                          if (context.mounted) {
                            await syncIncomeReminder(ref, l10n);
                          }
                          refreshMoneyViews(ref);
                        } on Object {
                          AppLog.event('month_start_failed');
                        }
                      },
                    ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              key: const Key('settings-income-kind'),
              title: Text(l10n.settingsIncomeKind),
              // Eski (migratsiya qilingan) foydalanuvchida tur hali yo'q —
              // ro'yxat baribir ko'rinadi.
              trailing: DropdownButton<IncomeKind>(
                key: const Key('settings-income-kind-select'),
                value: kind,
                hint: Text(l10n.settingsIncomeKindUnset),
                items: [
                  for (final k in IncomeKind.values)
                    DropdownMenuItem(
                      value: k,
                      child: Text(switch (k) {
                        IncomeKind.dailyCash => l10n.obIncomeDaily,
                        IncomeKind.orders => l10n.obIncomeOrders,
                        IncomeKind.salary => l10n.obIncomeSalary,
                      }),
                    ),
                ],
                onChanged: (k) async {
                  if (k == null) return;
                  try {
                    await (await ref.read(
                      householdServiceProvider.future,
                    )).setIncomeKind(k);
                    ref.invalidate(currentHouseholdProvider);
                    if (context.mounted) {
                      await syncIncomeReminder(ref, l10n);
                    }
                  } on Object {
                    AppLog.event('income_kind_failed');
                  }
                },
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              key: const Key('settings-backup'),
              leading: const Icon(Icons.lock_outline),
              title: Text(l10n.backupTitle),
              subtitle: Text(l10n.settingsBackupHint),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(AppRoutes.backup),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              key: const Key('settings-members'),
              leading: const Icon(Icons.home_outlined),
              title: Text(l10n.sectionMembers),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(AppRoutes.members),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              key: const Key('settings-about'),
              leading: const Icon(Icons.info_outline),
              title: Text(l10n.aboutTitle),
              subtitle: Text(l10n.settingsAboutHint),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(AppRoutes.about),
            ),
          ),
          const SizedBox(height: 8),
          const NativeBridgeCard(),
        ],
      ),
    );
  }
}
