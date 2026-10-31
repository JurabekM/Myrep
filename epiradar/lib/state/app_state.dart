import 'package:flutter/widgets.dart';

import '../data/engine_api.dart';
import '../data/models.dart';

/// Ilova holati: yadrodan kelgan snapshot, sozlamalar va ma'lumotnomalar.
class AppState extends ChangeNotifier {
  AppState(this.engine);

  final EngineApi engine;

  Snapshot? snapshot;
  Settings settings = const Settings();
  Catalog catalog = Catalog.empty;
  DateTime? lastSync;
  String notificationStatus = 'disabled';

  bool ready = false;
  bool refreshing = false;
  String? error;

  /// Bildirishnoma orqali ochilishi kerak bo'lgan hodisa (UI bir marta iste'mol qiladi).
  String? pendingEventId;

  Future<void> init() async {
    try {
      final results = await Future.wait<Object?>([
        engine.settings(),
        engine.catalog(),
        engine.snapshot(),
        engine.lastSync(),
        engine.notificationStatus(),
        engine.consumeLaunchEventId(),
      ]);
      settings = results[0]! as Settings;
      catalog = results[1]! as Catalog;
      snapshot = results[2] as Snapshot?;
      lastSync = results[3] as DateTime?;
      notificationStatus = results[4]! as String;
      pendingEventId = results[5] as String?;
      engine.onOpenEvent = (id) {
        pendingEventId = id;
        notifyListeners();
      };
    } catch (e) {
      error = 'Yadro ishga tushmadi: $e';
    }
    ready = true;
    notifyListeners();
    // Birinchi ishga tushish yoki eski ma'lumot — darhol yangilaymiz.
    final age = snapshot == null ? null : DateTime.now().difference(snapshot!.generatedAt);
    if (settings.onboardingDone && (age == null || age > const Duration(hours: 1))) {
      await refresh();
    }
  }

  Future<void> refresh() async {
    if (refreshing) return;
    refreshing = true;
    error = null;
    notifyListeners();
    try {
      snapshot = await engine.refresh();
      lastSync = DateTime.now();
      if (snapshot!.sources.every((s) => !s.ok)) {
        error = "Manbalarga ulanib bo'lmadi. Internet aloqasini tekshiring — oxirgi saqlangan ma'lumot ko'rsatilmoqda.";
      }
    } catch (e) {
      error = "Yangilab bo'lmadi: $e";
    } finally {
      refreshing = false;
      notifyListeners();
    }
  }

  Future<void> updateSettings(Settings next) async {
    final countryChanged = next.country != settings.country || next.watchCountries.join() != settings.watchCountries.join();
    settings = next;
    notifyListeners();
    try {
      settings = await engine.saveSettings(next);
      if (countryChanged) {
        // Mamlakat o'zgarsa — xavf darhol (tarmoqsiz) qayta baholanadi, keyin trendlar yangilanadi.
        snapshot = await engine.snapshot() ?? snapshot;
        catalog = await engine.catalog();
        notifyListeners();
        await refresh();
      }
    } catch (e) {
      error = "Sozlamalarni saqlab bo'lmadi: $e";
    }
    notifyListeners();
  }

  Future<void> toggleChecklist(String id) async {
    final done = settings.checklistDone.toList();
    done.contains(id) ? done.remove(id) : done.add(id);
    await updateSettings(settings.copyWith(checklistDone: done));
  }

  Future<String> requestNotifications() async {
    notificationStatus = await engine.requestNotificationPermission();
    notifyListeners();
    return notificationStatus;
  }

  Future<void> recheckNotifications() async {
    notificationStatus = await engine.notificationStatus();
    notifyListeners();
  }

  String? takePendingEvent() {
    final id = pendingEventId;
    pendingEventId = null;
    return id;
  }
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child}) : super(notifier: state);

  static AppState of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;

  /// Qayta qurishga obuna bo'lmasdan (tugma bosilganda va h.k.).
  static AppState read(BuildContext context) => context.getInheritedWidgetOfExactType<AppScope>()!.notifier!;
}
