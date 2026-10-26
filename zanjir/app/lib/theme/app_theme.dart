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
    surfaceContainerHighest: ZanjirColors.surface,
    onSurfaceVariant: ZanjirColors.inkMuted,
    outline: ZanjirColors.line,
    outlineVariant: ZanjirColors.line,
  );
  const minSize = Size(minTapTarget, minTapTarget);
  return ThemeData(
    colorScheme: scheme,
    fontFamily: 'NotoSans',
    scaffoldBackgroundColor: ZanjirColors.paper,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    appBarTheme: const AppBarTheme(backgroundColor: ZanjirColors.sidebar, foregroundColor: ZanjirColors.ink),
    cardTheme: const CardThemeData(
      color: ZanjirColors.surface,
      margin: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    ),
    dividerColor: ZanjirColors.line,
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      fillColor: ZanjirColors.surface,
      border: OutlineInputBorder(borderSide: BorderSide(color: ZanjirColors.line)),
      enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: ZanjirColors.line)),
      focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: ZanjirColors.accent, width: 2)),
    ),
    filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(minimumSize: minSize)),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(minimumSize: minSize)),
    textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(minimumSize: minSize)),
    iconButtonTheme: IconButtonThemeData(style: IconButton.styleFrom(minimumSize: minSize)),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: ZanjirColors.accent,
      foregroundColor: ZanjirColors.accentInk,
    ),
    snackBarTheme: const SnackBarThemeData(
      backgroundColor: ZanjirColors.surface,
      contentTextStyle: TextStyle(color: ZanjirColors.ink),
    ),
  );
}
