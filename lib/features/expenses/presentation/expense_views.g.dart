// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'expense_views.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$monthExpensesHash() => r'37b7026d09fc60728aeb6e480077a109f8179a94';

/// Joriy oy (oylik kuni bo'yicha) xarajatlari, eng yangisi birinchi.
///
/// Copied from [monthExpenses].
@ProviderFor(monthExpenses)
final monthExpensesProvider = AutoDisposeFutureProvider<List<Expense>>.internal(
  monthExpenses,
  name: r'monthExpensesProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$monthExpensesHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef MonthExpensesRef = AutoDisposeFutureProviderRef<List<Expense>>;
String _$expenseCategoriesHash() => r'50e0a25063ef146f65e5f158313b8495bcab1f9b';

/// See also [expenseCategories].
@ProviderFor(expenseCategories)
final expenseCategoriesProvider =
    AutoDisposeFutureProvider<List<Category>>.internal(
      expenseCategories,
      name: r'expenseCategoriesProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$expenseCategoriesHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef ExpenseCategoriesRef = AutoDisposeFutureProviderRef<List<Category>>;
String _$expenseTemplatesHash() => r'835f6b237db391e0c0ca708c726cac37b786da44';

/// See also [expenseTemplates].
@ProviderFor(expenseTemplates)
final expenseTemplatesProvider =
    AutoDisposeFutureProvider<List<ExpenseTemplate>>.internal(
      expenseTemplates,
      name: r'expenseTemplatesProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$expenseTemplatesHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef ExpenseTemplatesRef =
    AutoDisposeFutureProviderRef<List<ExpenseTemplate>>;
String _$latestExpenseHash() => r'4fa15dac9b4794bda08a2a76c9da7fb399909c51';

/// See also [latestExpense].
@ProviderFor(latestExpense)
final latestExpenseProvider = AutoDisposeFutureProvider<Expense?>.internal(
  latestExpense,
  name: r'latestExpenseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$latestExpenseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef LatestExpenseRef = AutoDisposeFutureProviderRef<Expense?>;
String _$necessityHistoryHash() => r'81fd793832668b1454a1a8057971bcfc663cb06a';

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

/// See also [necessityHistory].
@ProviderFor(necessityHistory)
const necessityHistoryProvider = NecessityHistoryFamily();

/// See also [necessityHistory].
class NecessityHistoryFamily extends Family<AsyncValue<List<NecessityChange>>> {
  /// See also [necessityHistory].
  const NecessityHistoryFamily();

  /// See also [necessityHistory].
  NecessityHistoryProvider call(String categoryId) {
    return NecessityHistoryProvider(categoryId);
  }

  @override
  NecessityHistoryProvider getProviderOverride(
    covariant NecessityHistoryProvider provider,
  ) {
    return call(provider.categoryId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'necessityHistoryProvider';
}

/// See also [necessityHistory].
class NecessityHistoryProvider
    extends AutoDisposeFutureProvider<List<NecessityChange>> {
  /// See also [necessityHistory].
  NecessityHistoryProvider(String categoryId)
    : this._internal(
        (ref) => necessityHistory(ref as NecessityHistoryRef, categoryId),
        from: necessityHistoryProvider,
        name: r'necessityHistoryProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$necessityHistoryHash,
        dependencies: NecessityHistoryFamily._dependencies,
        allTransitiveDependencies:
            NecessityHistoryFamily._allTransitiveDependencies,
        categoryId: categoryId,
      );

  NecessityHistoryProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.categoryId,
  }) : super.internal();

  final String categoryId;

  @override
  Override overrideWith(
    FutureOr<List<NecessityChange>> Function(NecessityHistoryRef provider)
    create,
  ) {
    return ProviderOverride(
      origin: this,
      override: NecessityHistoryProvider._internal(
        (ref) => create(ref as NecessityHistoryRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        categoryId: categoryId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<List<NecessityChange>> createElement() {
    return _NecessityHistoryProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is NecessityHistoryProvider && other.categoryId == categoryId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, categoryId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin NecessityHistoryRef
    on AutoDisposeFutureProviderRef<List<NecessityChange>> {
  /// The parameter `categoryId` of this provider.
  String get categoryId;
}

class _NecessityHistoryProviderElement
    extends AutoDisposeFutureProviderElement<List<NecessityChange>>
    with NecessityHistoryRef {
  _NecessityHistoryProviderElement(super.provider);

  @override
  String get categoryId => (origin as NecessityHistoryProvider).categoryId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
