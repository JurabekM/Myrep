import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../bindings/api/core.dart';
import '../bindings/third_party/baraka_app.dart';
import '../bindings/third_party/baraka_app/session.dart';
import 'platform.dart';
import 'prefs.dart';

export '../bindings/api/core.dart' show BarakaCore;
export '../bindings/third_party/baraka_app.dart';
export '../bindings/third_party/baraka_app/session.dart';

/// Yadro va platforma xizmatlari. `main.dart` (yoki test) `ProviderScope.overrides` bilan beradi.
class CoreServices {
  CoreServices({required this.core, required this.secrets, required this.window, required this.prefs});

  final BarakaCore core;
  final SecretSource secrets;
  final SecureWindow window;
  final PrefsStore prefs;
}

final servicesProvider = Provider<CoreServices>((ref) => throw UnimplementedError('servicesProvider'));

final coreProvider = Provider<BarakaCore>((ref) => ref.watch(servicesProvider).core);

/// Yadrodagi har bir o'zgarishda oshadi: barcha so'rov provider'lari qayta o'qiladi
/// (desktop'dagi `invalidateQueries()` bilan bir xil xulq).
final changeTickProvider = StateProvider<int>((ref) => 0);

/// Sessiya holati: sozlanmagan → onboarding, qulflangan → qulf ekrani, ochiq → ilova.
final sessionProvider = FutureProvider<SessionStatus>((ref) => ref.watch(coreProvider).status());

/// Ochilgandan keyin yadro hodisalarini tinglash; qulflanganda oqim o'zi tugaydi.
class ChangeWatcher {
  ChangeWatcher(this._ref);

  final Ref _ref;
  StreamSubscription<ChangeEvent>? _sub;

  void start() {
    unawaited(_sub?.cancel());
    _sub = _ref
        .read(coreProvider)
        .watchChanges()
        .listen(
          (_) => _ref.read(changeTickProvider.notifier).state++,
          onError: (Object _) {},
        );
  }

  void stop() {
    unawaited(_sub?.cancel());
    _sub = null;
  }
}

final changeWatcherProvider = Provider<ChangeWatcher>((ref) {
  final w = ChangeWatcher(ref);
  ref.onDispose(w.stop);
  return w;
});

/// Sessiya amallari: sozlash, ochish, qulflash. Har biridan keyin holat qayta o'qiladi.
class SessionActions {
  SessionActions(this._ref);

  final Ref _ref;

  CoreServices get _s => _ref.read(servicesProvider);

  void _opened() {
    _ref.read(changeWatcherProvider).start();
    _ref.invalidate(sessionProvider);
  }

  Future<SetupResult> setup(String pin, BootstrapInput input) async {
    final r = await _s.core.setup(platformSecret: await _s.secrets.create(), pin: pin, input: input);
    _ref.read(changeWatcherProvider).start();
    return r;
  }

  Future<SetupResult> join(String pin, List<int> file, JoinInput input) async {
    final r = await _s.core.joinHousehold(
      platformSecret: await _s.secrets.create(),
      pin: pin,
      file: file,
      input: input,
    );
    _ref.read(changeWatcherProvider).start();
    return r;
  }

  /// Onboarding tugadi (tiklash kodi ko'rsatilgandan keyin) — ilovaga o'tish.
  void finishSetup() => _ref.invalidate(sessionProvider);

  Future<void> unlock(String pin) async {
    await _s.core.unlock(platformSecret: await _s.secrets.load(), pin: pin);
    _opened();
  }

  Future<void> unlockWithRecovery(String code, String newPin) async {
    await _s.core.unlockWithRecovery(platformSecret: await _s.secrets.load(), recoveryCode: code, newPin: newPin);
    _opened();
  }

  Future<void> lock() async {
    try {
      await _s.core.lock();
    } finally {
      _ref.read(changeWatcherProvider).stop();
      _ref.invalidate(sessionProvider);
    }
  }

  /// Ilova fonga o'tib qaytganda (7.4): 2 daqiqadan oshgan bo'lsa — qulf.
  Future<void> lockIfIdle() async {
    if (await _s.core.lockIfIdle()) {
      _ref.read(changeWatcherProvider).stop();
      _ref.invalidate(sessionProvider);
    }
  }

  /// PIN qayta so'raladigan amallar uchun platforma siri.
  Future<List<int>> secret() => _s.secrets.load();
}

final sessionActionsProvider = Provider<SessionActions>(SessionActions.new);

/// Yadro xatosi uchun i18n kaliti (`error.<CODE>`, topilmasa — umumiy xabar).
String errorKey(Object? error, bool Function(String) exists) {
  if (error is AppError) {
    final key = 'error.${error.code}';
    if (exists(key)) return key;
  }
  return 'error.GENERIC';
}
