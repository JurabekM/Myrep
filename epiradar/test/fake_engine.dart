import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:epiradar/data/engine_api.dart';
import 'package:epiradar/data/models.dart';

/// Haqiqiy Kotlin yadro chiqishi (engine testi `EPIRADAR_EXPORT` bilan yaratadi).
Map<String, dynamic> fixture(String name) =>
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as Map<String, dynamic>;

class FakeEngine implements EngineApi {
  FakeEngine({Settings? settings, bool withSnapshot = true})
      : _settings = settings ?? const Settings(onboardingDone: true),
        _snapshot = withSnapshot ? Snapshot.fromJson(fixture('snapshot.json')) : null;

  Settings _settings;
  final Snapshot? _snapshot;
  final calls = <String>[];
  final opened = <String>[];
  final saved = <Settings>[];
  String permission = 'denied';

  /// Berilsa, refresh() shu Completer tugaguncha kutadi (parallel holatlarni sinash uchun).
  Completer<void>? refreshGate;
  bool failSettings = false;

  @override
  set onOpenEvent(void Function(String eventId)? handler) {}

  @override
  Future<Snapshot?> snapshot() async => _snapshot;

  @override
  Future<Snapshot> refresh() async {
    calls.add('refresh:${_settings.country}');
    await refreshGate?.future;
    return Snapshot.fromJson(fixture('snapshot.json'));
  }

  @override
  Future<Settings> settings() async {
    if (failSettings) throw StateError('prefs');
    return _settings;
  }

  @override
  Future<Settings> saveSettings(Settings settings) async {
    saved.add(settings);
    return _settings = settings;
  }

  @override
  Future<Catalog> catalog() async => Catalog.fromJson(fixture('catalog.json'));

  @override
  Future<DateTime?> lastSync() async => null;

  @override
  Future<String> notificationStatus() async => permission;

  @override
  Future<String> requestNotificationPermission() async {
    calls.add('permission');
    return permission = 'granted';
  }

  @override
  Future<void> openNotificationSettings() async {}

  @override
  Future<String?> consumeLaunchEventId() async => null;

  @override
  Future<bool> openUrl(String url) async {
    opened.add(url);
    return true;
  }

  @override
  Future<bool> share(String text) async {
    calls.add('share');
    return true;
  }

  @override
  Future<bool> dial(String number) async {
    calls.add('dial:$number');
    return true;
  }
}
