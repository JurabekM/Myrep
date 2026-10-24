// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'security_settings.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_SecuritySettings _$SecuritySettingsFromJson(Map<String, dynamic> json) =>
    _SecuritySettings(
      biometricEnabled: json['biometricEnabled'] as bool? ?? false,
      lockTimeoutMinutes: (json['lockTimeoutMinutes'] as num?)?.toInt() ?? 2,
    );

Map<String, dynamic> _$SecuritySettingsToJson(_SecuritySettings instance) =>
    <String, dynamic>{
      'biometricEnabled': instance.biometricEnabled,
      'lockTimeoutMinutes': instance.lockTimeoutMinutes,
    };

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$securitySettingsRepositoryHash() =>
    r'03610041270b5e455a5a5c2d36e03660afe68166';

/// See also [securitySettingsRepository].
@ProviderFor(securitySettingsRepository)
final securitySettingsRepositoryProvider =
    Provider<SecuritySettingsRepository>.internal(
      securitySettingsRepository,
      name: r'securitySettingsRepositoryProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$securitySettingsRepositoryHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SecuritySettingsRepositoryRef = ProviderRef<SecuritySettingsRepository>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
