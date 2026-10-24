import 'package:baraka_daftari/app/l10n/gen/app_localizations.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/data/renewal_reminders.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/home/presentation/home_screen.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/pump_app.dart';

/// Yillik yangilash eslatmasi (SPEC 6-qonun): `reviewDate` dan 30 kun oldin
/// Kotlin WorkManager'ga yuboriladi. Qurilmada eslatma rejalashtirilmagani
/// topilgan edi — bu test o'sha yo'lni bosh ekran `ref` i bilan sinaydi.
void main() {
  testWidgets('kelishuvning yangilash eslatmasi WorkManager ga yuboriladi', (
    tester,
  ) async {
    final env = await pumpBarakaApp(tester);
    final s = await env.container.read(agreementServiceProvider.future);
    final today = Tashkent.dateOf(env.clock.nowUtc());
    final a = await s.create(
      type: AgreementType.rent,
      title: 'Doʻkon ijarasi',
      parties: const [
        AgreementParty(id: 'p1', name: 'Akmal', isMe: true),
        AgreementParty(id: 'p2', name: 'Bahodir'),
      ],
      effectiveFrom: today,
    );
    final reviewDate = (await s.find(a.meta.id))!.reviewDate!;
    final on = renewalReminderOn(reviewDate);

    final ref = tester.state<ConsumerState>(find.byType(HomeScreen)).ref;
    await syncAgreementRenewals(
      ref,
      lookupAppLocalizations(const Locale('uz')),
    );

    verify(
      () => env.reminders.scheduleAgreementRenewal(
        a.meta.id,
        on.year,
        on.month,
        on.day,
        any(),
        any(),
        any(),
      ),
    ).called(1);
  });
}
