// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$databaseFileHash() => r'c0aa5f368bfb4213b4691d1481e0128e11688e3f';

/// Baza fayli: `<app support>/db/baraka.sqlite` (backup'dan chiqarilgan).
///
/// Copied from [databaseFile].
@ProviderFor(databaseFile)
final databaseFileProvider = FutureProvider<File>.internal(
  databaseFile,
  name: r'databaseFileProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$databaseFileHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef DatabaseFileRef = FutureProviderRef<File>;
String _$appDatabaseHash() => r'bcf0b7f1f52211f2ec2c09dcc3e271aca0a3c6fb';

/// Shifrlangan baza. Kalit Kotlin'dan (Keystore bilan wrap qilingan)
/// olinadi va baza ochilgach xotiradagi nusxasi tozalanadi.
///
/// Copied from [appDatabase].
@ProviderFor(appDatabase)
final appDatabaseProvider = FutureProvider<AppDatabase>.internal(
  appDatabase,
  name: r'appDatabaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$appDatabaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AppDatabaseRef = FutureProviderRef<AppDatabase>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
