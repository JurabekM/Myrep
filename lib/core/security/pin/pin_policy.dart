/// PIN talablari: aniq 6 ta raqam, topilishi oson ketma-ketliklar emas.
abstract final class PinPolicy {
  static const length = 6;

  static PinIssue? validate(String pin) {
    if (pin.length != length) return PinIssue.wrongLength;
    if (!RegExp(r'^[0-9]+$').hasMatch(pin)) return PinIssue.notDigits;
    if (_isTrivial(pin)) return PinIssue.tooSimple;
    return null;
  }

  /// 111111, 123456, 987654 kabi kodlar.
  static bool _isTrivial(String pin) {
    final d = pin.codeUnits;
    bool allSteps(int step) {
      for (var i = 1; i < d.length; i++) {
        if (d[i] - d[i - 1] != step) return false;
      }
      return true;
    }

    return allSteps(0) || allSteps(1) || allSteps(-1);
  }
}

enum PinIssue { wrongLength, notDigits, tooSimple }
