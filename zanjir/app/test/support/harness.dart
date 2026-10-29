import 'package:drift/drift.dart' show driftRuntimeOptions;
import 'package:drift/native.dart';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/app.dart';
import 'package:zanjir_app/core/key_store.dart';
import 'package:zanjir_app/core/platform.dart';
import 'package:zanjir_app/core/profile.dart';
import 'package:zanjir_app/core/providers.dart';
import 'package:zanjir_app/router.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'fake_http_server.dart';

/// Ilova bilan birga keladigan normalar (host testida ham, qurilmada ham asset orqali).
Future<String> loadNorms() => rootBundle.loadString('assets/norms/v0.yaml');

Future<Uint8List> assetBytes(String path) async => (await rootBundle.load(path)).buffer.asUint8List();

/// Qat'iy soat: asbob qiyoslash muddati va vaqtlar deterministik.
final DateTime testNow = DateTime.utc(2026, 10, 26, 8);

class TestEnv {
  TestEnv({this.server}) : db = ZanjirDatabase(NativeDatabase.memory()) {
    driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
  }

  final ZanjirDatabase db;
  final keys = MemoryDeviceKeyStore();
  final secureScreen = FakeSecureScreen();
  final pdfActions = FakePdfActions();
  final tokens = MemoryTokenStore();

  /// Berilsa — ilova shu soxta serverga ulanadi (`https://zanjir.test/`); aks holda server sozlanmagan.
  final FakeHttpServer? server;
  Profile? profile;

  Widget app() => ProviderScope(
    retry: (_, _) => null,
    overrides: [
      databaseProvider.overrideWithValue(db),
      keyStoreProvider.overrideWithValue(keys),
      clockProvider.overrideWithValue(() => testNow),
      secureScreenProvider.overrideWithValue(secureScreen),
      pdfActionsProvider.overrideWithValue(pdfActions),
      tokenStoreProvider.overrideWithValue(tokens),
      serverUrlProvider.overrideWithValue(server == null ? '' : 'https://zanjir.test/'),
      httpClientProvider.overrideWithValue(server?.client),
    ],
    child: const ZanjirApp(),
  );

  /// Haqiqiy IO (sqlite, ed25519) — `runAsync` ichida.
  Future<T> io<T>(WidgetTester tester, Future<T> Function() f) async => (await tester.runAsync(f)) as T;

  Future<Profile> createProfile(WidgetTester tester, {String role = 'LEAD'}) => io(tester, () async {
    final normsYaml = await loadNorms();
    final p = await ProfileService(
      db: db,
      keyStore: keys,
      clock: () => testNow,
    ).create(labName: 'Elektrolab', fullName: 'Karimov A.', phone: '+998901234567', role: role, normsYaml: normsYaml);
    profile = p;
    return p;
  });

  /// Joriy profil repozitoriylari (UI orqali yaratilgan bo'lsa — bazadan yuklanadi).
  Future<Repositories> repos(WidgetTester tester) => io(tester, () async {
    final p = profile ??= await ProfileService(db: db, keyStore: keys).load();
    if (p == null) throw StateError('Profil yo\'q');
    final signer = await Ed25519Signer.fromSeed((await keys.readSeed())!);
    return Repositories(
      DataContext(db: db, orgId: p.orgId, clock: () => testNow),
      signer: signer,
      deviceId: p.deviceId,
      actorId: p.userId,
    );
  });

  Future<void> dispose(WidgetTester tester) => io(tester, db.close);
}

/// Kichik obyekt: TP-1 (tarmoq) — QF1 (C16) — XS1 (rozetkalar, oxirgi zanjir) va asbob.
class DemoSite {
  DemoSite(this.site, this.grid, this.qf1, this.xs1, this.instrument);
  final SiteRow site;
  final NodeRow grid;
  final NodeRow qf1;
  final NodeRow xs1;
  final InstrumentRow instrument;

