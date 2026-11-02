import 'package:flutter/material.dart';

import '../core/risk.dart';

/// ROSTOR oilasi palitrasi: to'q ko'k fon, firuza urg'u (AETHER-Q/ROSTOR-1 bilan bir xil).
class RColors {
  static const bg = Color(0xFF0B1D33);
  static const surface = Color(0xFF12294A);
  static const surfaceHi = Color(0xFF1A3560);
  static const line = Color(0xFF24426E);
  static const accent = Color(0xFF4FD1C5);
  static const text = Color(0xFFE6EEF8);
  static const textDim = Color(0xFF9DB1CC);

  static Color of(Severity s) => switch (s) {
        Severity.ok => const Color(0xFF48BB78),
        Severity.info => const Color(0xFF63B3ED),
        Severity.low => const Color(0xFF9DB1CC),
        Severity.medium => const Color(0xFFECC94B),
        Severity.high => const Color(0xFFED8936),
        Severity.critical => const Color(0xFFF56565),
      };

  static IconData icon(Severity s) => switch (s) {
        Severity.ok => Icons.verified_user_rounded,
        Severity.info => Icons.info_outline_rounded,
        Severity.low => Icons.remove_circle_outline_rounded,
        Severity.medium => Icons.warning_amber_rounded,
        Severity.high => Icons.gpp_maybe_rounded,
        Severity.critical => Icons.dangerous_rounded,
      };
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: RColors.accent,
    brightness: Brightness.dark,
    surface: RColors.surface,
    primary: RColors.accent,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: RColors.bg,
    appBarTheme: const AppBarTheme(
      backgroundColor: RColors.bg,
      foregroundColor: RColors.text,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: RColors.text),
    ),
    cardTheme: CardThemeData(
      color: RColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: RColors.line)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: RColors.accent,
        foregroundColor: RColors.bg,
        minimumSize: const Size(48, 52),
        textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: RColors.accent,
        side: const BorderSide(color: RColors.accent),
        minimumSize: const Size(48, 48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: RColors.surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: RColors.line)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: RColors.line)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: RColors.accent, width: 1.5)),
      hintStyle: const TextStyle(color: RColors.textDim),
    ),
    textTheme: const TextTheme(
      bodyMedium: TextStyle(color: RColors.text, fontSize: 15, height: 1.4),
      bodySmall: TextStyle(color: RColors.textDim, fontSize: 13, height: 1.35),
      titleMedium: TextStyle(color: RColors.text, fontSize: 16, fontWeight: FontWeight.w600),
    ),
    dividerColor: RColors.line,
  );
}
