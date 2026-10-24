// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'onboarding_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$currentHouseholdHash() => r'36a792fa53eb70326cb090d896f8fbc2e6452062';

/// Joriy uy xo'jaligi (onboarding holati, daromad turi, oylik kuni).
///
/// Copied from [currentHousehold].
@ProviderFor(currentHousehold)
final currentHouseholdProvider = AutoDisposeFutureProvider<Household>.internal(
  currentHousehold,
  name: r'currentHouseholdProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$currentHouseholdHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef CurrentHouseholdRef = AutoDisposeFutureProviderRef<Household>;
String _$onboardedHash() => r'8913f455a70f457f50a1b68f0090c512c682bdbb';

/// Onboarding tugaganmi (router shunga qarab `/onboarding` ga yo'naltiradi).
///
/// Copied from [onboarded].
@ProviderFor(onboarded)
final onboardedProvider = FutureProvider<bool>.internal(
  onboarded,
  name: r'onboardedProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$onboardedHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef OnboardedRef = FutureProviderRef<bool>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
