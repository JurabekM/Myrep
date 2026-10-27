import 'package:freezed_annotation/freezed_annotation.dart';

part 'pin_models.freezed.dart';
part 'pin_models.g.dart';

/// Saqlanadigan PIN yozuvi. PIN o'zi yo'q — faqat tuz va hosila.
/// Yozuv Keystore kaliti bilan shifrlangan blob ichida turadi.
@freezed
abstract class PinRecord with _$PinRecord {
  const factory PinRecord({
    required int version,
    required String algorithm,
    required int iterations,

    /// base64
    required String salt,

    /// base64
    required String hash,
  }) = _PinRecord;

  factory PinRecord.fromJson(Map<String, dynamic> json) =>
      _$PinRecordFromJson(json);
}

/// Noto'g'ri urinishlar va kutish holati. Ilova qayta ishga tushsa ham
/// saqlanib qoladi.
@freezed
abstract class LockoutState with _$LockoutState {
  const factory LockoutState({
    @Default(0) int failedAttempts,

    /// Kutish boshlangan payt (UTC). Soat orqaga surilganini aniqlash uchun.
    DateTime? lockStartedAt,

    /// Kutish tugaydigan payt (UTC).
    DateTime? lockedUntil,
  }) = _LockoutState;

  factory LockoutState.fromJson(Map<String, dynamic> json) =>
      _$LockoutStateFromJson(json);
}
