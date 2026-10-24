import 'package:baraka_daftari/app/settings/app_settings.dart';
import 'package:flutter/material.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'settings_controller.g.dart';

/// Til va mavzu holati. Hozircha xotirada saqlanadi; doimiy saqlash shifrlangan
/// baza paydo bo'lgach (Vazifa 3) qo'shiladi.
@Riverpod(keepAlive: true)
class SettingsController extends _$SettingsController {
  @override
  AppSettings build() => const AppSettings();

  void setLanguage(AppLanguage language) =>
      state = state.copyWith(language: language);

  void toggleLanguage() => setLanguage(
    state.language == AppLanguage.uz ? AppLanguage.ru : AppLanguage.uz,
  );

  /// Joriy ko'rinayotgan yorqinlikka qarab teskari mavzuga o'tadi.
  void toggleTheme(Brightness current) => state = state.copyWith(
    themeMode: current == Brightness.dark ? ThemeMode.light : ThemeMode.dark,
  );
}
