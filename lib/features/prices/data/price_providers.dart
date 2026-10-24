import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/prices/data/drift_price_repositories.dart';
import 'package:baraka_daftari/features/prices/domain/price_book_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'price_providers.g.dart';

@Riverpod(keepAlive: true)
Future<PriceBookService> priceBookService(Ref ref) async => PriceBookService(
  households: await ref.watch(householdRepositoryProvider.future),
  items: await ref.watch(priceItemRepositoryProvider.future),
  points: await ref.watch(pricePointRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

@riverpod
Future<PriceBookOverview> priceBook(Ref ref) async =>
    (await ref.watch(priceBookServiceProvider.future)).overview();
