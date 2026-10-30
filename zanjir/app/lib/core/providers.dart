import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

import 'key_store.dart';
import 'platform.dart';
import 'profile.dart';

/// `main.dart` va testlarda override qilinadi.
final databaseProvider = Provider<ZanjirDatabase>((ref) => throw UnimplementedError('databaseProvider'));
final keyStoreProvider = Provider<DeviceKeyStore>((ref) => throw UnimplementedError('keyStoreProvider'));
final clockProvider = Provider<DateTime Function()>((ref) => DateTime.now);

/// Ilova bilan birga keladigan normalar to'plami (`assets/norms/v0.yaml` = `norms/v0.yaml`).
final bundledNormsProvider = Provider<Future<String> Function()>(
  (ref) =>
      () => rootBundle.loadString('assets/norms/v0.yaml'),
);

/// PDF shriftlari — UI bilan bir xil fayllar (`assets/fonts`, ADR-0010).
final protocolFontsProvider = FutureProvider<ProtocolFonts>((ref) async {
  Future<Uint8List> load(String name) async => (await rootBundle.load('assets/fonts/$name')).buffer.asUint8List();
  return ProtocolFonts(
    regular: await load('NotoSans-Regular.ttf'),
    bold: await load('NotoSans-Bold.ttf'),
    symbols: await load('NotoSansMath-Regular.ttf'),
  );
});

final secureScreenProvider = Provider<SecureScreen>((ref) => const MethodChannelSecureScreen());
final pdfActionsProvider = Provider<PdfActions>((ref) => const PrintingPdfActions());
final fileActionsProvider = Provider<FileActions>((ref) => const PickerFileActions());

/// Zaxira kaliti parametrlari; testlarda tezkor qiymat bilan almashtiriladi.
final backupKdfProvider = Provider<KdfParams>((ref) => KdfParams.standard);

final prefsProvider = Provider((ref) => LocalPrefRepository(ref.watch(databaseProvider)));

class ProfileNotifier extends AsyncNotifier<Profile?> {
  ProfileService get _service => ProfileService(
    db: ref.read(databaseProvider),
    keyStore: ref.read(keyStoreProvider),
    clock: ref.read(clockProvider),
  );

  @override
  Future<Profile?> build() => _service.load();

  Future<void> create({
    required String labName,
    required String fullName,
    required String phone,
    required String role,
  }) async {
    final yaml = await ref.read(bundledNormsProvider)();
    final p = await _service.create(labName: labName, fullName: fullName, phone: phone, role: role, normsYaml: yaml);
    state = AsyncData(p);
  }

  /// Shifrlangan zaxira faylidan (yangi telefon, ADR-0017).
  Future<void> restore(List<int> backup, String password) async {
    state = AsyncData(await _service.restore(backup, password));
    ref
      ..invalidate(repositoriesProvider)
      ..invalidate(localeProvider)
      ..invalidate(largeTextProvider)
      ..invalidate(lastBackupProvider);
  }
}

final profileProvider = AsyncNotifierProvider<ProfileNotifier, Profile?>(ProfileNotifier.new);

final repositoriesProvider = FutureProvider<Repositories>((ref) async {
  final profile = await ref.watch(profileProvider.future) ?? (throw StateError('Profil yo\'q'));
  final seed = await ref.read(keyStoreProvider).readSeed() ?? (throw StateError('Qurilma kaliti yo\'q'));
  final signer = await Ed25519Signer.fromSeed(seed);
  final ctx = DataContext(db: ref.watch(databaseProvider), orgId: profile.orgId, clock: ref.read(clockProvider));
  return Repositories(ctx, signer: signer, deviceId: profile.deviceId, actorId: profile.userId);
});

// --- UI sozlamalari (qurilmaga xos) ---

class LocaleNotifier extends AsyncNotifier<String> {
  @override
  Future<String> build() async => await ref.read(prefsProvider).get(LocalPrefRepository.locale) ?? 'uz';

  Future<void> set(String code) async {
    await ref.read(prefsProvider).set(LocalPrefRepository.locale, code);
    state = AsyncData(code);
  }
}

/// Oxirgi saqlangan zaxira vaqti (`null` — hali yo'q).
final lastBackupProvider = FutureProvider<DateTime?>((ref) async {
  final v = await ref.read(prefsProvider).get(LocalPrefRepository.lastBackupAt);
  return v == null ? null : DateTime.tryParse(v);
});

final localeProvider = AsyncNotifierProvider<LocaleNotifier, String>(LocaleNotifier.new);

class LargeTextNotifier extends AsyncNotifier<bool> {
  @override
  Future<bool> build() async => await ref.read(prefsProvider).get(LocalPrefRepository.largeText) == '1';

  Future<void> set(bool value) async {
    await ref.read(prefsProvider).set(LocalPrefRepository.largeText, value ? '1' : '0');
    state = AsyncData(value);
  }
}

final largeTextProvider = AsyncNotifierProvider<LargeTextNotifier, bool>(LargeTextNotifier.new);

// --- Ma'lumotlar (o'zgarishdan keyin `ref.invalidate`) ---

final sitesProvider = FutureProvider((ref) async => (await ref.watch(repositoriesProvider.future)).sites.list());

