import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/features/household/data/household_providers.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'onboarding_providers.g.dart';

/// Joriy uy xo'jaligi (onboarding holati, daromad turi, oylik kuni).
@riverpod
Future<Household> currentHousehold(Ref ref) async =>
    (await ref.watch(householdServiceProvider.future)).household();

/// Onboarding tugaganmi (router shunga qarab `/onboarding` ga yo'naltiradi).
@Riverpod(keepAlive: true)
Future<bool> onboarded(Ref ref) async =>
    (await (await ref.watch(
      householdServiceProvider.future,
    )).household()).onboardedAt !=
    null;

/// Daromad turiga mos eslatma: kunlik — har kuni 20:00, buyurtma —
/// shanba 20:00, maosh — oylik kuni 10:00 (Kotlin WorkManager, idempotent).
/// Bildirishnomada summa yo'q.
Future<void> syncIncomeReminder(WidgetRef ref, AppLocalizations l10n) async {
  try {
    final h = await (await ref.read(
      householdServiceProvider.future,
    )).household();
    final kind = h.incomeKind;
    if (kind == null) return;
    await ref
        .read(reminderApiProvider)
        .scheduleIncomeReminder(
          switch (kind) {
            IncomeKind.dailyCash => IncomeReminderKind.daily,
            IncomeKind.orders => IncomeReminderKind.weekly,
            IncomeKind.salary => IncomeReminderKind.monthly,
          },
          h.monthStartDay,
          l10n.reminderIncomeTitle,
          switch (kind) {
            IncomeKind.dailyCash => l10n.reminderIncomeDaily,
            IncomeKind.orders => l10n.reminderIncomeWeekly,
            IncomeKind.salary => l10n.reminderIncomeMonthly,
          },
          l10n.reminderIncomeChannel,
        );
  } on Object {
    AppLog.event('income_reminder_failed');
  }
}
