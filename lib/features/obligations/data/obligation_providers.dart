import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'obligation_providers.g.dart';

@Riverpod(keepAlive: true)
ReminderApi reminderApi(Ref ref) => ReminderApi();

@Riverpod(keepAlive: true)
Future<ObligationService> obligationService(Ref ref) async => ObligationService(
  households: await ref.watch(householdRepositoryProvider.future),
  obligations: await ref.watch(obligationRepositoryProvider.future),
  debts: await ref.watch(debtRepositoryProvider.future),
  categories: await ref.watch(categoryRepositoryProvider.future),
  installments: await ref.watch(debtInstallmentRepositoryProvider.future),
  payments: await ref.watch(debtPaymentRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
  clock: ref.watch(clockProvider),
);
