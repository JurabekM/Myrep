// Pigeon kontrakti: majburiyat eslatmalari (Kotlin WorkManager +
// bildirishnoma). Generatsiya: `dart run pigeon --input pigeons/reminder_api.dart`
import 'package:pigeon/pigeon.dart';

@ConfigurePigeon(
  PigeonOptions(
    dartOut: 'lib/core/notifications/reminder_api.pigeon.dart',
    dartOptions: DartOptions(),
    kotlinOut:
        'android/app/src/main/kotlin/uz/barakadaftari/app/native/ReminderApi.g.kt',
    kotlinOptions: KotlinOptions(
      package: 'uz.barakadaftari.app.native',
      errorClassName: 'ReminderFlutterError',
    ),
    dartPackageName: 'baraka_daftari',
  ),
)
/// Bitta majburiyat uchun oylik eslatma: to'lov kunidan 1 kun oldin 09:00
/// (Asia/Tashkent). Matnlar Dart'da (ARB) tayyorlanadi; summa yozilmaydi.
class ObligationReminder {
  ObligationReminder({
    required this.id,
    required this.dayOfMonth,
    required this.title,
    required this.body,
  });

  /// Majburiyat ID (UUIDv7).
  final String id;

  /// 1–31; qisqa oyda oyning oxirgi kuni.
  final int dayOfMonth;
  final String title;
  final String body;
}

/// «Juma shirinligi» (SPEC 2B.4): har hafta [weekday] kuni 09:00
/// (Asia/Tashkent). Matnlarda summa yo'q.
class TreatReminder {
  TreatReminder({
    required this.id,
    required this.weekday,
    required this.title,
    required this.body,
  });

  final String id;

  /// 1 = dushanba … 7 = yakshanba (ISO).
  final int weekday;
  final String title;
  final String body;
}

/// Daromad eslatmasi davri (onboarding'dagi daromad turidan, Vazifa 15).
enum IncomeReminderKind {
  /// Kunlik naqd — har kuni 20:00.
  daily,

  /// Buyurtma bo'yicha — har shanba 20:00.
  weekly,

  /// Oylik maosh — maosh kuni 10:00.
  monthly,
}

@HostApi()
abstract class ReminderApi {
  /// Barcha eslatmalarni berilgan ro'yxat bilan almashtiradi (idempotent):
  /// ro'yxatda yo'qlari bekor qilinadi. Ilova ishga tushganda va har
  /// o'zgarishda chaqiriladi.
  void sync(List<ObligationReminder> reminders, String channelName);

  /// Har juma 09:00 (Asia/Tashkent) — «Yangi bob / haftalik yakun»
  /// bildirishnomasi. Idempotent; WorkManager qurilma qayta yoqilgandan keyin
  /// ham saqlaydi. Matnlar Dart'da (ARB).
  void scheduleWeekly(String title, String body, String channelName);

  /// Shirinlik eslatmalarini berilgan ro'yxat bilan almashtiradi
  /// (idempotent; ro'yxatda yo'qlari bekor qilinadi).
  void syncTreats(List<TreatReminder> treats, String channelName);

  /// Daromadni yozish eslatmasi (bitta, idempotent — avvalgisini almashtiradi).
  /// [dayOfMonth] — faqat oylik uchun (maosh kuni).
  void scheduleIncomeReminder(
    IncomeReminderKind kind,
    int dayOfMonth,
    String title,
    String body,
    String channelName,
  );

  /// Kelishuv yangilash eslatmasi (SPEC 6-qonun, Vazifa 14A): [year]-[month]-
  /// [day] kuni 09:00 (Asia/Tashkent). Kelishuv ID bo'yicha idempotent;
  /// WorkManager qurilma qayta yoqilgandan keyin ham saqlaydi.
  void scheduleAgreementRenewal(
    String id,
    int year,
    int month,
    int day,
    String title,
    String body,
    String channelName,
  );

  /// Kelishuv eslatmasini bekor qiladi (yopilgan yoki muddati o'tgan).
  void cancelAgreementRenewal(String id);

  bool areNotificationsEnabled();

  /// Android 13+ da ruxsat so'raydi (natija kutilmaydi).
  void requestNotificationPermission();
}
