// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_settings.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_AppSettings _$AppSettingsFromJson(Map<String, dynamic> json) => _AppSettings(
  language:
      $enumDecodeNullable(_$AppLanguageEnumMap, json['language']) ??
      AppLanguage.uz,
  themeMode:
      $enumDecodeNullable(_$ThemeModeEnumMap, json['themeMode']) ??
      ThemeMode.system,
);

Map<String, dynamic> _$AppSettingsToJson(_AppSettings instance) =>
    <String, dynamic>{
      'language': _$AppLanguageEnumMap[instance.language]!,
      'themeMode': _$ThemeModeEnumMap[instance.themeMode]!,
    };

const _$AppLanguageEnumMap = {AppLanguage.uz: 'uz', AppLanguage.ru: 'ru'};

const _$ThemeModeEnumMap = {
  ThemeMode.system: 'system',
  ThemeMode.light: 'light',
  ThemeMode.dark: 'dark',
};
