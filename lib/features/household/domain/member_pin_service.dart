import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';

/// Oila a'zosining ixtiyoriy shaxsiy PIN'i (MVP_PLAN 0-bo'lim: oilaviy
/// rozilik). Hosila va lockout qoidalari asosiy PIN bilan bir xil
/// ([PinService]), lekin har a'zoning xatolar hisobi alohida.
class MemberPinService {
  MemberPinService({
    required PinService pins,
    required MemberRepository members,
  }) : _pins = pins,
       _members = members;

  final PinService _pins;
  final MemberRepository _members;

  static String lockoutKey(Member m) => 'member_pin_lockout_${m.meta.id}';

  /// PIN o'rnatadi yoki almashtiradi. Noto'g'ri formatda [ArgumentError].
  Future<Member> setPin(Member m, String pin) async {
    final record = await _pins.createRecord(pin);
    final updated = await _members.update(m.copyWith(personalPin: record));
    await _pins.resetFailures(key: lockoutKey(m));
    return updated;
  }

  Future<Member> clearPin(Member m) =>
      _members.update(m.copyWith(personalPin: null));

  /// PIN'i yo'q a'zo uchun tasdiq PIN so'ramaydi — [PinAccepted].
  Future<PinCheck> verify(Member m, String pin) async {
    final record = m.personalPin;
    if (record == null) return const PinAccepted();
    return _pins.verifyRecord(record, pin, lockoutKey: lockoutKey(m));
  }
}
