import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/fake_http_server.dart';
import 'support/harness.dart';

const password = 'Juda-maxfiy-parol-1';

void viewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.5;
  addTearDown(tester.view.reset);
}

/// LEAD oflayn profili serverda ro'yxatdan o'tgan (ma'lumot qatlami orqali), obyekt bilan.
Future<TestEnv> registeredLab(WidgetTester tester, FakeHttpServer server) async {
  final env = TestEnv(server: server);
  await env.createProfile(tester);
  final repos = await env.repos(tester);
  await env.io(tester, () async {
    await repos.sites.create(name: 'Serverdagi obyekt');
    final signer = await Ed25519Signer.fromSeed((await env.keys.readSeed())!);
    final api = ServerApi('https://zanjir.test/', tokens: env.tokens, client: server.client);
    await ServerAccount(env.db, api).registerLab(password: password, publicKeyHex: signer.publicKeyHex);
  });
  return env;
}

Future<void> tapKey(WidgetTester tester, String key, {int frames = 40}) async {
  await reveal(tester, find.byKey(Key(key)));
  await tester.tap(find.byKey(Key(key)));
  await settle(tester, frames: frames);
}

void main() {
  testWidgets('LEAD laboratoriyani serverda ro\'yxatdan o\'tkazadi, keyin sinxronlaydi', (tester) async {
    viewport(tester);
    final server = FakeHttpServer();
    final env = TestEnv(server: server);
    await env.createProfile(tester);
    await tester.pumpWidget(env.app());
    await settle(tester);
    await goTo(tester, '/settings');
    expect(find.textContaining('Serverga ulanmagan'), findsOneWidget);

    await tapKey(tester, 'server.register');
    await tester.enterText(find.byKey(const Key('register.password')), 'qisqa');
    await tester.tap(find.byKey(const Key('register.submit')));
    await settle(tester);
    expect(find.text('Kamida 10 belgi'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('register.password')), password);
    await tester.enterText(find.byKey(const Key('register.repeat')), password);
    await tester.tap(find.byKey(const Key('register.submit')));
    await settle(tester, frames: 60);

    expect(find.text('Serverga ulangan'), findsOneWidget);
    expect(find.textContaining('Yuborilmagan o\'zgarishlar: 0'), findsOneWidget);
    expect(server.table('organization'), hasLength(1));
    expect(server.table('norm_set'), isNotEmpty);
    expect(server.table('audit_event'), isNotEmpty);
    expect(server.table('device').single['id'], env.profile!.deviceId);

    // Yangi lokal o'zgarish → "Sinxronlash".
    final repos = await env.repos(tester);
    await env.io(tester, () => repos.sites.create(name: 'Yangi obyekt'));
    await tapKey(tester, 'sync.now', frames: 60);
    expect(server.table('site').map((s) => s['name']), contains('Yangi obyekt'));
    expect(find.textContaining('Yuborilmagan o\'zgarishlar: 0'), findsOneWidget);
    await env.dispose(tester);
  });

  testWidgets('taklif kodi → yangi qurilmada qo\'shilish → serverdagi obyekt ko\'rinadi', (tester) async {
    viewport(tester);
    final server = FakeHttpServer();
    final lead = await registeredLab(tester, server);
    await tester.pumpWidget(lead.app());
    await settle(tester);
    await goTo(tester, '/settings');
    await settle(tester, frames: 30);
    await tapKey(tester, 'server.invite');
    await tester.tap(find.byKey(const Key('invite.role.ENGINEER')));
    await settle(tester, frames: 30);
    final code = tester.widget<SelectableText>(find.byKey(const Key('invite.code'))).data!;
    expect(code, hasLength(16));

    final eng = TestEnv(server: server);
    await tester.pumpWidget(const SizedBox()); // eski ProviderScope yopiladi — boshqa qurilma
    await tester.pumpWidget(eng.app());
    await settle(tester);
    await tester.tap(find.byKey(const Key('login.join')));
    await settle(tester);
    await tester.enterText(find.byKey(const Key('join.code')), code.toLowerCase());
    await tester.enterText(find.byKey(const Key('join.name')), 'Muhandis B');
    await tester.enterText(find.byKey(const Key('join.phone')), '+998907654321');
    await tester.enterText(find.byKey(const Key('join.password')), password);
    await tester.enterText(find.byKey(const Key('join.repeat')), password);
    await tapKey(tester, 'join.submit', frames: 80);

    expect(find.text('Serverdagi obyekt'), findsOneWidget);
    final profile = await eng.io(tester, () => ProfileServiceProbe(eng).load());
    expect(profile?.role, 'ENGINEER');
    expect(server.table('device'), hasLength(2));
    await eng.dispose(tester);
    await lead.dispose(tester);
  });

  testWidgets('yangi qurilmada kirish: noto\'g\'ri parol xatosi, keyin hamma narsa serverdan', (tester) async {
    viewport(tester);
    final server = FakeHttpServer();
    final lead = await registeredLab(tester, server);
    final fresh = TestEnv(server: server);
    await tester.pumpWidget(fresh.app());
    await settle(tester);
    await tester.enterText(find.byKey(const Key('login.phone')), '+998901234567');
    await tester.enterText(find.byKey(const Key('login.password')), 'Noto\'g\'ri-parol');
    await tapKey(tester, 'login.submit');
    expect(find.text('Telefon yoki parol noto\'g\'ri'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('login.password')), password);
    await tapKey(tester, 'login.submit', frames: 80);
    expect(find.text('Serverdagi obyekt'), findsOneWidget);
    await fresh.dispose(tester);
    await lead.dispose(tester);
  });

  testWidgets('server paketni rad etsa — xato ko\'rsatiladi, o\'zgarishlar navbatda qoladi', (tester) async {
    viewport(tester);
    final server = FakeHttpServer();
    final env = await registeredLab(tester, server);
    await tester.pumpWidget(env.app());
    await settle(tester);
    final repos = await env.repos(tester);
    await env.io(tester, () => repos.sites.create(name: 'Rad etiladigan'));
    server.rejectPushReason = 'audit_chain:bad_signature';
    await goTo(tester, '/settings');
    await tapKey(tester, 'sync.now', frames: 60);
    expect(find.byKey(const Key('server.error')), findsOneWidget);
    expect(find.textContaining('audit_chain:bad_signature'), findsOneWidget);
    expect(find.textContaining('Yuborilmagan o\'zgarishlar: 1'), findsOneWidget);
    expect(server.table('site').map((s) => s['name']), isNot(contains('Rad etiladigan')));

    // Server tuzalgach — navbat yuboriladi; chiqish.
    server.rejectPushReason = null;
    await tapKey(tester, 'sync.now', frames: 60);
    expect(server.table('site').map((s) => s['name']), contains('Rad etiladigan'));
    expect(find.byKey(const Key('server.error')), findsNothing);
    await tapKey(tester, 'server.logout');
    expect(find.textContaining('Serverga ulanmagan'), findsOneWidget);
    await env.dispose(tester);
  });
}

/// Lokal profilni bazadan o'qish (UI dan tashqari tekshiruv).
class ProfileServiceProbe {
  ProfileServiceProbe(this.env);
  final TestEnv env;

  Future<({String role})?> load() async {
    final prefs = LocalPrefRepository(env.db);
    final org = await prefs.get(LocalPrefRepository.orgId);
    final user = await prefs.get(LocalPrefRepository.userId);
    if (org == null || user == null) return null;
    final row = await UserRepository(DataContext(db: env.db, orgId: org)).get(user);
    return row == null ? null : (role: row.role);
  }
}
