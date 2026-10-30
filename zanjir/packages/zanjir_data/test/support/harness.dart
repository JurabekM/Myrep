import 'dart:io';

import 'package:drift/native.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

final String v0Yaml = File('../../norms/v0.yaml').readAsStringSync();

/// Har chaqiruvda 1 soniya oldinga yuradigan deterministik soat (UTC).
DateTime Function() steppingClock([DateTime? start]) {
  var t = start ?? DateTime.utc(2026, 10, 26, 7);
  return () {
    final now = t;
    t = t.add(const Duration(seconds: 1));
    return now;
  };
}

/// Bitta tashkilot uchun to'liq muhit: baza, foydalanuvchi, qurilma kaliti, repozitoriylar.
class Org {
  Org._(this.ctx, this.user, this.device, this.signer, this.repos);
  final DataContext ctx;
  final AppUserRow user;
  final DeviceRow device;
  final Ed25519Signer signer;
  final Repositories repos;

  static Future<Org> create(ZanjirDatabase db, String name, {List<int>? seed, String role = 'LEAD'}) async {
    final orgId = await OrganizationRepository(db, clock: steppingClock()).create(name: name);
    final ctx = DataContext(db: db, orgId: orgId, clock: steppingClock());
    final user = await UserRepository(ctx)
        .create(fullName: 'Muhandis $name', phone: '+998900000000', role: role, safetyGroup: 'V');
    final signer = await Ed25519Signer.fromSeed(seed ?? List.filled(32, name.codeUnitAt(0)));
    final device = await DeviceRepository(ctx)
        .register(userId: user.id, publicKeyHex: signer.publicKeyHex, sigAlg: signer.sigAlg);
    final repos = Repositories(ctx, signer: signer, deviceId: device.id, actorId: user.id);
    return Org._(ctx, user, device, signer, repos);
  }
}

ZanjirDatabase memoryDb() => ZanjirDatabase(NativeDatabase.memory());

/// Kichik obyekt: GRID — QF1 (C16) — CAB1 (oxirgi zanjir) — SOCK1.
class SmallSite {
  SmallSite(this.site, this.grid, this.qf1, this.cab1, this.sock1, this.instrument);
  final SiteRow site;
  final NodeRow grid;
  final NodeRow qf1;
  final NodeRow cab1;
  final NodeRow sock1;
  final InstrumentRow instrument;

  static Future<SmallSite> create(Org org) => createWith(org.repos);

  static Future<SmallSite> createWith(Repositories r) async {
    final site = await r.sites.create(name: 'Obyekt', earthingSystem: EarthingSystem.tnCS, u0Volts: 220);
    final grid = await r.graph.addNode(siteId: site.id, kind: NodeKind.srcGrid, label: 'TP-1', verified: true);
    final qf1 = await r.graph.addNode(
      siteId: site.id,
      kind: NodeKind.breaker,
      label: 'QF1',
      attrs: {'in_a': 16, 'curve': 'C'},
      verified: true,
      state: SwitchState.closed,
    );
    final cab1 = await r.graph.addNode(
      siteId: site.id,
      kind: NodeKind.cable,
      label: 'W1',
      attrs: {'circuit_role': 'final', 'circuit_class': 'wiring', 'length_m': 22},
      verified: true,
    );
    final sock1 = await r.graph.addNode(
      siteId: site.id,
      kind: NodeKind.socketGroup,
      label: 'XS1',
      attrs: {'circuit_role': 'final'},
      verified: true,
    );
    await r.graph.addEdge(siteId: site.id, aNodeId: grid.id, bNodeId: qf1.id, conductors: 'L1 N PE');
    await r.graph.addEdge(siteId: site.id, aNodeId: qf1.id, bNodeId: cab1.id, conductors: 'L1 N PE');
    await r.graph.addEdge(siteId: site.id, aNodeId: cab1.id, bNodeId: sock1.id, conductors: 'L1 N PE');
    final instrument = await r.instruments.create(
      kind: 'MULTIFUNCTION',
      model: 'MI 3152',
      serialNo: 'SN-001',
      verificationCertNo: 'QV-2026/123',
      verifiedUntil: DateTime.utc(2027, 3, 1),
    );
    await r.normSets.import(v0Yaml);
    return SmallSite(site, grid, qf1, cab1, sock1, instrument);
  }
}

/// Faqat testlar uchun: v0 normalari boshqa versiya nomi va **soxta** tekshiruvchi bilan.
/// `norms/v0.yaml` dagi `reviewed_by` ga tegilmaydi (CLAUDE.md, 11-qoida).
final String reviewedTestYaml = v0Yaml
    .replaceFirst('version: "0.3.0"', 'version: "0.3.1"')
    .replaceFirst('reviewed_by: ""', 'reviewed_by: "TEST FIXTURE — haqiqiy tekshiruv emas"')
    .replaceFirst('reviewed_at: ""', 'reviewed_at: "2026-10-01"');
const reviewedTestVersion = '0.3.1';

ProtocolFonts testFonts() {
  const dir = '../../app/assets/fonts';
  return ProtocolFonts(
    regular: File('$dir/NotoSans-Regular.ttf').readAsBytesSync(),
    bold: File('$dir/NotoSans-Bold.ttf').readAsBytesSync(),
    symbols: File('$dir/NotoSansMath-Regular.ttf').readAsBytesSync(),
  );
}

/// Imzolashga tayyor sessiya: litsenziya, tekshirilgan (test) normalar, yaroqli asbob, PASS o'lchov, yopilgan.
class SignableSession {
  SignableSession(this.site, this.session, this.measurement);
  final SmallSite site;
  final MeasurementSessionRow session;
  final MeasurementRow measurement;

  static Future<SignableSession> create(Org org, {bool close = true}) async {
    final r = org.repos;
    final s = await SmallSite.create(org);
    await r.normSets.import(reviewedTestYaml);
    await r.settings.updateLab(
      byUserId: org.user.id,
      name: 'Lab ${org.ctx.orgId.substring(0, 4)}',
      licenseNo: 'EL-0042',
      licenseValidUntil: DateTime.utc(2027, 12, 31),
    );
    final session = await r.sessions.start(
      siteId: s.site.id,
      kind: SessionKind.davriy,
      engineerId: org.user.id,
      ambientTempC: 18,
    );
    final m = await recordLoop(org, session.id, s, zs: 0.84);
    return SignableSession(s, close ? await r.sessions.close(session.id) : session, m);
  }
}

Future<MeasurementRow> recordLoop(
  Org org,
  String sessionId,
  SmallSite s, {
  required double zs,
  String pair = 'L1-PE',
  String? instrumentId,
  String normSetVersion = reviewedTestVersion,
}) => org.repos.measurements.record(
  sessionId: sessionId,
  nodeId: s.sock1.id,
  type: MeasurementType.loopImpedance,
  instrumentId: instrumentId ?? s.instrument.id,
  values: {'pair': pair, 'zs_ohm': zs},
  enteredVia: EnteredVia.manual,
  normSetVersion: normSetVersion,
);
