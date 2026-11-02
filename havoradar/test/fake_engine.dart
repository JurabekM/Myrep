import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:havoradar/data/engine_api.dart';
import 'package:havoradar/data/models.dart';

/// Haqiqiy Kotlin yadro chiqishi (engine testi `HAVORADAR_EXPORT` bilan yaratadi).
Map<String, dynamic> fixture(String name) =>
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as Map<String, dynamic>;

class FakeEngine implements EngineApi {
  FakeEngine({Settings? settings, bool withSnapshot = true, this.launchPlaceId})
      : _settings = settings ?? Settings.fromJson(fixture('settings.json')).copyWith(onboardingDone: true),
        _snapshot = withSnapshot ? Snapshot.fromJson(fixture('snapshot.json')) : null;

  Settings _settings;
  final Snapshot? _snapshot;
  final String? launchPlaceId;
  final calls = <String>[];
  final opened = <String>[];
  final saved = <Settings>[];
  String permission = 'denied';
  bool failRefresh = false;

  @override
  set onOpenPlace(void Function(String placeId)? handler) {}

  @override
  Future<Snapshot?> snapshot() async => _snapshot;

  @override
  Future<Snapshot> refresh() async {
    calls.add('refresh:${_settings.placeId}');
    if (failRefresh) throw StateError('tarmoq yo\'q');
    return Snapshot.fromJson(fixture('snapshot.json'));
  }

  @override
  Future<Settings> settings() async => _settings;

  @override
  Future<Settings> saveSettings(Settings settings) async {
    saved.add(settings);
    return _settings = settings;
  }

  @override
  Future<Catalog> catalog() async => Catalog.fromJson(fixture('catalog.json'));

  @override
  Future<DateTime?> lastSync() async => _snapshot == null ? null : DateTime.now();

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
  Future<String?> consumeLaunchPlaceId() async => launchPlaceId;

  @override
  Future<bool> openUrl(String url) async {
    opened.add(url);
    return true;
  }

  @override
  Future<bool> share(String text) async {
    calls.add('share:$text');
    return true;
  }

  @override
  Future<bool> dial(String number) async {
    calls.add('dial:$number');
    return true;
  }
}
