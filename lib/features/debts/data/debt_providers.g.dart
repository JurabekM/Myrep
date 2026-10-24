// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'debt_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$debtServiceHash() => r'7c994ed91153b41e0538c207d217e0b54202b7dd';

/// See also [debtService].
@ProviderFor(debtService)
final debtServiceProvider = FutureProvider<DebtService>.internal(
  debtService,
  name: r'debtServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$debtServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef DebtServiceRef = FutureProviderRef<DebtService>;
String _$debtOverviewHash() => r'cf5e1b32023219009f79c7861caed4b9de01057f';

/// See also [debtOverview].
@ProviderFor(debtOverview)
final debtOverviewProvider = AutoDisposeFutureProvider<DebtOverview>.internal(
  debtOverview,
  name: r'debtOverviewProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$debtOverviewHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef DebtOverviewRef = AutoDisposeFutureProviderRef<DebtOverview>;
String _$loanReceiptServiceHash() =>
    r'6f852b51be59c7f1a49d19ab252171c1467e5fc8';

/// See also [loanReceiptService].
@ProviderFor(loanReceiptService)
final loanReceiptServiceProvider = FutureProvider<LoanReceiptService>.internal(
  loanReceiptService,
  name: r'loanReceiptServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$loanReceiptServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef LoanReceiptServiceRef = FutureProviderRef<LoanReceiptService>;
String _$debtViewHash() => r'802635d78a1919e837e9cdb79556ceef44142eef';

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

/// Bitta qarz (tafsilot ekrani).
///
/// Copied from [debtView].
@ProviderFor(debtView)
const debtViewProvider = DebtViewFamily();

/// Bitta qarz (tafsilot ekrani).
///
/// Copied from [debtView].
class DebtViewFamily extends Family<AsyncValue<DebtView?>> {
  /// Bitta qarz (tafsilot ekrani).
  ///
  /// Copied from [debtView].
  const DebtViewFamily();

  /// Bitta qarz (tafsilot ekrani).
  ///
  /// Copied from [debtView].
  DebtViewProvider call(String debtId) {
    return DebtViewProvider(debtId);
  }

  @override
  DebtViewProvider getProviderOverride(covariant DebtViewProvider provider) {
    return call(provider.debtId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'debtViewProvider';
}

/// Bitta qarz (tafsilot ekrani).
///
/// Copied from [debtView].
class DebtViewProvider extends AutoDisposeFutureProvider<DebtView?> {
  /// Bitta qarz (tafsilot ekrani).
  ///
  /// Copied from [debtView].
  DebtViewProvider(String debtId)
    : this._internal(
        (ref) => debtView(ref as DebtViewRef, debtId),
        from: debtViewProvider,
        name: r'debtViewProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$debtViewHash,
        dependencies: DebtViewFamily._dependencies,
        allTransitiveDependencies: DebtViewFamily._allTransitiveDependencies,
        debtId: debtId,
      );

  DebtViewProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.debtId,
  }) : super.internal();

  final String debtId;

  @override
  Override overrideWith(
    FutureOr<DebtView?> Function(DebtViewRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: DebtViewProvider._internal(
        (ref) => create(ref as DebtViewRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        debtId: debtId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<DebtView?> createElement() {
    return _DebtViewProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is DebtViewProvider && other.debtId == debtId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, debtId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin DebtViewRef on AutoDisposeFutureProviderRef<DebtView?> {
  /// The parameter `debtId` of this provider.
  String get debtId;
}

class _DebtViewProviderElement
    extends AutoDisposeFutureProviderElement<DebtView?>
    with DebtViewRef {
  _DebtViewProviderElement(super.provider);

  @override
  String get debtId => (origin as DebtViewProvider).debtId;
}

String _$receivableHash() => r'db907550fa3735652fc26e30b6c82bf0f733fe1d';

/// Bitta bergan qarz (tilxat uchun).
///
/// Copied from [receivable].
@ProviderFor(receivable)
const receivableProvider = ReceivableFamily();

/// Bitta bergan qarz (tilxat uchun).
///
/// Copied from [receivable].
class ReceivableFamily extends Family<AsyncValue<Receivable?>> {
  /// Bitta bergan qarz (tilxat uchun).
  ///
  /// Copied from [receivable].
  const ReceivableFamily();

  /// Bitta bergan qarz (tilxat uchun).
  ///
  /// Copied from [receivable].
  ReceivableProvider call(String id) {
    return ReceivableProvider(id);
  }

  @override
  ReceivableProvider getProviderOverride(
    covariant ReceivableProvider provider,
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
  String? get name => r'receivableProvider';
}

/// Bitta bergan qarz (tilxat uchun).
///
/// Copied from [receivable].
class ReceivableProvider extends AutoDisposeFutureProvider<Receivable?> {
  /// Bitta bergan qarz (tilxat uchun).
  ///
  /// Copied from [receivable].
  ReceivableProvider(String id)
    : this._internal(
        (ref) => receivable(ref as ReceivableRef, id),
        from: receivableProvider,
        name: r'receivableProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$receivableHash,
        dependencies: ReceivableFamily._dependencies,
        allTransitiveDependencies: ReceivableFamily._allTransitiveDependencies,
        id: id,
      );

  ReceivableProvider._internal(
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
    FutureOr<Receivable?> Function(ReceivableRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: ReceivableProvider._internal(
        (ref) => create(ref as ReceivableRef),
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
  AutoDisposeFutureProviderElement<Receivable?> createElement() {
    return _ReceivableProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is ReceivableProvider && other.id == id;
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
mixin ReceivableRef on AutoDisposeFutureProviderRef<Receivable?> {
  /// The parameter `id` of this provider.
  String get id;
}

class _ReceivableProviderElement
    extends AutoDisposeFutureProviderElement<Receivable?>
    with ReceivableRef {
  _ReceivableProviderElement(super.provider);

  @override
  String get id => (origin as ReceivableProvider).id;
}

String _$recoveryServiceHash() => r'f19e5d88c5e2c2a960c2e502e30b3d2420b03852';

/// See also [recoveryService].
@ProviderFor(recoveryService)
final recoveryServiceProvider = FutureProvider<RecoveryService>.internal(
  recoveryService,
  name: r'recoveryServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$recoveryServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef RecoveryServiceRef = FutureProviderRef<RecoveryService>;
String _$recoveryStateHash() => r'b2635d56cbbbe76edd8ef240d64be008c009b1c2';

/// «Qarzdan chiqish» rejimi holati (SPEC 2D.1).
///
/// Copied from [recoveryState].
@ProviderFor(recoveryState)
final recoveryStateProvider = AutoDisposeFutureProvider<RecoveryState>.internal(
  recoveryState,
  name: r'recoveryStateProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$recoveryStateHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef RecoveryStateRef = AutoDisposeFutureProviderRef<RecoveryState>;
String _$sellablesHash() => r'0cf6af5d30d1c96d54954319cfb10900fed355b2';

/// Sotiladigan buyumlar (SPEC 2D.7).
///
/// Copied from [sellables].
@ProviderFor(sellables)
final sellablesProvider =
    AutoDisposeFutureProvider<List<SellableItem>>.internal(
      sellables,
      name: r'sellablesProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$sellablesHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SellablesRef = AutoDisposeFutureProviderRef<List<SellableItem>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
