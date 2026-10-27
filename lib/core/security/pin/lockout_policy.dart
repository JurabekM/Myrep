import 'dart:math' as math;

/// O'sib boruvchi kutish: dastlabki 4 ta xato — kutishsiz; 5-xatodan boshlab
/// 30 s, 1 daq, 2 daq, 4 daq … har safar ikki baravar, eng ko'pi 1 soat.
abstract final class LockoutPolicy {
  static const freeAttempts = 5;
  static const baseDelay = Duration(seconds: 30);
  static const maxDelay = Duration(hours: 1);

  /// [failedAttempts] ta ketma-ket xatodan keyingi kutish.
  /// `null` — kutish yo'q.
  static Duration? delayAfter(int failedAttempts) {
    if (failedAttempts < freeAttempts) return null;
    final exponent = math.min(failedAttempts - freeAttempts, 20);
    final seconds = baseDelay.inSeconds * (1 << exponent);
    return seconds >= maxDelay.inSeconds
        ? maxDelay
        : Duration(seconds: seconds);
  }

  /// Kutish qo'yilgunga qadar qolgan urinishlar.
  static int attemptsBeforeLockout(int failedAttempts) =>
      math.max(0, freeAttempts - failedAttempts);
}
