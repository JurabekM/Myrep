import 'package:flutter/material.dart';

import 'tokens.dart';

/// Dala sharoiti: tugmalar ≥ 48 dp (prompt 8-bo'lim).
const double minTapTarget = 48;

ThemeData buildDarkTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.dark,
    primary: ZanjirColors.accent,
    onPrimary: ZanjirColors.accentInk,
    secondary: ZanjirColors.accentText,
    onSecondary: ZanjirColors.accentInk,
    error: ZanjirColors.danger,
    onError: ZanjirColors.accentInk,
    surface: ZanjirColors.paper,
    onSurface: ZanjirColors.ink,
    surfaceContainer: ZanjirColors.surface,
    onSurfaceVariant: ZanjirColors.inkMuted,
    outline: ZanjirColors.line,
  );
  return ThemeData(
    colorScheme: scheme,
    scaffoldBackgroundColor: ZanjirColors.paper,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    appBarTheme: const AppBarTheme(
      backgroundColor: ZanjirColors.sidebar,
      foregroundColor: ZanjirColors.ink,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(minTapTarget, minTapTarget),
      ),
    ),
  );
}
