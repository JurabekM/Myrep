// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'pin_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_PinRecord _$PinRecordFromJson(Map<String, dynamic> json) => _PinRecord(
  version: (json['version'] as num).toInt(),
  algorithm: json['algorithm'] as String,
  iterations: (json['iterations'] as num).toInt(),
  salt: json['salt'] as String,
  hash: json['hash'] as String,
);

Map<String, dynamic> _$PinRecordToJson(_PinRecord instance) =>
    <String, dynamic>{
      'version': instance.version,
      'algorithm': instance.algorithm,
      'iterations': instance.iterations,
      'salt': instance.salt,
      'hash': instance.hash,
    };

_LockoutState _$LockoutStateFromJson(Map<String, dynamic> json) =>
    _LockoutState(
      failedAttempts: (json['failedAttempts'] as num?)?.toInt() ?? 0,
      lockStartedAt: json['lockStartedAt'] == null
          ? null
          : DateTime.parse(json['lockStartedAt'] as String),
      lockedUntil: json['lockedUntil'] == null
          ? null
          : DateTime.parse(json['lockedUntil'] as String),
    );

Map<String, dynamic> _$LockoutStateToJson(_LockoutState instance) =>
    <String, dynamic>{
      'failedAttempts': instance.failedAttempts,
      'lockStartedAt': instance.lockStartedAt?.toIso8601String(),
      'lockedUntil': instance.lockedUntil?.toIso8601String(),
    };
