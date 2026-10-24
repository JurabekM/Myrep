// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'envelope_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$envelopeServiceHash() => r'7836f1cbf7edbdceb550a4ee16c2604762bf67a2';

/// See also [envelopeService].
@ProviderFor(envelopeService)
final envelopeServiceProvider = FutureProvider<EnvelopeService>.internal(
  envelopeService,
  name: r'envelopeServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$envelopeServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef EnvelopeServiceRef = FutureProviderRef<EnvelopeService>;
String _$envelopeStatusHash() => r'cb720b1f6799b243c32198d155a9a41b6b65cbbe';

/// See also [envelopeStatus].
@ProviderFor(envelopeStatus)
final envelopeStatusProvider =
    AutoDisposeFutureProvider<List<EnvelopeStatus>>.internal(
      envelopeStatus,
      name: r'envelopeStatusProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$envelopeStatusHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef EnvelopeStatusRef = AutoDisposeFutureProviderRef<List<EnvelopeStatus>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
