import 'dart:convert';

import 'package:flutter/services.dart';

import 'models.dart';

/// Kotlin yadro bilan aloqa. Testlarda soxta implementatsiya bilan almashtiriladi.
abstract class EngineApi {
  /// Saqlangan holat (tarmoqsiz). Birinchi ishga tushishda null.
  Future<Snapshot?> snapshot();

  /// Barcha manbalardan yangilash va xavfni qayta baholash.
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

  /// Bildirishnoma bosilib ilova ochilgan bo'lsa — hodisa id'si.
  Future<String?> consumeLaunchEventId();

  Future<bool> openUrl(String url);

  Future<bool> share(String text);

  Future<bool> dial(String number);

  /// Ilova ochiq paytda bildirishnoma bosilsa.
  set onOpenEvent(void Function(String eventId)? handler);
}

class ChannelEngine implements EngineApi {
  ChannelEngine() {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'openEvent' && call.arguments is String) {
        _onOpenEvent?.call(call.arguments as String);
      }
    });
  }

  static const _channel = MethodChannel('uz.epiradar/engine');
  void Function(String)? _onOpenEvent;

  @override
  set onOpenEvent(void Function(String eventId)? handler) => _onOpenEvent = handler;

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
  Future<String?> consumeLaunchEventId() => _channel.invokeMethod<String>('consumeLaunchEventId');

  @override
  Future<bool> openUrl(String url) async => await _channel.invokeMethod<bool>('openUrl', url) ?? false;

  @override
  Future<bool> share(String text) async => await _channel.invokeMethod<bool>('share', text) ?? false;

  @override
  Future<bool> dial(String number) async => await _channel.invokeMethod<bool>('dial', number) ?? false;
}
