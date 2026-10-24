import 'package:flutter/material.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'app_settings.freezed.dart';
part 'app_settings.g.dart';

/// Qo'llab-quvvatlanadigan tillar. `uz` — asosiy (lotin), `ru` — ikkinchi.
enum AppLanguage {
  uz,
  ru;

  Locale get locale => Locale(name);
}

/// Foydalanuvchi interfeysi sozlamalari.
@freezed
abstract class AppSettings with _$AppSettings {
  const factory AppSettings({
    @Default(AppLanguage.uz) AppLanguage language,
    @Default(ThemeMode.system) ThemeMode themeMode,
  }) = _AppSettings;

  factory AppSettings.fromJson(Map<String, dynamic> json) =>
      _$AppSettingsFromJson(json);
}
