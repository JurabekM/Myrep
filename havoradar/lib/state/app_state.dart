import 'package:flutter/widgets.dart';

import '../data/engine_api.dart';
import '../data/models.dart';

/// Ilova holati: yadrodan kelgan snapshot, sozlamalar, ma'lumotnomalar va ko'rilayotgan joy.
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

  /// Ekranda ko'rsatilayotgan joy (null — asosiy joy).
  String? viewedPlaceId;

  /// Bildirishnoma orqali ochilishi kerak bo'lgan joy (UI bir marta iste'mol qiladi).
  String? pendingPlaceId;

  /// Sozlamalarni o'qib bo'lmadi — onboarding ko'rsatilmaydi (aks holda saqlangan sozlamalar ustiga yoziladi).
  String? fatalError;
  bool _refreshAgain = false;

  PlaceReport? get viewed {
    final s = snapshot;
    if (s == null) return null;
    return (viewedPlaceId == null ? null : s.place(viewedPlaceId!)) ?? s.main;
  }

  Future<void> init() async {
    engine.onOpenPlace = (id) {
      pendingPlaceId = id;
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
    pendingPlaceId = await safe(engine.consumeLaunchPlaceId) ?? pendingPlaceId;
    ready = true;
    notifyListeners();
    // Birinchi ishga tushish yoki eski ma'lumot — darhol yangilaymiz.
    final age = lastSync == null ? null : DateTime.now().difference(lastSync!);
    if (settings.onboardingDone && (snapshot == null || age == null || age > const Duration(hours: 1))) {
      await refresh();
    }
  }

  Future<void> refresh() async {
    if (refreshing) {
      // Masalan, joy almashtirilganda eski sozlamalar bilan sinxronlash ketayotgan bo'lsa —
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
      } while (_refreshAgain);
      snapshot = result;
      lastSync = DateTime.now();
      if (snapshot!.sources.every((s) => !s.ok)) {
        error = "Prognozni yangilab bo'lmadi. Internet aloqasini tekshiring — oxirgi saqlangan ma'lumot ko'rsatilmoqda.";
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
    final placesChanged = next.allPlaces.join(',') != settings.allPlaces.join(',');
    final profileChanged = next.profile.toSet().length != settings.profile.toSet().length ||
        !next.profile.toSet().containsAll(settings.profile);
    settings = next;
    notifyListeners();
    try {
      settings = await engine.saveSettings(next);
      if (placesChanged || profileChanged) {
        // Tarmoqsiz darhol qayta baholanadi; yangi joy bo'lsa — keyin prognoz yuklanadi.
        snapshot = await engine.snapshot() ?? snapshot;
        if (viewedPlaceId != null && !settings.allPlaces.contains(viewedPlaceId)) viewedPlaceId = null;
        notifyListeners();
        if (placesChanged && settings.onboardingDone) await refresh();
      }
    } catch (e) {
      error = "Sozlamalarni saqlab bo'lmadi: $e";
    }
    notifyListeners();
  }

  void viewPlace(String? id) {
    viewedPlaceId = id == settings.placeId ? null : id;
    notifyListeners();
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

  String? takePendingPlace() {
    final id = pendingPlaceId;
    pendingPlaceId = null;
    return id;
  }
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child}) : super(notifier: state);

  static AppState of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;

  /// Qayta qurishga obuna bo'lmasdan (tugma bosilganda va h.k.).
  static AppState read(BuildContext context) => context.getInheritedWidgetOfExactType<AppScope>()!.notifier!;
}
