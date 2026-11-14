/// Kotlin qatlami bilan aloqa (MainActivity.kt). Hamma narsa qurilma ichida, tarmoqsiz.
library;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class Native {
  Native._();
  static const _ch = MethodChannel('uz.rostor.rostor2/native');

  /// Qo'ng'iroq Qalqoni tarixga yangi yozuv qo'shganda oshadi.
  static final callsChanged = ValueNotifier<int>(0);

  static void onIncoming(void Function(Map<String, dynamic>) handler) {
    _ch.setMethodCallHandler((call) async {
      if (call.method == 'incoming' && call.arguments is Map) {
        handler(Map<String, dynamic>.from(call.arguments as Map));
      } else if (call.method == 'callsChanged') {
        callsChanged.value++;
      }
    });
  }

  static Future<Map<String, dynamic>?> _map(String method, [Map<String, Object?>? args]) async {
    final r = await _ch.invokeMethod<Object?>(method, args);
    return r == null ? null : _deep(r) as Map<String, dynamic>;
  }

  /// Platforma kanalidan kelgan `Map<Object?, Object?>` larni `Map<String, dynamic>` ga aylantiradi.
  static Object? _deep(Object? v) {
    if (v is Map) return {for (final e in v.entries) e.key.toString(): _deep(e.value)};
    if (v is List) return [for (final x in v) _deep(x)];
    return v;
  }

  static Future<Map<String, dynamic>?> takeIncoming() => _map('takeIncoming');
  static Future<Map<String, dynamic>> selfInfo() async => (await _map('selfInfo'))!;
  static Future<Map<String, dynamic>> loadDb() async => (await _map('loadDb'))!;
  static Future<Map<String, dynamic>?> pickApk() => _map('pickApk');
  static Future<Map<String, dynamic>> inspectUri(String uri) async => (await _map('inspectUri', {'uri': uri}))!;
  static Future<Map<String, dynamic>> audit() async => (await _map('audit'))!;
  static Future<Map<String, dynamic>> changedSinceLast() async => (await _map('changedSinceLast'))!;
  static Future<void> markAudited(int sequence) => _ch.invokeMethod('markAudited', {'sequence': sequence});
  static Future<Uint8List?> appIcon(String pkg) => _ch.invokeMethod<Uint8List>('appIcon', {'package': pkg});

  static Future<bool> open(String kind, [String? pkg]) async =>
      (await _ch.invokeMethod<bool>(kind, pkg == null ? null : {'package': pkg})) ?? false;

  // Qo'ng'iroq Qalqoni (F2)
  static Future<Map<String, dynamic>> callStatus() async => (await _map('callStatus'))!;
  static Future<Map<String, dynamic>> requestCallRole() async => (await _map('requestCallRole'))!;
  static Future<Map<String, dynamic>> requestNotifications() async => (await _map('requestNotifications'))!;
  static Future<Map<String, dynamic>> checkPhone(String number) async => (await _map('checkPhone', {'number': number}))!;
  static Future<bool> testCallNotification() async => (await _ch.invokeMethod<bool>('testCallNotification')) ?? false;

  // Firibgarlik hisoboti (F3)
  static Future<Map<String, dynamic>> reportIdentity() async => (await _map('reportIdentity'))!;
  static Future<Map<String, dynamic>> createReport(Map<String, Object?> args) async => (await _map('createReport', args))!;
  static Future<List<Map<String, dynamic>>> listReports() async {
    final r = await _ch.invokeMethod<List<Object?>>('listReports');
    return [for (final x in r ?? const []) _deep(x) as Map<String, dynamic>];
  }
  static Future<Map<String, dynamic>> readReport(String name) async => (await _map('readReport', {'name': name}))!;
  static Future<bool> shareReport(String name) async => (await _ch.invokeMethod<bool>('shareReport', {'name': name})) ?? false;
  static Future<bool> deleteReport(String name) async => (await _ch.invokeMethod<bool>('deleteReport', {'name': name})) ?? false;

  static Future<String?> kvGet(String key) => _ch.invokeMethod<String>('kvGet', {'key': key});
  static Future<void> kvSet(String key, String value) => _ch.invokeMethod('kvSet', {'key': key, 'value': value});
}
