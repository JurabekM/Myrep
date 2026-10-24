// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'price_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$priceBookServiceHash() => r'5acc6fd57d1e87a3c405b341671ec0f1f6067c44';

/// See also [priceBookService].
@ProviderFor(priceBookService)
final priceBookServiceProvider = FutureProvider<PriceBookService>.internal(
  priceBookService,
  name: r'priceBookServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$priceBookServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef PriceBookServiceRef = FutureProviderRef<PriceBookService>;
String _$priceBookHash() => r'21bc304320083dfe6cb8ab2f9386b85735d49f6f';

/// See also [priceBook].
@ProviderFor(priceBook)
final priceBookProvider = AutoDisposeFutureProvider<PriceBookOverview>.internal(
  priceBook,
  name: r'priceBookProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$priceBookHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef PriceBookRef = AutoDisposeFutureProviderRef<PriceBookOverview>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
