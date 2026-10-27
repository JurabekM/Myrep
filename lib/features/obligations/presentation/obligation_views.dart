import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'obligation_views.g.dart';

@riverpod
Future<List<Obligation>> obligationsList(Ref ref) async =>
    (await ref.watch(obligationServiceProvider.future)).obligations();

@riverpod
Future<List<Debt>> nasiyaList(Ref ref) async =>
    (await ref.watch(obligationServiceProvider.future)).nasiya();

/// Har juma 09:00 — «Yangi bob / haftalik yakun» (idempotent).
Future<void> scheduleWeeklyChapterNotification(
  WidgetRef ref,
  AppLocalizations l10n,
) async {
  try {
    await ref
        .read(reminderApiProvider)
        .scheduleWeekly(
          l10n.weeklyNotificationTitle,
          l10n.weeklyNotificationBody,
          l10n.weeklyChannel,
        );
  } on Object {
    AppLog.event('weekly_schedule_failed');
  }
}

/// Faol majburiyatlar eslatmalarini Kotlin WorkManager bilan sinxronlaydi
/// (ilova ochilganda va har o'zgarishdan keyin). Bildirishnomada summa yo'q.
Future<void> syncObligationReminders(
  WidgetRef ref,
  AppLocalizations l10n,
) async {
  try {
    final service = await ref.read(obligationServiceProvider.future);
    final reminders = [
      for (final o in await service.obligations())
        if (o.isActive)
          ObligationReminder(
            id: o.meta.id,
            dayOfMonth: o.dayOfMonth,
            title: l10n.reminderTitle(o.title),
            body: l10n.reminderBody(o.title),
          ),
    ];
    await ref.read(reminderApiProvider).sync(reminders, l10n.reminderChannel);
  } on Object {
    AppLog.event('reminder_sync_failed');
  }
}
