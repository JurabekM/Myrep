import 'package:flutter/material.dart';

/// «Daftar» mavzusining placeholder ranglari: qog'oz foni, siyoh matni.
///
/// Zarur/Kerak/Havas ranglari (SPEC 9) MVP-2 da qo'shiladi.
abstract final class DaftarColors {
  static const paper = Color(0xFFF8F3E6);
  static const paperRaised = Color(0xFFFFFCF4);
  static const ink = Color(0xFF2B2A26);
  static const inkMuted = Color(0xFF6B655A);
  static const rule = Color(0xFFD9CFB8);
  static const accent = Color(0xFF2F6B4F);

  /// Ogohlantirish (qum rang) — qo'rqitmaydigan, iliq.
  static const notice = Color(0xFFF3E6C4);
  static const onNotice = Color(0xFF4A3B17);

  static const nightPaper = Color(0xFF1C1B18);
  static const nightPaperRaised = Color(0xFF26241F);
  static const nightInk = Color(0xFFEDE6D6);
  static const nightInkMuted = Color(0xFFB3AA97);
  static const nightRule = Color(0xFF3D3A33);
  static const nightAccent = Color(0xFF8CC7A8);
  static const nightNotice = Color(0xFF4A3F24);
  static const nightOnNotice = Color(0xFFF3E6C4);
}

/// Ilova shrifti (pubspec `fonts`). O'zbek lotin yozuvining `ʻ` va `ʼ`
/// belgilari uchun majburiy (MVP_PLAN, Vazifa 1).
const appFontFamily = 'NotoSans';

abstract final class AppTheme {
  static ThemeData light() => _build(
    ColorScheme.fromSeed(
      seedColor: DaftarColors.accent,
      primary: DaftarColors.accent,
      surface: DaftarColors.paper,
      surfaceContainerLow: DaftarColors.paperRaised,
      onSurface: DaftarColors.ink,
      onSurfaceVariant: DaftarColors.inkMuted,
      outlineVariant: DaftarColors.rule,
      tertiaryContainer: DaftarColors.notice,
      onTertiaryContainer: DaftarColors.onNotice,
    ),
  );

  static ThemeData dark() => _build(
    ColorScheme.fromSeed(
      seedColor: DaftarColors.accent,
      brightness: Brightness.dark,
      primary: DaftarColors.nightAccent,
      surface: DaftarColors.nightPaper,
      surfaceContainerLow: DaftarColors.nightPaperRaised,
      onSurface: DaftarColors.nightInk,
      onSurfaceVariant: DaftarColors.nightInkMuted,
      outlineVariant: DaftarColors.nightRule,
      tertiaryContainer: DaftarColors.nightNotice,
      onTertiaryContainer: DaftarColors.nightOnNotice,
    ),
  );

  static ThemeData _build(ColorScheme scheme) {
    final base = ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      fontFamily: appFontFamily,
    );
    // O'qilishi oson: kattaroq asosiy matn va keng qator oralig'i.
    final text = base.textTheme.copyWith(
      bodyLarge: base.textTheme.bodyLarge?.copyWith(fontSize: 17, height: 1.5),
      bodyMedium: base.textTheme.bodyMedium?.copyWith(
        fontSize: 15,
        height: 1.45,
      ),
    );
    return base.copyWith(
      scaffoldBackgroundColor: scheme.surface,
      textTheme: text.apply(
        bodyColor: scheme.onSurface,
        displayColor: scheme.onSurface,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: scheme.surfaceContainerLow,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      dividerTheme: DividerThemeData(color: scheme.outlineVariant),
      dialogTheme: DialogThemeData(
        backgroundColor: scheme.surfaceContainerLow,
        surfaceTintColor: Colors.transparent,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surfaceContainerLow,
        surfaceTintColor: Colors.transparent,
      ),
    );
  }
}