final siteProvider = FutureProvider.family<SiteRow?, String>(
  (ref, id) async => (await ref.watch(repositoriesProvider.future)).sites.get(id),
);

final nodesProvider = FutureProvider.family<List<NodeRow>, String>(
  (ref, siteId) async => (await ref.watch(repositoriesProvider.future)).graph.nodes(siteId),
);

final edgesProvider = FutureProvider.family<List<EdgeRow>, String>(
  (ref, siteId) async => (await ref.watch(repositoriesProvider.future)).graph.edges(siteId),
);

final graphProvider = FutureProvider.family<Graph, String>(
  (ref, siteId) async => (await ref.watch(repositoriesProvider.future)).graph.loadGraph(siteId),
);

final nodeProvider = FutureProvider.family<NodeRow?, String>(
  (ref, id) async => (await ref.watch(repositoriesProvider.future)).graph.getNode(id),
);

final nodeMeasurementsProvider = FutureProvider.family<List<MeasurementRow>, String>(
  (ref, nodeId) async => (await ref.watch(repositoriesProvider.future)).measurements.forNode(nodeId),
);

final siteSessionsProvider = FutureProvider.family<List<MeasurementSessionRow>, String>(
  (ref, siteId) async => (await ref.watch(repositoriesProvider.future)).sessions.forSite(siteId),
);

final sessionProvider = FutureProvider.family<MeasurementSessionRow?, String>(
  (ref, id) async => (await ref.watch(repositoriesProvider.future)).sessions.get(id),
);

final sessionMeasurementsProvider = FutureProvider.family<List<MeasurementRow>, String>(
  (ref, sessionId) async => (await ref.watch(repositoriesProvider.future)).measurements.forSession(sessionId),
);

final instrumentsProvider = FutureProvider(
  (ref) async => (await ref.watch(repositoriesProvider.future)).instruments.list(),
);

final labSettingsProvider = FutureProvider(
  (ref) async => (await ref.watch(repositoriesProvider.future)).settings.current(),
);

final organizationProvider = FutureProvider(
  (ref) async => (await ref.watch(repositoriesProvider.future)).settings.organization(),
);

final sessionProtocolsProvider = FutureProvider.family<List<(ProtocolRow, ProtocolStatus)>, String>((
  ref,
  sessionId,
) async {
  final repos = await ref.watch(repositoriesProvider.future);
  return [for (final p in await repos.protocols.forSession(sessionId)) (p, await repos.protocols.status(p.id))];
});

/// Imzolash shartlari (izohsiz qoralama; izoh UI'da kiritiladi, imzolashda qoralama qayta tuziladi).
final protocolDraftProvider = FutureProvider.family<ProtocolDraft, String>(
  (ref, sessionId) async => (await ref.watch(repositoriesProvider.future)).protocols.prepare(sessionId: sessionId),
);

/// Obyekt rejalari; ochilganda graf o'zgargan rejalar STALE qilinadi.
final sitePlansProvider = FutureProvider.family<List<IsolationPlanRow>, String>((ref, siteId) async {
  final repos = await ref.watch(repositoriesProvider.future);
  await repos.isolationPlans.refreshStale(siteId);
  return repos.isolationPlans.forSite(siteId);
});

/// Reja, qadamlar, ogohlantirishlar va bajarilgan qadamlar.
typedef PlanView = ({
  IsolationPlanRow plan,
  List<PlanStep> steps,
  List<PlanWarning> warnings,
  Map<int, StepRecord> done,
  Map<String, String> labels,
  Map<String, String> users,
});

final planProvider = FutureProvider.family<PlanView?, String>((ref, id) async {
  final repos = await ref.watch(repositoriesProvider.future);
  var plan = await repos.isolationPlans.get(id);
  if (plan == null) return null;
  if ((await repos.isolationPlans.refreshStale(plan.siteId)).contains(id)) plan = await repos.isolationPlans.get(id);
  final done = await repos.isolationPlans.doneSteps(id);
  final users = <String, String>{};
  for (final uid in {...done.values.map((r) => r.actorId), ?plan!.approvedBy}) {
    users[uid] = (await repos.users.get(uid))?.fullName ?? uid;
  }
  return (
    plan: plan,
    steps: repos.isolationPlans.steps(plan),
    warnings: repos.isolationPlans.warnings(plan),
    done: done,
    labels: {for (final n in await repos.graph.nodes(plan.siteId)) n.id: n.label},
    users: users,
  );
});

/// Faol normalar to'plami (sozlamalardagi versiya).
final activeNormSetProvider = FutureProvider<NormSet>((ref) async {
  final repos = await ref.watch(repositoriesProvider.future);
  final version = (await ref.watch(labSettingsProvider.future)).activeNormSetVersion;
  if (version == null) throw StateError('Faol normalar to\'plami tanlanmagan');
  return repos.normSets.load(version);
});

/// Obyekt grafiga tegishli barcha provayderlarni yangilash.
void invalidateSite(WidgetRef ref, String siteId) {
  ref.invalidate(nodesProvider(siteId));
  ref.invalidate(edgesProvider(siteId));
  ref.invalidate(graphProvider(siteId));
  ref.invalidate(siteProvider(siteId));
  ref.invalidate(sitesProvider);
}
