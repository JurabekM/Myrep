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

  /// Sozlamalarni o'qib bo'lmadi — onboarding ko'rsatilmaydi (aks holda saqlangan sozlamalar ustiga yoziladi).
  String? fatalError;
  bool _refreshAgain = false;

  Future<void> init() async {
    // Bildirishnoma bosilishi ishga tushish paytida ham yo'qolmasligi uchun eng avval.
    engine.onOpenEvent = (id) {
      pendingEventId = id;
      notifyListeners();
    };
    fatalError = null;
    try {
      settings = await engine.settings();
    } catch (e) {
      fatalError = 'Ilova yadrosi ishga tushmadi: $e';
      ready = true;
      notifyListeners();
      return;
    }
    // Qolganlari mustaqil: bittasining xatosi boshqasini to'xtatmaydi.
    Future<T?> safe<T>(Future<T?> Function() f) async {
      try {
        return await f();
      } catch (e) {
        error ??= "Ma'lumotni o'qishda xato: $e";
        return null;
      }
    }

    catalog = await safe(engine.catalog) ?? catalog;
    snapshot = await safe(engine.snapshot);
    lastSync = await safe(engine.lastSync);
    notificationStatus = await safe(engine.notificationStatus) ?? notificationStatus;
    pendingEventId = await safe(engine.consumeLaunchEventId) ?? pendingEventId;
    ready = true;
    notifyListeners();
    // Birinchi ishga tushish yoki eski ma'lumot — darhol yangilaymiz.
    final age = snapshot == null ? null : DateTime.now().difference(snapshot!.generatedAt);
    if (settings.onboardingDone && (age == null || age > const Duration(hours: 1))) {
      await refresh();
    }
  }

  Future<void> refresh() async {
    if (refreshing) {
      // Masalan, mamlakat almashtirilganda eski sozlamalar bilan sinxronlash ketayotgan bo'lsa —
      // tugagach yangi sozlamalar bilan yana bir marta.
      _refreshAgain = true;
      return;
    }
    refreshing = true;
    error = null;
    notifyListeners();
    try {
      Snapshot result;
      do {
        _refreshAgain = false;
        result = await engine.refresh();
        // Eski sozlamalar bilan olingan natija ekranga chiqmaydi — navbatdagi sinxronlash kutiladi.
      } while (_refreshAgain);
      snapshot = result;
      lastSync = DateTime.now();
      if (snapshot!.sources.every((s) => !s.ok)) {
        error = "Manbalarga ulanib bo'lmadi. Internet aloqasini tekshiring — oxirgi saqlangan ma'lumot ko'rsatilmoqda.";
      }
    } catch (e) {
      error = "Yangilab bo'lmadi: $e";
    } finally {
      refreshing = false;
      _refreshAgain = false;
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
