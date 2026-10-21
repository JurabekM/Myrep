// Pigeon: Kotlin ↔ Dart platforma xizmatlari (BARAKA_OILASI 3.2, 11.1).
// Generatsiya: `dart run pigeon --input pigeons/platform.dart` (`cargo xtask codegen` ichida).
import 'package:pigeon/pigeon.dart';

@ConfigurePigeon(
  PigeonOptions(
    dartOut: 'lib/platform/platform_api.g.dart',
    dartPackageName: 'baraka',
    kotlinOut: 'android/app/src/main/kotlin/uz/baraka/oilasi/PlatformApi.g.kt',
    kotlinOptions: KotlinOptions(package: 'uz.baraka.oilasi'),
  ),
)
/// Platforma siri (7.2): 32 bayt tasodifiy, Keystore'dagi AES-GCM kalit bilan o'ralgan holda
/// ilovaning private storage'ida. Baytlar Rust'ga uzatiladi va u yerda ishlatilgach tozalanadi.
@HostApi()
abstract class PlatformSecretApi {
  /// Mavjud sirni ochadi; yo'q bo'lsa — yaratadi (faqat birinchi sozlashda).
  Uint8List getOrCreatePlatformSecret();

  /// Faqat mavjud sirni ochadi; yo'q yoki buzilgan bo'lsa — xato.
  Uint8List loadPlatformSecret();
}

/// Moliyaviy ekranlar: `FLAG_SECURE` (skrinshot va «so'nggi ilovalar» oynasi qora).
@HostApi()
abstract class SecureWindowApi {
  void setSecure(bool secure);
}
