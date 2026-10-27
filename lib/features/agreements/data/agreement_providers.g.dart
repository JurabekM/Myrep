// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agreement_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$agreementRepositoryHash() =>
    r'819f5a3cba507ff2a604b73a41091af7d4957670';

/// See also [agreementRepository].
@ProviderFor(agreementRepository)
final agreementRepositoryProvider =
    FutureProvider<AgreementRepository>.internal(
      agreementRepository,
      name: r'agreementRepositoryProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$agreementRepositoryHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AgreementRepositoryRef = FutureProviderRef<AgreementRepository>;
String _$agreementVersionRepositoryHash() =>
    r'1298411a8344e9c5c535189c1da214bc9ea7c4c9';

/// See also [agreementVersionRepository].
@ProviderFor(agreementVersionRepository)
final agreementVersionRepositoryProvider =
    FutureProvider<AgreementVersionRepository>.internal(
      agreementVersionRepository,
      name: r'agreementVersionRepositoryProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$agreementVersionRepositoryHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AgreementVersionRepositoryRef =
    FutureProviderRef<AgreementVersionRepository>;
String _$journalRepositoryHash() => r'f06d561f01fc3dc74533e9279a8f73c4823d48d4';

/// See also [journalRepository].
@ProviderFor(journalRepository)
final journalRepositoryProvider = FutureProvider<JournalRepository>.internal(
  journalRepository,
  name: r'journalRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$journalRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef JournalRepositoryRef = FutureProviderRef<JournalRepository>;
String _$agreementServiceHash() => r'e7dca0084146decfc8fd9d2083e3de703e3bc61a';

/// See also [agreementService].
@ProviderFor(agreementService)
final agreementServiceProvider = FutureProvider<AgreementService>.internal(
  agreementService,
  name: r'agreementServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$agreementServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AgreementServiceRef = FutureProviderRef<AgreementService>;
String _$agreementsHash() => r'b67ab5f966847b9a78dbc330c671995a6c729784';

/// Kelishuvlar ro'yxati.
///
/// Copied from [agreements].
@ProviderFor(agreements)
final agreementsProvider = AutoDisposeFutureProvider<List<Agreement>>.internal(
  agreements,
  name: r'agreementsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$agreementsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AgreementsRef = AutoDisposeFutureProviderRef<List<Agreement>>;
String _$agreementViewHash() => r'85583b4649b19f1f37d5dec9c28588463b285844';

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

/// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
///
/// Copied from [agreementView].
@ProviderFor(agreementView)
const agreementViewProvider = AgreementViewFamily();

/// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
///
/// Copied from [agreementView].
class AgreementViewFamily extends Family<AsyncValue<AgreementView?>> {
  /// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
  ///
  /// Copied from [agreementView].
  const AgreementViewFamily();

  /// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
  ///
  /// Copied from [agreementView].
  AgreementViewProvider call(String id) {
    return AgreementViewProvider(id);
  }

  @override
  AgreementViewProvider getProviderOverride(
    covariant AgreementViewProvider provider,
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
  String? get name => r'agreementViewProvider';
}

/// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
///
/// Copied from [agreementView].
class AgreementViewProvider extends AutoDisposeFutureProvider<AgreementView?> {
  /// Bitta kelishuv (javoblar, to'liqlik, imzolar, jurnal).
  ///
  /// Copied from [agreementView].
  AgreementViewProvider(String id)
    : this._internal(
        (ref) => agreementView(ref as AgreementViewRef, id),
        from: agreementViewProvider,
        name: r'agreementViewProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$agreementViewHash,
        dependencies: AgreementViewFamily._dependencies,
        allTransitiveDependencies:
            AgreementViewFamily._allTransitiveDependencies,
        id: id,
      );

  AgreementViewProvider._internal(
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
    FutureOr<AgreementView?> Function(AgreementViewRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AgreementViewProvider._internal(
        (ref) => create(ref as AgreementViewRef),
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
  AutoDisposeFutureProviderElement<AgreementView?> createElement() {
    return _AgreementViewProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AgreementViewProvider && other.id == id;
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
mixin AgreementViewRef on AutoDisposeFutureProviderRef<AgreementView?> {
  /// The parameter `id` of this provider.
  String get id;
}

class _AgreementViewProviderElement
    extends AutoDisposeFutureProviderElement<AgreementView?>
    with AgreementViewRef {
  _AgreementViewProviderElement(super.provider);

  @override
  String get id => (origin as AgreementViewProvider).id;
}

String _$agreementBySourceHash() => r'99f05fe4732ecf013045be7f049bbf2e8abc6a72';

/// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
///
/// Copied from [agreementBySource].
@ProviderFor(agreementBySource)
const agreementBySourceProvider = AgreementBySourceFamily();

/// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
///
/// Copied from [agreementBySource].
class AgreementBySourceFamily extends Family<AsyncValue<AgreementView?>> {
  /// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
  ///
  /// Copied from [agreementBySource].
  const AgreementBySourceFamily();

  /// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
  ///
  /// Copied from [agreementBySource].
  AgreementBySourceProvider call(AgreementSource source, String sourceId) {
    return AgreementBySourceProvider(source, sourceId);
  }

  @override
  AgreementBySourceProvider getProviderOverride(
    covariant AgreementBySourceProvider provider,
  ) {
    return call(provider.source, provider.sourceId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'agreementBySourceProvider';
}

/// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
///
/// Copied from [agreementBySource].
class AgreementBySourceProvider
    extends AutoDisposeFutureProvider<AgreementView?> {
  /// Modul yozuviga (qarz, sheriklik) bog'langan kelishuv.
  ///
  /// Copied from [agreementBySource].
  AgreementBySourceProvider(AgreementSource source, String sourceId)
    : this._internal(
        (ref) =>
            agreementBySource(ref as AgreementBySourceRef, source, sourceId),
        from: agreementBySourceProvider,
        name: r'agreementBySourceProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$agreementBySourceHash,
        dependencies: AgreementBySourceFamily._dependencies,
        allTransitiveDependencies:
            AgreementBySourceFamily._allTransitiveDependencies,
        source: source,
        sourceId: sourceId,
      );

  AgreementBySourceProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.source,
    required this.sourceId,
  }) : super.internal();

  final AgreementSource source;
  final String sourceId;

  @override
  Override overrideWith(
    FutureOr<AgreementView?> Function(AgreementBySourceRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AgreementBySourceProvider._internal(
        (ref) => create(ref as AgreementBySourceRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        source: source,
        sourceId: sourceId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<AgreementView?> createElement() {
    return _AgreementBySourceProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AgreementBySourceProvider &&
        other.source == source &&
        other.sourceId == sourceId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, source.hashCode);
    hash = _SystemHash.combine(hash, sourceId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AgreementBySourceRef on AutoDisposeFutureProviderRef<AgreementView?> {
  /// The parameter `source` of this provider.
  AgreementSource get source;

  /// The parameter `sourceId` of this provider.
  String get sourceId;
}

class _AgreementBySourceProviderElement
    extends AutoDisposeFutureProviderElement<AgreementView?>
    with AgreementBySourceRef {
  _AgreementBySourceProviderElement(super.provider);

  @override
  AgreementSource get source => (origin as AgreementBySourceProvider).source;
  @override
  String get sourceId => (origin as AgreementBySourceProvider).sourceId;
}

String _$accountabilityServiceHash() =>
    r'3bd86b70549e9ffc069ec3faee40481825dfbffe';

/// Ko'rik, hodisa va nizo amallari (SPEC 2F.4–2F.8).
///
/// Copied from [accountabilityService].
@ProviderFor(accountabilityService)
final accountabilityServiceProvider =
    FutureProvider<AccountabilityService>.internal(
      accountabilityService,
      name: r'accountabilityServiceProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$accountabilityServiceHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AccountabilityServiceRef = FutureProviderRef<AccountabilityService>;
String _$accountabilityViewHash() =>
    r'ca8b5f129504113cff9923f5400b332df2631e8e';

/// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
///
/// Copied from [accountabilityView].
@ProviderFor(accountabilityView)
const accountabilityViewProvider = AccountabilityViewFamily();

/// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
///
/// Copied from [accountabilityView].
class AccountabilityViewFamily extends Family<AsyncValue<AccountabilityView?>> {
  /// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
  ///
  /// Copied from [accountabilityView].
  const AccountabilityViewFamily();

  /// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
  ///
  /// Copied from [accountabilityView].
  AccountabilityViewProvider call(String id) {
    return AccountabilityViewProvider(id);
  }

  @override
  AccountabilityViewProvider getProviderOverride(
    covariant AccountabilityViewProvider provider,
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
  String? get name => r'accountabilityViewProvider';
}

/// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
///
/// Copied from [accountabilityView].
class AccountabilityViewProvider
    extends AutoDisposeFutureProvider<AccountabilityView?> {
  /// Bitta kelishuvning kengaytirilgan ko'rinishi (ko'rik, nizolar).
  ///
  /// Copied from [accountabilityView].
  AccountabilityViewProvider(String id)
    : this._internal(
        (ref) => accountabilityView(ref as AccountabilityViewRef, id),
        from: accountabilityViewProvider,
        name: r'accountabilityViewProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$accountabilityViewHash,
        dependencies: AccountabilityViewFamily._dependencies,
        allTransitiveDependencies:
            AccountabilityViewFamily._allTransitiveDependencies,
        id: id,
      );

  AccountabilityViewProvider._internal(
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
    FutureOr<AccountabilityView?> Function(AccountabilityViewRef provider)
    create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AccountabilityViewProvider._internal(
        (ref) => create(ref as AccountabilityViewRef),
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
  AutoDisposeFutureProviderElement<AccountabilityView?> createElement() {
    return _AccountabilityViewProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AccountabilityViewProvider && other.id == id;
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
mixin AccountabilityViewRef
    on AutoDisposeFutureProviderRef<AccountabilityView?> {
  /// The parameter `id` of this provider.
  String get id;
}

class _AccountabilityViewProviderElement
    extends AutoDisposeFutureProviderElement<AccountabilityView?>
    with AccountabilityViewRef {
  _AccountabilityViewProviderElement(super.provider);

  @override
  String get id => (origin as AccountabilityViewProvider).id;
}

String _$agreementCenterHash() => r'8045ab893223e3ee57711dd56954d40e5da6fc5c';

/// Kelishuvlar markazi: hamma kelishuvlar, ko'rik va nizo holati bilan.
///
/// Copied from [agreementCenter].
@ProviderFor(agreementCenter)
final agreementCenterProvider =
    AutoDisposeFutureProvider<List<AccountabilityView>>.internal(
      agreementCenter,
      name: r'agreementCenterProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$agreementCenterHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AgreementCenterRef =
    AutoDisposeFutureProviderRef<List<AccountabilityView>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
