import 'dart:convert';

import 'package:flutter/services.dart';

import 'models.dart';

/// Kotlin yadro bilan aloqa. Testlarda soxta implementatsiya bilan almashtiriladi.
abstract class EngineApi {
  /// Saqlangan prognozdan baholangan holat (tarmoqsiz). Birinchi ishga tushishda null.
  Future<Snapshot?> snapshot();

  /// Prognozni yangilash va xavfni qayta baholash.
  Future<Snapshot> refresh();

  Future<Settings> settings();

  /// Yadro qiymatlarni tekshirib, tozalangan sozlamalarni qaytaradi.
  Future<Settings> saveSettings(Settings settings);

  Future<Catalog> catalog();

  Future<DateTime?> lastSync();

  /// "granted" | "denied" | "disabled"
  Future<String> notificationStatus();

  Future<String> requestNotificationPermission();

  Future<void> openNotificationSettings();

  /// Bildirishnoma bosilib ilova ochilgan bo'lsa — joy id'si.
  Future<String?> consumeLaunchPlaceId();

  Future<bool> openUrl(String url);

  Future<bool> share(String text);

  Future<bool> dial(String number);

  /// Ilova ochiq paytda bildirishnoma bosilsa.
  set onOpenPlace(void Function(String placeId)? handler);
}

class ChannelEngine implements EngineApi {
  ChannelEngine() {
    _channel.setMethodCallHandler((call) async {
      final handler = _onOpenPlace;
      if (call.method == 'openPlace' && call.arguments is String && handler != null) {
        handler(call.arguments as String);
        return true;
      }
      // Ishlov beruvchi hali o'rnatilmagan — Kotlin id'ni saqlab qoladi (consumeLaunchPlaceId).
      return false;
    });
  }

  static const _channel = MethodChannel('uz.havoradar/engine');
  void Function(String)? _onOpenPlace;

  @override
  set onOpenPlace(void Function(String placeId)? handler) => _onOpenPlace = handler;

  Future<Map<String, dynamic>?> _json(String method, [Object? args]) async {
    final raw = await _channel.invokeMethod<String>(method, args);
    if (raw == null) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  @override
  Future<Snapshot?> snapshot() async {
    final j = await _json('getSnapshot');
    return j == null ? null : Snapshot.fromJson(j);
  }

  @override
  Future<Snapshot> refresh() async => Snapshot.fromJson((await _json('refresh'))!);

  @override
  Future<Settings> settings() async => Settings.fromJson((await _json('getSettings'))!);

  @override
  Future<Settings> saveSettings(Settings settings) async =>
      Settings.fromJson((await _json('saveSettings', jsonEncode(settings.toJson())))!);

  @override
  Future<Catalog> catalog() async => Catalog.fromJson((await _json('getCatalog'))!);

  @override
  Future<DateTime?> lastSync() async {
    final raw = await _channel.invokeMethod<String>('lastSync');
    return raw == null ? null : DateTime.tryParse(raw);
  }

  @override
  Future<String> notificationStatus() async => await _channel.invokeMethod<String>('notificationStatus') ?? 'disabled';

  @override
  Future<String> requestNotificationPermission() async =>
      await _channel.invokeMethod<String>('requestNotificationPermission') ?? 'disabled';

  @override
  Future<void> openNotificationSettings() => _channel.invokeMethod<bool>('openNotificationSettings');

  @override
  Future<String?> consumeLaunchPlaceId() => _channel.invokeMethod<String>('consumeLaunchPlaceId');

  @override
  Future<bool> openUrl(String url) async => await _channel.invokeMethod<bool>('openUrl', url) ?? false;

  @override
  Future<bool> share(String text) async => await _channel.invokeMethod<bool>('share', text) ?? false;

  @override
  Future<bool> dial(String number) async => await _channel.invokeMethod<bool>('dial', number) ?? false;
}
