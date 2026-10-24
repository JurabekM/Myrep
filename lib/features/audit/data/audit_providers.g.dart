// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$ledgerServiceHash() => r'aafe028ab7d836a00c348aa4082cb24720d48fd6';

/// See also [ledgerService].
@ProviderFor(ledgerService)
final ledgerServiceProvider = FutureProvider<LedgerService>.internal(
  ledgerService,
  name: r'ledgerServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$ledgerServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef LedgerServiceRef = FutureProviderRef<LedgerService>;
String _$homeKpisHash() => r'4acdda855a23b9a855c6caadd7e59309f64818bb';

/// Bosh ekran ko'rsatkichlari. O'zgarishdan keyin `invalidateMoneyViews`.
///
/// Copied from [homeKpis].
@ProviderFor(homeKpis)
final homeKpisProvider = AutoDisposeFutureProvider<HomeKpis>.internal(
  homeKpis,
  name: r'homeKpisProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$homeKpisHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef HomeKpisRef = AutoDisposeFutureProviderRef<HomeKpis>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
