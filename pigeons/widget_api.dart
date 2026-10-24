// Pigeon kontrakti: bosh ekran vidjeti (Jetpack Glance, SPEC 2B.1).
// Generatsiya: `dart run pigeon --input pigeons/widget_api.dart`
import 'package:pigeon/pigeon.dart';

@ConfigurePigeon(
  PigeonOptions(
    dartOut: 'lib/core/widget/widget_api.pigeon.dart',
    dartOptions: DartOptions(),
    kotlinOut:
        'android/app/src/main/kotlin/uz/barakadaftari/app/native/WidgetApi.g.kt',
    kotlinOptions: KotlinOptions(
      package: 'uz.barakadaftari.app.native',
      errorClassName: 'WidgetFlutterError',
    ),
    dartPackageName: 'baraka_daftari',
  ),
)
/// Vidjet tugmasi. Summa Dart'da formatlanadi; vidjet uni faqat ilova
/// qulfdan ochiq paytda ko'rsatadi.
class WidgetTemplate {
  WidgetTemplate({
    required this.id,
    required this.title,
    required this.amountLabel,
  });

  final String id;
  final String title;
  final String amountLabel;
}

/// Vidjet matnlari (ARB'dan).
class WidgetTexts {
  WidgetTexts({required this.title, required this.locked, required this.empty});

  final String title;
  final String locked;
  final String empty;
}

/// Vidjetda bosilgan, hali ilovaga yozilmagan xarajat.
class PendingWidgetExpense {
  PendingWidgetExpense({
    required this.templateId,
    required this.recordedAtMillis,
  });

  final String templateId;

  /// UTC, epoch millisekund.
  final int recordedAtMillis;
}

@HostApi()
abstract class WidgetApi {
  /// Shablonlar va matnlar (shifrlangan holda saqlanadi), vidjet yangilanadi.
  void setTemplates(List<WidgetTemplate> templates, WidgetTexts texts);

  /// Summalar shu vaqtgacha (epoch ms) ko'rinadi; 0 — qulf, darhol
  /// yashiriladi. Vaqt kelganda vidjet o'zi yangilanadi.
  void setVisibleUntil(int epochMillis);

  /// Navbatdagi yozuvlarni oladi va navbatni tozalaydi.
  List<PendingWidgetExpense> takePending();
}
