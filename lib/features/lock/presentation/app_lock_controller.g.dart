// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_lock_controller.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$appLockControllerHash() => r'3f37f3b290caf8cb25332bb48c6b8909ced9d287';

/// Ilova qulfi holati va fon → qaytish tsikli.
///
/// Ilova fonga o'tgan paytdan boshlab [SecuritySettings.lockTimeoutMinutes]
/// (standart 2 daqiqa) o'tsa, qaytishda qayta qulflanadi.
///
/// Copied from [AppLockController].
@ProviderFor(AppLockController)
final appLockControllerProvider =
    NotifierProvider<AppLockController, LockStatus>.internal(
      AppLockController.new,
      name: r'appLockControllerProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$appLockControllerHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$AppLockController = Notifier<LockStatus>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
