// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'secure_screen_sync.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$secureScreenSyncHash() => r'60037c7fb1436fa878f0ddb380f3104b2f0cf43d';

/// Marshrut darajasidagi FLAG_SECURE: joriy manzil [AppRoutes.secure] da
/// bo'lsa skrinshot va ekran yozuvi taqiqlanadi. Holat — oxirgi yuborilgan
/// qiymat.
///
/// Copied from [SecureScreenSync].
@ProviderFor(SecureScreenSync)
final secureScreenSyncProvider =
    NotifierProvider<SecureScreenSync, bool>.internal(
      SecureScreenSync.new,
      name: r'secureScreenSyncProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$secureScreenSyncHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$SecureScreenSync = Notifier<bool>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
