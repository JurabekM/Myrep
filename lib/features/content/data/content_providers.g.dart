// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'content_providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$contentSourceHash() => r'16849d841bd7a9f7336195c6006e573e8a9f54f1';

/// Kontent manbasi (testlarda almashtiriladi). `ContentService` natijani
/// o'zi keshlaydi; bundle keshi o'chiq — keshlangan Future eski zonaga
/// bog'lanib qolmasin (testlarda ketma-ket osilish shundan edi).
///
/// Copied from [contentSource].
@ProviderFor(contentSource)
final contentSourceProvider = Provider<Future<String> Function()>.internal(
  contentSource,
  name: r'contentSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$contentSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef ContentSourceRef = ProviderRef<Future<String> Function()>;
String _$showPendingReligiousHash() =>
    r'bc18196bf61012e3b16e2e208774e1cf08da14cd';

/// Tasdiqlanmagan diniy bloklar faqat debug/profile'da (kontent tekshiruvi
/// uchun) ko'rinadi; release'da hech qachon (SPEC 3).
///
/// Copied from [showPendingReligious].
@ProviderFor(showPendingReligious)
final showPendingReligiousProvider = Provider<bool>.internal(
  showPendingReligious,
  name: r'showPendingReligiousProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$showPendingReligiousHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef ShowPendingReligiousRef = ProviderRef<bool>;
String _$contentServiceHash() => r'd57a65804d82cfbae279f16643f9d5d6e37ec453';

/// See also [contentService].
@ProviderFor(contentService)
final contentServiceProvider = FutureProvider<ContentService>.internal(
  contentService,
  name: r'contentServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$contentServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef ContentServiceRef = FutureProviderRef<ContentService>;
String _$chapterListHash() => r'82184001803fa84030a6523f1cde798e694636ad';

/// See also [chapterList].
@ProviderFor(chapterList)
final chapterListProvider =
    AutoDisposeFutureProvider<List<ChapterView>>.internal(
      chapterList,
      name: r'chapterListProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$chapterListHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef ChapterListRef = AutoDisposeFutureProviderRef<List<ChapterView>>;
String _$weekTasksHash() => r'78b21afff2e2c0abc1101872dbc40a830f084a1b';

/// See also [weekTasks].
@ProviderFor(weekTasks)
final weekTasksProvider = AutoDisposeFutureProvider<WeekTasks?>.internal(
  weekTasks,
  name: r'weekTasksProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$weekTasksHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef WeekTasksRef = AutoDisposeFutureProviderRef<WeekTasks?>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
