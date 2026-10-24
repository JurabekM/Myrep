// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'subscription_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$subscriptionServiceHash() =>
    r'4cb164714d52731327e07584b311c70f0696305d';

/// See also [subscriptionService].
@ProviderFor(subscriptionService)
final subscriptionServiceProvider =
    FutureProvider<SubscriptionService>.internal(
      subscriptionService,
      name: r'subscriptionServiceProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$subscriptionServiceHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SubscriptionServiceRef = FutureProviderRef<SubscriptionService>;
String _$subscriptionsHash() => r'5474fe2205561cc476211bd31d38f3cbd6210c69';

/// See also [subscriptions].
@ProviderFor(subscriptions)
final subscriptionsProvider =
    AutoDisposeFutureProvider<List<Subscription>>.internal(
      subscriptions,
      name: r'subscriptionsProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$subscriptionsHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SubscriptionsRef = AutoDisposeFutureProviderRef<List<Subscription>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
