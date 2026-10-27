import 'package:zanjir_core/zanjir_core.dart';

import 'audit_repository.dart';
import 'context.dart';
import 'graph_repository.dart';
import 'instrument_repository.dart';
import 'isolation_plan_repository.dart';
import 'measurement_repository.dart';
import 'norm_set_repository.dart';
import 'protocol_repository.dart';
import 'session_repository.dart';
import 'settings_repository.dart';
import 'site_repository.dart';
import 'user_repository.dart';

/// Bitta tashkilot + qurilma + foydalanuvchi uchun barcha repozitoriylar.
class Repositories {
  Repositories(
    this.ctx, {
    required Signer signer,
    required String deviceId,
    required String actorId,
    String Function()? newQrToken,
  }) : users = UserRepository(ctx),
       devices = DeviceRepository(ctx),
       instruments = InstrumentRepository(ctx),
       sites = SiteRepository(ctx),
       graph = GraphRepository(ctx),
       sessions = SessionRepository(ctx),
       normSets = NormSetRepository(ctx),
       audit = AuditRepository(ctx, signer: signer, deviceId: deviceId, actorId: actorId) {
    isolationPlans = IsolationPlanRepository(ctx, audit: audit);
    measurements = MeasurementRepository(ctx, audit: audit, normSets: normSets);
    settings = SettingsRepository(ctx, audit: audit);
    protocols = ProtocolRepository(
      ctx,
      audit: audit,
      signer: signer,
      normSets: normSets,
      measurements: measurements,
      newQrToken: newQrToken,
    );
  }

  final DataContext ctx;
  final UserRepository users;
  final DeviceRepository devices;
  final InstrumentRepository instruments;
  final SiteRepository sites;
  final GraphRepository graph;
  final SessionRepository sessions;
  final NormSetRepository normSets;
  final AuditRepository audit;
  late final IsolationPlanRepository isolationPlans;
  late final MeasurementRepository measurements;
  late final ProtocolRepository protocols;
  late final SettingsRepository settings;
}
