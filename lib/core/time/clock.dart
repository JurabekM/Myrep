import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'clock.g.dart';

/// Vaqt manbai. Testlarda soxta soat bilan almashtiriladi.
///
/// Vazifa 3 da `Asia/Tashkent` lokal sanasi va `weekAnchor` shu yerga
/// qo'shiladi.
// ignore: one_member_abstracts
abstract interface class Clock {
  /// Joriy vaqt, UTC.
  DateTime nowUtc();
}

class SystemClock implements Clock {
  const SystemClock();

  @override
  DateTime nowUtc() => DateTime.now().toUtc();
}

@Riverpod(keepAlive: true)
Clock clock(Ref ref) => const SystemClock();
