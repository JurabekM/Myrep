import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/budget/data/drift_budget_repositories.dart';
import 'package:baraka_daftari/features/envelopes/data/drift_envelope_repositories.dart';
import 'package:baraka_daftari/features/envelopes/domain/envelope_service.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'envelope_providers.g.dart';

@Riverpod(keepAlive: true)
Future<EnvelopeService> envelopeService(Ref ref) async => EnvelopeService(
  households: await ref.watch(householdRepositoryProvider.future),
  envelopes: await ref.watch(envelopeRepositoryProvider.future),
  periods: await ref.watch(envelopePeriodRepositoryProvider.future),
  expenses: await ref.watch(expenseRepositoryProvider.future),
  rescues: await ref.watch(savingsRescueRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);

@riverpod
Future<List<EnvelopeStatus>> envelopeStatus(Ref ref) async =>
    (await ref.watch(envelopeServiceProvider.future)).status();
