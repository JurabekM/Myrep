import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Kelishuvlarning yillik yangilash eslatmalarini Kotlin WorkManager bilan
/// sinxronlaydi (SPEC 6-qonun): `reviewDate` dan 30 kun oldin, 09:00. Yopilgan
/// yoki muddati o'tgan kelishuvning eslatmasi bekor qilinadi. Idempotent —
/// har ilova ochilishida va yangilashdan keyin chaqiriladi.
Future<void> syncAgreementRenewals(
  WidgetRef ref,
  AppLocalizations l10n,
) async {
  try {
    final api = ref.read(reminderApiProvider);
    final today = Tashkent.dateOf(ref.read(clockProvider).nowUtc());
    // keepAlive xizmat orqali: autoDispose `agreementsProvider.future` ni
    // tinglovchisiz o'qish natija kelmasdan yopilib, xato berardi (eslatma
    // jim rejalashtirilmasdi — qurilmada topildi).
    final list = await (await ref.read(agreementServiceProvider.future)).list();
    for (final a in list) {
      final r = a.reviewDate;
      final on = r == null ? null : renewalReminderOn(r);
      if (on == null ||
          on.isBefore(today) ||
          a.status == AgreementStatus.closed) {
        await api.cancelAgreementRenewal(a.meta.id);
        continue;
      }
      await api.scheduleAgreementRenewal(
        a.meta.id,
        on.year,
        on.month,
        on.day,
        l10n.acRenewalNotifTitle,
        l10n.acRenewalNotifBody(a.title),
        l10n.acRenewalChannel,
      );
    }
  } on Object {
    AppLog.event('renewal_schedule_failed');
  }
}
