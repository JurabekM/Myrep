import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'providers.dart';

/// Sinxronlash holati (sozlamalar ekrani uchun).
class SyncState {
  const SyncState({
    this.configured = false,
    this.connected = false,
    this.pending = 0,
    this.lastAt,
    this.running = false,
    this.error,
    this.lastReport,
  });
  final bool configured;
  final bool connected;
  final int pending;
  final DateTime? lastAt;
  final bool running;
  final Object? error;
  final SyncReport? lastReport;

  SyncState copyWith({
    bool? connected,
    int? pending,
    DateTime? lastAt,
    bool? running,
    Object? error,
    SyncReport? lastReport,
  }) => SyncState(
    configured: configured,
    connected: connected ?? this.connected,
    pending: pending ?? this.pending,
    lastAt: lastAt ?? this.lastAt,
    running: running ?? this.running,
    error: error,
    lastReport: lastReport ?? this.lastReport,
  );
}

/// Fonda sinxronlash (ADR-0012): ulanganda har [interval] da, ilova qayta ochilganda va qo'lda. Bir vaqtda bitta.
class SyncController extends Notifier<SyncState> {
  static const interval = Duration(minutes: 5);
  Timer? _timer;
  AppLifecycleListener? _lifecycle;
  Future<void>? _inFlight;

  @override
  SyncState build() {
    ref.onDispose(() {
      _timer?.cancel();
      _lifecycle?.dispose();
    });
    final configured = ref.watch(serverApiProvider) != null;
    if (configured) {
      _lifecycle = AppLifecycleListener(onResume: () => unawaited(syncNow(quiet: true)));
      _timer = Timer.periodic(interval, (_) => unawaited(syncNow(quiet: true)));
      Future.microtask(refresh);
    }
    return SyncState(configured: configured);
  }

  /// Ulanish, navbat va oxirgi vaqtni qayta o'qiydi.
  Future<void> refresh() async {
    final api = ref.read(serverApiProvider);
    if (api == null) return;
    final db = ref.read(databaseProvider);
    final engine = SyncEngine(db, api);
    final last = await LocalPrefRepository(db).get(SyncEngine.lastSyncKey);
    state = state.copyWith(
      connected: await api.tokens.read() != null,
      pending: await engine.pendingCount(),
      lastAt: last == null ? null : DateTime.tryParse(last),
      error: state.error,
    );
  }

  /// Hozir sinxronlash. `quiet` — fon chaqiruvi (ulanmagan bo'lsa hech narsa qilmaydi).
  Future<void> syncNow({bool quiet = false}) {
    if (_inFlight != null) return _inFlight!;
    return _inFlight = _run(quiet).whenComplete(() => _inFlight = null);
  }

  Future<void> _run(bool quiet) async {
    final api = ref.read(serverApiProvider);
    if (api == null || await api.tokens.read() == null) {
      if (!quiet) await refresh();
      return;
    }
    state = state.copyWith(running: true, error: null);
    try {
      final report = await SyncEngine(ref.read(databaseProvider), api).run(now: ref.read(clockProvider)());
      state = state.copyWith(running: false, lastReport: report);
      if (report.pulled > 0) ref.invalidate(repositoriesProvider);
    } catch (e) {
      state = state.copyWith(running: false, error: e);
    }
    await refresh();
  }

  /// Oflayn yaratilgan laboratoriyani serverda ro'yxatdan o'tkazish (LEAD/ADMIN).
  Future<void> registerLab(String password) async {
    final api = ref.read(serverApiProvider) ?? (throw StateError('server_not_configured'));
    final seed = await ref.read(keyStoreProvider).readSeed() ?? (throw StateError('Qurilma kaliti yo\'q'));
    final signer = await Ed25519Signer.fromSeed(seed);
    state = state.copyWith(running: true, error: null);
    try {
      final report = await ServerAccount(
        ref.read(databaseProvider),
        api,
      ).registerLab(password: password, publicKeyHex: signer.publicKeyHex);
      state = state.copyWith(running: false, lastReport: report);
      ref.invalidate(repositoriesProvider);
    } catch (e) {
      state = state.copyWith(running: false, error: e);
      rethrow;
    } finally {
      await refresh();
    }
  }

  Future<String> createInvite(String role) => ref.read(serverApiProvider)!.createInvite(role);

  Future<void> logout() async {
    await ref.read(serverApiProvider)?.logout();
    state = state.copyWith(error: null);
    await refresh();
  }
}

final syncControllerProvider = NotifierProvider<SyncController, SyncState>(SyncController.new);
