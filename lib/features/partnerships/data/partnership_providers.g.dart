// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'partnership_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$partnershipServiceHash() =>
    r'ecfa5442680d127ae219ae258750ca77253c6ca8';

/// See also [partnershipService].
@ProviderFor(partnershipService)
final partnershipServiceProvider = FutureProvider<PartnershipService>.internal(
  partnershipService,
  name: r'partnershipServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$partnershipServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef PartnershipServiceRef = FutureProviderRef<PartnershipService>;
String _$partnershipsHash() => r'abba78b621ee24ee53f588c087483d85658e371f';

/// Sherikliklar ro'yxati.
///
/// Copied from [partnerships].
@ProviderFor(partnerships)
final partnershipsProvider =
    AutoDisposeFutureProvider<List<Partnership>>.internal(
      partnerships,
      name: r'partnershipsProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$partnershipsHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef PartnershipsRef = AutoDisposeFutureProviderRef<List<Partnership>>;
String _$partnershipViewHash() => r'07a38f31f9a21e2cac63b6d09a0c2d365c792486';

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

/// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
///
/// Copied from [partnershipView].
@ProviderFor(partnershipView)
const partnershipViewProvider = PartnershipViewFamily();

/// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
///
/// Copied from [partnershipView].
class PartnershipViewFamily extends Family<AsyncValue<PartnershipView?>> {
  /// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
  ///
  /// Copied from [partnershipView].
  const PartnershipViewFamily();

  /// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
  ///
  /// Copied from [partnershipView].
  PartnershipViewProvider call(String id) {
    return PartnershipViewProvider(id);
  }

  @override
  PartnershipViewProvider getProviderOverride(
    covariant PartnershipViewProvider provider,
  ) {
    return call(provider.id);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'partnershipViewProvider';
}

/// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
///
/// Copied from [partnershipView].
class PartnershipViewProvider
    extends AutoDisposeFutureProvider<PartnershipView?> {
  /// Bitta sheriklik (shartnoma, imzolar, rozilik, buyout).
  ///
  /// Copied from [partnershipView].
  PartnershipViewProvider(String id)
    : this._internal(
        (ref) => partnershipView(ref as PartnershipViewRef, id),
        from: partnershipViewProvider,
        name: r'partnershipViewProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$partnershipViewHash,
        dependencies: PartnershipViewFamily._dependencies,
        allTransitiveDependencies:
            PartnershipViewFamily._allTransitiveDependencies,
        id: id,
      );

  PartnershipViewProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.id,
  }) : super.internal();

  final String id;

  @override
  Override overrideWith(
    FutureOr<PartnershipView?> Function(PartnershipViewRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: PartnershipViewProvider._internal(
        (ref) => create(ref as PartnershipViewRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        id: id,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<PartnershipView?> createElement() {
    return _PartnershipViewProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is PartnershipViewProvider && other.id == id;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, id.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin PartnershipViewRef on AutoDisposeFutureProviderRef<PartnershipView?> {
  /// The parameter `id` of this provider.
  String get id;
}

class _PartnershipViewProviderElement
    extends AutoDisposeFutureProviderElement<PartnershipView?>
    with PartnershipViewRef {
  _PartnershipViewProviderElement(super.provider);

  @override
  String get id => (origin as PartnershipViewProvider).id;
}

String _$ventureLedgerServiceHash() =>
    r'e8b3f087b8d5c11ebf20d65097f087abcd2c66b3';

/// See also [ventureLedgerService].
@ProviderFor(ventureLedgerService)
final ventureLedgerServiceProvider =
    FutureProvider<VentureLedgerService>.internal(
      ventureLedgerService,
      name: r'ventureLedgerServiceProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$ventureLedgerServiceHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef VentureLedgerServiceRef = FutureProviderRef<VentureLedgerService>;
String _$ledgerViewHash() => r'bd499cf30b6d4f186670888185ea031eb1a83534';

/// Sheriklik kassa daftari.
///
/// Copied from [ledgerView].
@ProviderFor(ledgerView)
const ledgerViewProvider = LedgerViewFamily();

/// Sheriklik kassa daftari.
///
/// Copied from [ledgerView].
class LedgerViewFamily extends Family<AsyncValue<LedgerView?>> {
  /// Sheriklik kassa daftari.
  ///
  /// Copied from [ledgerView].
  const LedgerViewFamily();

  /// Sheriklik kassa daftari.
  ///
  /// Copied from [ledgerView].
  LedgerViewProvider call(String partnershipId) {
    return LedgerViewProvider(partnershipId);
  }

  @override
  LedgerViewProvider getProviderOverride(
    covariant LedgerViewProvider provider,
  ) {
    return call(provider.partnershipId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'ledgerViewProvider';
}

/// Sheriklik kassa daftari.
///
/// Copied from [ledgerView].
class LedgerViewProvider extends AutoDisposeFutureProvider<LedgerView?> {
  /// Sheriklik kassa daftari.
  ///
  /// Copied from [ledgerView].
  LedgerViewProvider(String partnershipId)
    : this._internal(
        (ref) => ledgerView(ref as LedgerViewRef, partnershipId),
        from: ledgerViewProvider,
        name: r'ledgerViewProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$ledgerViewHash,
        dependencies: LedgerViewFamily._dependencies,
        allTransitiveDependencies: LedgerViewFamily._allTransitiveDependencies,
        partnershipId: partnershipId,
      );

  LedgerViewProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.partnershipId,
  }) : super.internal();

  final String partnershipId;

  @override
  Override overrideWith(
    FutureOr<LedgerView?> Function(LedgerViewRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: LedgerViewProvider._internal(
        (ref) => create(ref as LedgerViewRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        partnershipId: partnershipId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<LedgerView?> createElement() {
    return _LedgerViewProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is LedgerViewProvider && other.partnershipId == partnershipId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, partnershipId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin LedgerViewRef on AutoDisposeFutureProviderRef<LedgerView?> {
  /// The parameter `partnershipId` of this provider.
  String get partnershipId;
}

class _LedgerViewProviderElement
    extends AutoDisposeFutureProviderElement<LedgerView?>
    with LedgerViewRef {
  _LedgerViewProviderElement(super.provider);

  @override
  String get partnershipId => (origin as LedgerViewProvider).partnershipId;
}

String _$ideaServiceHash() => r'a704528817b0dc5b207fc88ce09294817f94933b';

/// See also [ideaService].
@ProviderFor(ideaService)
final ideaServiceProvider = FutureProvider<IdeaService>.internal(
  ideaService,
  name: r'ideaServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$ideaServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef IdeaServiceRef = FutureProviderRef<IdeaService>;
String _$ideasOverviewHash() => r'52493cfbdc88a7254cd97a168b9f1e44cfb3ec72';

/// «Hunardan ishga»: hunarlar va g'oyalar.
///
/// Copied from [ideasOverview].
@ProviderFor(ideasOverview)
final ideasOverviewProvider =
    AutoDisposeFutureProvider<(List<Skill>, List<IdeaView>)>.internal(
      ideasOverview,
      name: r'ideasOverviewProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$ideasOverviewHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef IdeasOverviewRef =
    AutoDisposeFutureProviderRef<(List<Skill>, List<IdeaView>)>;
String _$offerCheckServiceHash() => r'486a53a222228d792039865024f6dca115b38e53';

/// See also [offerCheckService].
@ProviderFor(offerCheckService)
final offerCheckServiceProvider = FutureProvider<OfferCheckService>.internal(
  offerCheckService,
  name: r'offerCheckServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$offerCheckServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef OfferCheckServiceRef = FutureProviderRef<OfferCheckService>;
String _$offerChecksHash() => r'0b382dc474f6df889d9e69a5671a39679cf21b3a';

/// Saqlangan taklif tekshiruvlari.
///
/// Copied from [offerChecks].
@ProviderFor(offerChecks)
final offerChecksProvider =
    AutoDisposeFutureProvider<List<OfferCheckRecord>>.internal(
      offerChecks,
      name: r'offerChecksProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$offerChecksHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef OfferChecksRef = AutoDisposeFutureProviderRef<List<OfferCheckRecord>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
