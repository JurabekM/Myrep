// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chapter_screen.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$chapterByIdHash() => r'623bf80c580d2f081d77bd09d18ff64f6abe43e2';

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

/// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
///
/// Copied from [chapterById].
@ProviderFor(chapterById)
const chapterByIdProvider = ChapterByIdFamily();

/// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
///
/// Copied from [chapterById].
class ChapterByIdFamily extends Family<AsyncValue<Chapter?>> {
  /// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
  ///
  /// Copied from [chapterById].
  const ChapterByIdFamily();

  /// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
  ///
  /// Copied from [chapterById].
  ChapterByIdProvider call(String id) {
    return ChapterByIdProvider(id);
  }

  @override
  ChapterByIdProvider getProviderOverride(
    covariant ChapterByIdProvider provider,
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
  String? get name => r'chapterByIdProvider';
}

/// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
///
/// Copied from [chapterById].
class ChapterByIdProvider extends AutoDisposeFutureProvider<Chapter?> {
  /// Ochiq bob (yopiq yoki mavjud bo'lmasa — `null`).
  ///
  /// Copied from [chapterById].
  ChapterByIdProvider(String id)
    : this._internal(
        (ref) => chapterById(ref as ChapterByIdRef, id),
        from: chapterByIdProvider,
        name: r'chapterByIdProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$chapterByIdHash,
        dependencies: ChapterByIdFamily._dependencies,
        allTransitiveDependencies: ChapterByIdFamily._allTransitiveDependencies,
        id: id,
      );

  ChapterByIdProvider._internal(
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
    FutureOr<Chapter?> Function(ChapterByIdRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: ChapterByIdProvider._internal(
        (ref) => create(ref as ChapterByIdRef),
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
  AutoDisposeFutureProviderElement<Chapter?> createElement() {
    return _ChapterByIdProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is ChapterByIdProvider && other.id == id;
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
mixin ChapterByIdRef on AutoDisposeFutureProviderRef<Chapter?> {
  /// The parameter `id` of this provider.
  String get id;
}

class _ChapterByIdProviderElement
    extends AutoDisposeFutureProviderElement<Chapter?>
    with ChapterByIdRef {
  _ChapterByIdProviderElement(super.provider);

  @override
  String get id => (origin as ChapterByIdProvider).id;
}

String _$hasDaftarPageHash() => r'9b2ce926edc0f35da0274e89d2c008be2102b526';

/// See also [hasDaftarPage].
@ProviderFor(hasDaftarPage)
const hasDaftarPageProvider = HasDaftarPageFamily();

/// See also [hasDaftarPage].
class HasDaftarPageFamily extends Family<AsyncValue<bool>> {
  /// See also [hasDaftarPage].
  const HasDaftarPageFamily();

  /// See also [hasDaftarPage].
  HasDaftarPageProvider call(String chapterId) {
    return HasDaftarPageProvider(chapterId);
  }

  @override
  HasDaftarPageProvider getProviderOverride(
    covariant HasDaftarPageProvider provider,
  ) {
    return call(provider.chapterId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'hasDaftarPageProvider';
}

/// See also [hasDaftarPage].
class HasDaftarPageProvider extends AutoDisposeFutureProvider<bool> {
  /// See also [hasDaftarPage].
  HasDaftarPageProvider(String chapterId)
    : this._internal(
        (ref) => hasDaftarPage(ref as HasDaftarPageRef, chapterId),
        from: hasDaftarPageProvider,
        name: r'hasDaftarPageProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$hasDaftarPageHash,
        dependencies: HasDaftarPageFamily._dependencies,
        allTransitiveDependencies:
            HasDaftarPageFamily._allTransitiveDependencies,
        chapterId: chapterId,
      );

  HasDaftarPageProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.chapterId,
  }) : super.internal();

  final String chapterId;

  @override
  Override overrideWith(
    FutureOr<bool> Function(HasDaftarPageRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: HasDaftarPageProvider._internal(
        (ref) => create(ref as HasDaftarPageRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        chapterId: chapterId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<bool> createElement() {
    return _HasDaftarPageProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is HasDaftarPageProvider && other.chapterId == chapterId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, chapterId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin HasDaftarPageRef on AutoDisposeFutureProviderRef<bool> {
  /// The parameter `chapterId` of this provider.
  String get chapterId;
}

class _HasDaftarPageProviderElement
    extends AutoDisposeFutureProviderElement<bool>
    with HasDaftarPageRef {
  _HasDaftarPageProviderElement(super.provider);

  @override
  String get chapterId => (origin as HasDaftarPageProvider).chapterId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
