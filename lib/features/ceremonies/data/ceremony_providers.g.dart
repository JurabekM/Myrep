// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ceremony_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$ceremonyServiceHash() => r'591a30b5bdff51e97afe79c647b2bf9cffc5e99f';

/// See also [ceremonyService].
@ProviderFor(ceremonyService)
final ceremonyServiceProvider = FutureProvider<CeremonyService>.internal(
  ceremonyService,
  name: r'ceremonyServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$ceremonyServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef CeremonyServiceRef = FutureProviderRef<CeremonyService>;
String _$ceremonyPlansHash() => r'13fa3749897f7a4f3917706bca72f4e1e00f54f9';

/// Marosim rejalari ro'yxati.
///
/// Copied from [ceremonyPlans].
@ProviderFor(ceremonyPlans)
final ceremonyPlansProvider =
    AutoDisposeFutureProvider<List<CeremonyPlan>>.internal(
      ceremonyPlans,
      name: r'ceremonyPlansProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$ceremonyPlansHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef CeremonyPlansRef = AutoDisposeFutureProviderRef<List<CeremonyPlan>>;
String _$ceremonyViewHash() => r'2d4b4e041e9e2df430444c59f44bbedff8e9aa20';

/// Copied from Dart SDK
class _SystemHash {
  _SystemHash._();

  static int combine(int hash, int value) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + value);
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x0007ffff & hash) << 10));
    return hash ^ (hash >> 6);
  }

  static int finish(int hash) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x03ffffff & hash) << 3));
    // ignore: parameter_assignments
    hash = hash ^ (hash >> 11);
    return 0x1fffffff & (hash + ((0x00003fff & hash) << 15));
  }
}

/// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
///
/// Copied from [ceremonyView].
@ProviderFor(ceremonyView)
const ceremonyViewProvider = CeremonyViewFamily();

/// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
///
/// Copied from [ceremonyView].
class CeremonyViewFamily extends Family<AsyncValue<CeremonyView?>> {
  /// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
  ///
  /// Copied from [ceremonyView].
  const CeremonyViewFamily();

  /// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
  ///
  /// Copied from [ceremonyView].
  CeremonyViewProvider call(String planId) {
    return CeremonyViewProvider(planId);
  }

  @override
  CeremonyViewProvider getProviderOverride(
    covariant CeremonyViewProvider provider,
  ) {
    return call(provider.planId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'ceremonyViewProvider';
}

/// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
///
/// Copied from [ceremonyView].
class CeremonyViewProvider extends AutoDisposeFutureProvider<CeremonyView?> {
  /// Bitta reja (taqqoslash, muhokama, to'yona jamg'armasi).
  ///
  /// Copied from [ceremonyView].
  CeremonyViewProvider(String planId)
    : this._internal(
        (ref) => ceremonyView(ref as CeremonyViewRef, planId),
        from: ceremonyViewProvider,
        name: r'ceremonyViewProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$ceremonyViewHash,
        dependencies: CeremonyViewFamily._dependencies,
        allTransitiveDependencies:
            CeremonyViewFamily._allTransitiveDependencies,
        planId: planId,
      );

  CeremonyViewProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.planId,
  }) : super.internal();

  final String planId;

  @override
  Override overrideWith(
    FutureOr<CeremonyView?> Function(CeremonyViewRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CeremonyViewProvider._internal(
        (ref) => create(ref as CeremonyViewRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        planId: planId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<CeremonyView?> createElement() {
    return _CeremonyViewProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CeremonyViewProvider && other.planId == planId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, planId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin CeremonyViewRef on AutoDisposeFutureProviderRef<CeremonyView?> {
  /// The parameter `planId` of this provider.
  String get planId;
}

class _CeremonyViewProviderElement
    extends AutoDisposeFutureProviderElement<CeremonyView?>
    with CeremonyViewRef {
  _CeremonyViewProviderElement(super.provider);

  @override
  String get planId => (origin as CeremonyViewProvider).planId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