  static Future<DemoSite> create(WidgetTester tester, TestEnv env) async {
    final r = await env.repos(tester);
    return env.io(tester, () async {
      final site = await r.sites.create(name: 'Savdo markazi', earthingSystem: EarthingSystem.tnCS, u0Volts: 220);
      final grid = await r.graph.addNode(siteId: site.id, kind: NodeKind.srcGrid, label: 'TP-1', verified: true);
      final qf1 = await r.graph.addNode(
        siteId: site.id,
        kind: NodeKind.breaker,
        label: 'QF1',
        attrs: {'in_a': 16, 'curve': 'C'},
        verified: true,
      );
      final xs1 = await r.graph.addNode(
        siteId: site.id,
        kind: NodeKind.socketGroup,
        label: 'XS1',
        attrs: {'circuit_role': 'final'},
        verified: true,
      );
      await r.graph.addEdge(siteId: site.id, aNodeId: grid.id, bNodeId: qf1.id, conductors: 'L1 N PE');
      await r.graph.addEdge(siteId: site.id, aNodeId: qf1.id, bNodeId: xs1.id, conductors: 'L1 N PE');
      final instrument = await r.instruments.create(
        kind: 'MULTIFUNCTION',
        model: 'MI 3152',
        serialNo: 'SN-001',
        verifiedUntil: DateTime.utc(2027, 3, 1),
      );
      return DemoSite(site, grid, qf1, xs1, instrument);
    });
  }
}

/// IO tugaguncha kadrlarni chizadi (cheksiz animatsiyalar uchun `pumpAndSettle` o'rniga).
Future<void> settle(WidgetTester tester, {int frames = 20}) async {
  for (var i = 0; i < frames; i++) {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 5)));
    await tester.pump(const Duration(milliseconds: 50));
  }
}

/// Router orqali to'g'ridan-to'g'ri ekranga o'tish.
Future<void> goTo(WidgetTester tester, String location) async {
  final container = ProviderScope.containerOf(tester.element(find.byType(Navigator).first));
  container.read(routerProvider).go(location);
  await settle(tester);
}

/// Profil + demo obyekt + ochiq sessiya, ilova ishga tushirilgan.
Future<(TestEnv, DemoSite, String)> startWithSession(
  WidgetTester tester, {
  String role = 'LEAD',
  double? temp = 20,
}) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.5;
  addTearDown(tester.view.reset);
  final env = TestEnv();
  await env.createProfile(tester, role: role);
  final demo = await DemoSite.create(tester, env);
  final repos = await env.repos(tester);
  final session = await env.io(
    tester,
    () => repos.sessions.start(
      siteId: demo.site.id,
      kind: SessionKind.davriy,
      engineerId: env.profile!.userId,
      ambientTempC: temp,
    ),
  );
  await tester.pumpWidget(env.app());
  await settle(tester);
  return (env, demo, session.id);
}

/// Dangasa `ListView` ichidagi elementni ko'rinadigan qilish (birinchi Scrollable bo'yicha).
/// Lazy ro'yxatdagi elementni ko'rinadigan qilish: sahifaning vertikal ro'yxati (gorizontal chip qatorlari emas) element
/// qurilguncha avval pastga, keyin tepaga aylantiriladi, so'ng element ekran markaziga keltiriladi (pastki doimiy
/// ogohlantirish banneri bosishni to'smasin).
Future<void> reveal(WidgetTester tester, Finder f) async {
  final list = find
      .byWidgetPredicate((w) => w is Scrollable && axisDirectionToAxis(w.axisDirection) == Axis.vertical)
      .first;
  for (final dy in [-200.0, 200.0]) {
    for (var i = 0; i < 40 && f.evaluate().isEmpty; i++) {
      await tester.drag(list, Offset(0, dy));
      await tester.pump();
    }
  }
  expect(f, findsWidgets, reason: 'aylantirib topilmadi');
  await Scrollable.ensureVisible(tester.element(f.first), alignment: 0.5);
  await tester.pump();
}

/// FLAG_SECURE holati (Android kanali o'rniga).
class FakeSecureScreen implements SecureScreen {
  bool enabled = false;
  final calls = <String>[];

  @override
  Future<void> enable() async {
    enabled = true;
    calls.add('enable');
  }

  @override
  Future<void> disable() async {
    enabled = false;
    calls.add('disable');
  }
}

class FakePdfActions implements PdfActions {
  final shared = <(String, Uint8List)>[];
  final printed = <String>[];

  @override
  Future<void> share(Uint8List pdf, String filename) async => shared.add((filename, pdf));

  @override
  Future<void> print(Uint8List pdf, String name) async => printed.add(name);
}

/// Faqat testlar uchun: v0 normalari `0.1.1` versiyasi va **soxta** tekshiruvchi bilan
/// (`norms/v0.yaml` ga tegilmaydi — CLAUDE.md, 11-qoida).
Future<String> reviewedTestNorms() async => (await loadNorms())
    .replaceFirst('version: "0.1.0"', 'version: "0.1.1"')
    .replaceFirst('reviewed_by: ""', 'reviewed_by: "TEST FIXTURE — haqiqiy tekshiruv emas"')
    .replaceFirst('reviewed_at: ""', 'reviewed_at: "2026-10-01"');
