// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'whose_money_screen.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$whoseMoneyDataHash() => r'f8594e84097370d27d54be146e37b1c328dfd41a';

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

/// [offset] — joriy oydan necha oy oldin (0 — shu oy).
///
/// Copied from [whoseMoneyData].
@ProviderFor(whoseMoneyData)
const whoseMoneyDataProvider = WhoseMoneyDataFamily();

/// [offset] — joriy oydan necha oy oldin (0 — shu oy).
///
/// Copied from [whoseMoneyData].
class WhoseMoneyDataFamily extends Family<AsyncValue<WhoseData>> {
  /// [offset] — joriy oydan necha oy oldin (0 — shu oy).
  ///
  /// Copied from [whoseMoneyData].
  const WhoseMoneyDataFamily();

  /// [offset] — joriy oydan necha oy oldin (0 — shu oy).
  ///
  /// Copied from [whoseMoneyData].
  WhoseMoneyDataProvider call(int offset) {
    return WhoseMoneyDataProvider(offset);
  }

  @override
  WhoseMoneyDataProvider getProviderOverride(
    covariant WhoseMoneyDataProvider provider,
  ) {
    return call(provider.offset);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'whoseMoneyDataProvider';
}

/// [offset] — joriy oydan necha oy oldin (0 — shu oy).
///
/// Copied from [whoseMoneyData].
class WhoseMoneyDataProvider extends AutoDisposeFutureProvider<WhoseData> {
  /// [offset] — joriy oydan necha oy oldin (0 — shu oy).
  ///
  /// Copied from [whoseMoneyData].
  WhoseMoneyDataProvider(int offset)
    : this._internal(
        (ref) => whoseMoneyData(ref as WhoseMoneyDataRef, offset),
        from: whoseMoneyDataProvider,
        name: r'whoseMoneyDataProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$whoseMoneyDataHash,
        dependencies: WhoseMoneyDataFamily._dependencies,
        allTransitiveDependencies:
            WhoseMoneyDataFamily._allTransitiveDependencies,
        offset: offset,
      );

  WhoseMoneyDataProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.offset,
  }) : super.internal();

  final int offset;

  @override
  Override overrideWith(
    FutureOr<WhoseData> Function(WhoseMoneyDataRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: WhoseMoneyDataProvider._internal(
        (ref) => create(ref as WhoseMoneyDataRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        offset: offset,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<WhoseData> createElement() {
    return _WhoseMoneyDataProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is WhoseMoneyDataProvider && other.offset == offset;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, offset.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin WhoseMoneyDataRef on AutoDisposeFutureProviderRef<WhoseData> {
  /// The parameter `offset` of this provider.
  int get offset;
}

class _WhoseMoneyDataProviderElement
    extends AutoDisposeFutureProviderElement<WhoseData>
    with WhoseMoneyDataRef {
  _WhoseMoneyDataProviderElement(super.provider);

  @override
  int get offset => (origin as WhoseMoneyDataProvider).offset;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
