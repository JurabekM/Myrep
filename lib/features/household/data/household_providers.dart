import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'household_providers.g.dart';

@Riverpod(keepAlive: true)
Future<HouseholdService> householdService(Ref ref) async => HouseholdService(
  households: await ref.watch(householdRepositoryProvider.future),
  members: await ref.watch(memberRepositoryProvider.future),
  metaFactory: ref.watch(syncMetaFactoryProvider),
);

@Riverpod(keepAlive: true)
Future<MemberPinService> memberPinService(Ref ref) async => MemberPinService(
  pins: ref.watch(pinServiceProvider),
  members: await ref.watch(memberRepositoryProvider.future),
);
