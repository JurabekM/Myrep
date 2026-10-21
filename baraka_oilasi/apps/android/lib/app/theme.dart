import 'package:flutter/material.dart';

import 'theme/tokens.g.dart';

/// Rang to'plami (tokens.g.dart dan): dark — standart (Claude Code dark theme uslubi).
@immutable
class BarakaPalette extends ThemeExtension<BarakaPalette> {
  const BarakaPalette({
    required this.paper,
    required this.sidebar,
    required this.surface,
    required this.ink,
    required this.inkMuted,
    required this.line,
    required this.fieldLine,
    required this.accent,
    required this.accentInk,
    required this.accentText,
    required this.zarur,
    required this.kerak,
    required this.havas,
    required this.warn,
    required this.danger,
    required this.chart1,
    required this.chart2,
  });

  static const dark = BarakaPalette(
    paper: BarakaDarkColors.paper,
    sidebar: BarakaDarkColors.sidebar,
    surface: BarakaDarkColors.surface,
    ink: BarakaDarkColors.ink,
    inkMuted: BarakaDarkColors.inkMuted,
    line: BarakaDarkColors.line,
    fieldLine: BarakaDarkColors.fieldLine,
    accent: BarakaDarkColors.accent,
    accentInk: BarakaDarkColors.accentInk,
    accentText: BarakaDarkColors.accentText,
    zarur: BarakaDarkColors.zarur,
    kerak: BarakaDarkColors.kerak,
    havas: BarakaDarkColors.havas,
    warn: BarakaDarkColors.warn,
    danger: BarakaDarkColors.danger,
    chart1: BarakaDarkColors.chart1,
    chart2: BarakaDarkColors.chart2,
  );

  static const light = BarakaPalette(
    paper: BarakaLightColors.paper,
    sidebar: BarakaLightColors.sidebar,
    surface: BarakaLightColors.surface,
    ink: BarakaLightColors.ink,
    inkMuted: BarakaLightColors.inkMuted,
    line: BarakaLightColors.line,
    fieldLine: BarakaLightColors.fieldLine,
    accent: BarakaLightColors.accent,
    accentInk: BarakaLightColors.accentInk,
    accentText: BarakaLightColors.accentText,
    zarur: BarakaLightColors.zarur,
    kerak: BarakaLightColors.kerak,
    havas: BarakaLightColors.havas,
    warn: BarakaLightColors.warn,
    danger: BarakaLightColors.danger,
    chart1: BarakaLightColors.chart1,
    chart2: BarakaLightColors.chart2,
  );

  final Color paper;
  final Color sidebar;
  final Color surface;
  final Color ink;
  final Color inkMuted;
  final Color line;
  final Color fieldLine;
  final Color accent;
  final Color accentInk;
  final Color accentText;
  final Color zarur;
  final Color kerak;
  final Color havas;
  final Color warn;
  final Color danger;
  final Color chart1;
  final Color chart2;

  @override
  BarakaPalette copyWith() => this;

  @override
  BarakaPalette lerp(BarakaPalette? other, double t) => t < 0.5 ? this : (other ?? this);
}

extension PaletteContext on BuildContext {
  BarakaPalette get palette => Theme.of(this).extension<BarakaPalette>() ?? BarakaPalette.dark;
}

ThemeData barakaTheme({required bool dark}) {
  final p = dark ? BarakaPalette.dark : BarakaPalette.light;
  final scheme = ColorScheme(
    brightness: dark ? Brightness.dark : Brightness.light,
    primary: p.accent,
    onPrimary: p.accentInk,
    secondary: p.accent,
    onSecondary: p.accentInk,
    error: p.danger,
    onError: p.accentInk,
    surface: p.paper,
    onSurface: p.ink,
    onSurfaceVariant: p.inkMuted,
    surfaceContainerLowest: p.paper,
    surfaceContainerLow: p.surface,
    surfaceContainer: p.surface,
    surfaceContainerHigh: p.surface,
    surfaceContainerHighest: p.surface,
    outline: p.fieldLine,
    outlineVariant: p.line,
  );
  const radius = BorderRadius.all(Radius.circular(BarakaDimens.radiusMd));
  OutlineInputBorder border(Color c, [double w = 1]) => OutlineInputBorder(
    borderRadius: radius,
    borderSide: BorderSide(color: c, width: w),
  );
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'NotoSans',
    // Noto Sans'da yo'q belgilar (→, ✓) — tizim shriftidan (Android: Roboto).
    fontFamilyFallback: const ['sans-serif'],
    scaffoldBackgroundColor: p.paper,
    canvasColor: p.paper,
    dividerColor: p.line,
    extensions: [p],
  );
  return base.copyWith(
    appBarTheme: AppBarTheme(
      backgroundColor: p.paper,
      foregroundColor: p.ink,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
    drawerTheme: DrawerThemeData(backgroundColor: p.sidebar, surfaceTintColor: Colors.transparent),
    cardTheme: CardThemeData(
      color: p.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: const BorderRadius.all(Radius.circular(BarakaDimens.radiusLg)),
        side: BorderSide(color: p.line),
      ),
    ),
    dialogTheme: DialogThemeData(backgroundColor: p.surface, surfaceTintColor: Colors.transparent),
    bottomSheetTheme: BottomSheetThemeData(backgroundColor: p.surface, surfaceTintColor: Colors.transparent),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: p.surface,
      border: border(p.fieldLine),
      enabledBorder: border(p.fieldLine),
      focusedBorder: border(p.accent, 2),
      errorBorder: border(p.danger),
      focusedErrorBorder: border(p.danger, 2),
      labelStyle: TextStyle(color: p.inkMuted),
      floatingLabelStyle: WidgetStateTextStyle.resolveWith(
        (s) => TextStyle(color: s.contains(WidgetState.focused) ? p.accentText : p.inkMuted),
      ),
      helperStyle: TextStyle(color: p.inkMuted),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: p.accent,
        foregroundColor: p.accentInk,
        disabledBackgroundColor: p.line,
        disabledForegroundColor: p.inkMuted,
        minimumSize: const Size(64, 48),
        shape: const RoundedRectangleBorder(borderRadius: radius),
        textStyle: const TextStyle(fontFamily: 'NotoSans', fontSize: 16, fontWeight: FontWeight.w700),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: p.ink,
        side: BorderSide(color: p.fieldLine),
        minimumSize: const Size(64, 48),
        shape: const RoundedRectangleBorder(borderRadius: radius),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: p.accentText, minimumSize: const Size(48, 48)),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: p.surface,
      selectedColor: p.accent,
      labelStyle: TextStyle(color: p.ink),
      secondaryLabelStyle: TextStyle(color: p.accentInk),
      side: BorderSide(color: p.fieldLine),
      checkmarkColor: p.accentInk,
    ),
    radioTheme: RadioThemeData(fillColor: WidgetStatePropertyAll(p.accent)),
    checkboxTheme: CheckboxThemeData(
      fillColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? p.accent : null),
      checkColor: WidgetStatePropertyAll(p.accentInk),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: p.surface,
      contentTextStyle: TextStyle(color: p.ink),
      behavior: SnackBarBehavior.floating,
    ),
    listTileTheme: ListTileThemeData(iconColor: p.inkMuted, textColor: p.ink),
  );
}
