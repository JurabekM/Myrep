import 'package:baraka_daftari/core/security/security_api.pigeon.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

export 'package:baraka_daftari/core/security/security_api.pigeon.dart'
    show
        BiometricAvailability,
        BiometricOutcome,
        IntegritySignals,
        NativeInfo,
        SecurityApi;

part 'security_bridge.g.dart';

/// Kotlin xavfsizlik qatlamiga Pigeon orqali kirish nuqtasi.
/// Testlarda bu provayder soxta implementatsiya bilan almashtiriladi.
@Riverpod(keepAlive: true)
SecurityApi securityApi(Ref ref) => SecurityApi();

/// Native ko'prik holati (Vazifa 1 qabul mezoni: Kotlin stub javob qaytaradi).
@riverpod
Future<NativeInfo> nativeInfo(Ref ref) => ref.watch(securityApiProvider).ping();
