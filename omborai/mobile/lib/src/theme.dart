import 'package:flutter/material.dart';

/// Tungi (dark) mavzu: desktop bilan bir xil ranglar (desktop/ui/theme.py). Yorug' rejim yo'q.
/// Ranglar bitta joyda; Claude Code tungi rejimiga yaqin: qora-kulrang fon, bitta teal aksent.
const kBg = Color(0xFF111315);
const kSurface = Color(0xFF1A1D21);
const kSurface2 = Color(0xFF23272D);
const kBorder = Color(0xFF2F353D);
const kText = Color(0xFFE6E8EB);
const kMuted = Color(0xFF9AA3AD);
const kAccent = Color(0xFF4FD1C5);
const kOnAccent = Color(0xFF0B1214);
const kDanger = Color(0xFFF87171);
const kSuccess = Color(0xFF34D399);

ThemeData appTheme() {
  final scheme = const ColorScheme.dark(
    primary: kAccent,
    onPrimary: kOnAccent,
    secondary: kAccent,
    onSecondary: kOnAccent,
    surface: kSurface,
    onSurface: kText,
    surfaceContainerHighest: kSurface2,
    outline: kBorder,
    error: kDanger,
    onError: kOnAccent,
  );
  final radius = BorderRadius.circular(12);
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: kBg,
    canvasColor: kBg,
    dividerColor: kBorder,
    appBarTheme: const AppBarTheme(
      backgroundColor: kBg,
      foregroundColor: kText,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
    ),
    cardTheme: CardThemeData(
      color: kSurface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: const BorderSide(color: kBorder),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: kSurface,
      labelStyle: const TextStyle(color: kMuted),
      hintStyle: const TextStyle(color: kMuted),
      border: OutlineInputBorder(borderRadius: radius, borderSide: const BorderSide(color: kBorder)),
      enabledBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: const BorderSide(color: kBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: const BorderSide(color: kAccent, width: 1.5),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: kAccent,
        foregroundColor: kOnAccent,
        shape: RoundedRectangleBorder(borderRadius: radius),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: kText,
        side: const BorderSide(color: kBorder),
        shape: RoundedRectangleBorder(borderRadius: radius),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      ),
    ),
    snackBarTheme: const SnackBarThemeData(
      backgroundColor: kSurface2,
      contentTextStyle: TextStyle(color: kText),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: kSurface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: radius),
    ),
    listTileTheme: const ListTileThemeData(textColor: kText, iconColor: kMuted),
    textTheme: ThemeData.dark().textTheme.apply(bodyColor: kText, displayColor: kText),
  );
}
