// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'integrity_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$integrityLogHash() => r'b2f1bda6217cb53aba74d5d6ad5880f71adf9914';

/// See also [integrityLog].
@ProviderFor(integrityLog)
final integrityLogProvider = Provider<IntegrityLog>.internal(
  integrityLog,
  name: r'integrityLogProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$integrityLogHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef IntegrityLogRef = ProviderRef<IntegrityLog>;
String _$integrityRisksHash() => r'dcbe5095fe3df830bf0cd48e0085a61b2bf1fdee';

/// Ilova ishga tushganda bir marta tekshiriladi. Xato bo'lsa — xavf yo'q deb
/// emas, shunchaki bo'sh natija (ilova bloklanmaydi).
///
/// Copied from [integrityRisks].
@ProviderFor(integrityRisks)
final integrityRisksProvider = FutureProvider<Set<IntegrityRisk>>.internal(
  integrityRisks,
  name: r'integrityRisksProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$integrityRisksHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef IntegrityRisksRef = FutureProviderRef<Set<IntegrityRisk>>;
String _$integrityWarningDismissedHash() =>
    r'05852030df2c2a37d0eb48f9ed936a34ae3bdbbd';

/// Foydalanuvchi ogohlantirishni shu sessiyada yopdimi.
///
/// Copied from [IntegrityWarningDismissed].
@ProviderFor(IntegrityWarningDismissed)
final integrityWarningDismissedProvider =
    NotifierProvider<IntegrityWarningDismissed, bool>.internal(
      IntegrityWarningDismissed.new,
      name: r'integrityWarningDismissedProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$integrityWarningDismissedHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$IntegrityWarningDismissed = Notifier<bool>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
