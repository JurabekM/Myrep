import 'package:flutter/foundation.dart';

/// Ilova log siyosati (SPEC 6).
///
/// * Release build'da `debugPrint` o'chiriladi va Flutter xatolari konsolga
///   chiqarilmaydi.
/// * Logga faqat **hodisa kodi** yoziladi. Summa, ism, PIN, kalit yoki
///   boshqa shaxsiy ma'lumot hech qachon loglanmaydi.
abstract final class AppLog {
  static void configureForBuildMode() {
    if (!kReleaseMode) return;
    debugPrint = (String? message, {int? wrapWidth}) {};
    FlutterError.onError = (details) {};
  }

  /// Faqat debug'da, faqat kod: `event('pin_verify_failed')`.
  static void event(String code) {
    if (kReleaseMode) return;
    debugPrint('[baraka] $code');
  }
}
