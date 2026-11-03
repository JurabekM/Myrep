import 'package:flutter/material.dart';

/// Myrep dizayn tokenlari (CLAUDE.md): standart — Claude Code dark uslubi.
class Tokens {
  const Tokens({
    required this.paper,
    required this.sidebar,
    required this.surface,
    required this.line,
    required this.ink,
    required this.inkMuted,
    required this.accent,
    required this.accentInk,
    required this.accentText,
    required this.warn,
    required this.danger,
  });

  final Color paper;
  final Color sidebar;
  final Color surface;
  final Color line;
  final Color ink;
  final Color inkMuted;
  final Color accent;
  final Color accentInk;
  final Color accentText;
  final Color warn;
  final Color danger;

  static const dark = Tokens(
    paper: Color(0xFF262624),
    sidebar: Color(0xFF1F1E1D),
    surface: Color(0xFF30302E),
    line: Color(0xFF4A4945),
    ink: Color(0xFFFAF9F5),
    inkMuted: Color(0xFFA6A39A),
    accent: Color(0xFFD97757),
    accentInk: Color(0xFF1F1E1D),
    accentText: Color(0xFFE8957A),
    warn: Color(0xFFE0A458),
    danger: Color(0xFFE5786D),
  );

  /// Ixtiyoriy light mavzu. Kontrast (oq fonda): ink 15.9:1, inkMuted 5.0:1, accentText 4.6:1.
  static const light = Tokens(
    paper: Color(0xFFFAF9F5),
    sidebar: Color(0xFFF0EEE6),
    surface: Color(0xFFFFFFFF),
    line: Color(0xFFD9D6CC),
    ink: Color(0xFF1F1E1D),
    inkMuted: Color(0xFF65625A),
    accent: Color(0xFFD97757),
    accentInk: Color(0xFF1F1E1D),
    accentText: Color(0xFFA9492A),
    warn: Color(0xFF8F5A12),
    danger: Color(0xFFB3261E),
  );
}

/// Xavf darajalari ranglari. Dark fonda (#30302E) barchasi ≥ 4.5:1 kontrastga ega.
class LevelColors {
  static Color of(String level, {bool light = false}) {
    if (light) {
      return switch (level) {
        'CALM' => const Color(0xFF2E6B2D),
        'WATCH' => const Color(0xFF2F5F8F),
        'ADVISORY' => const Color(0xFF8F5A12),
        'WARNING' => const Color(0xFFA9492A),
        _ => const Color(0xFFB3261E),
      };
    }
    return switch (level) {
      'CALM' => const Color(0xFF7FB77E),
      'WATCH' => const Color(0xFF8FB3D9),
      'ADVISORY' => const Color(0xFFE0A458),
      'WARNING' => const Color(0xFFE8957A),
      _ => const Color(0xFFE5786D),
    };
  }
}

extension TokensX on BuildContext {
  Tokens get tokens => Theme.of(this).brightness == Brightness.light ? Tokens.light : Tokens.dark;
  bool get isLight => Theme.of(this).brightness == Brightness.light;
  Color levelColor(String level) => LevelColors.of(level, light: isLight);
}

ThemeData buildTheme(Tokens t, Brightness brightness) {
  final scheme = ColorScheme(
    brightness: brightness,
    primary: t.accent,
    onPrimary: t.accentInk,
    secondary: t.accentText,
    onSecondary: t.accentInk,
    error: t.danger,
    onError: t.accentInk,
    surface: t.paper,
    onSurface: t.ink,
    surfaceContainerLowest: t.sidebar,
    surfaceContainerLow: t.sidebar,
    surfaceContainer: t.surface,
    surfaceContainerHigh: t.surface,
    surfaceContainerHighest: t.surface,
    onSurfaceVariant: t.inkMuted,
    outline: t.line,
    outlineVariant: t.line,
  );
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'NotoSans',
    scaffoldBackgroundColor: t.paper,
    canvasColor: t.paper,
    dividerColor: t.line,
  );
  return base.copyWith(
    appBarTheme: AppBarTheme(
      backgroundColor: t.paper,
      foregroundColor: t.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(fontFamily: 'NotoSans', fontSize: 20, fontWeight: FontWeight.w700, color: t.ink),
    ),
    cardTheme: CardThemeData(
      color: t.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: BorderSide(color: t.line)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: t.sidebar,
      indicatorColor: t.accent.withValues(alpha: 0.25),
      labelTextStyle: WidgetStatePropertyAll(TextStyle(fontFamily: 'NotoSans', fontSize: 12, color: t.ink)),
      iconTheme: WidgetStateProperty.resolveWith(
        (s) => IconThemeData(color: s.contains(WidgetState.selected) ? t.accentText : t.inkMuted),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: t.surface,
      selectedColor: t.accent.withValues(alpha: 0.25),
      side: BorderSide(color: t.line),
      labelStyle: TextStyle(fontFamily: 'NotoSans', color: t.ink),
    ),
    dialogTheme: DialogThemeData(backgroundColor: t.surface, barrierColor: Colors.black.withValues(alpha: 0.6)),
    bottomSheetTheme: BottomSheetThemeData(backgroundColor: t.surface, modalBarrierColor: Colors.black.withValues(alpha: 0.6)),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: t.accent,
        foregroundColor: t.accentInk,
        minimumSize: const Size(64, 56),
        textStyle: const TextStyle(fontFamily: 'NotoSans', fontWeight: FontWeight.w700, fontSize: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: t.ink,
        side: BorderSide(color: t.line),
        minimumSize: const Size(64, 48),
      ),
    ),
    textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(foregroundColor: t.accentText)),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: t.surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: t.line)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: t.line)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: t.accent, width: 2)),
      hintStyle: TextStyle(color: t.inkMuted),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? t.accentInk : t.inkMuted),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? t.accent : t.surface),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: t.accent, linearTrackColor: t.line),
    snackBarTheme: SnackBarThemeData(backgroundColor: t.surface, contentTextStyle: TextStyle(color: t.ink, fontFamily: 'NotoSans')),
  );
}
