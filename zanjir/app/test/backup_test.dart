import 'package:flutter/foundation.dart' show Uint8List;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

Future<void> enterPassword(WidgetTester tester, String password, {bool repeat = false}) async {
  await tester.enterText(find.byKey(const Key('password.value')), password);
  if (repeat) await tester.enterText(find.byKey(const Key('password.repeat')), password);
  await tester.tap(find.byKey(const Key('password.confirm')));
  await settle(tester, frames: 40);
}

void main() {
  testWidgets('zaxira sozlamalarda yaratiladi va yangi telefonda tiklanadi', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    // 1-telefon: laboratoriya va obyekt, zaxira hali yo'q.
    final a = TestEnv();
    await a.createProfile(tester);
    await DemoSite.create(tester, a);
    await tester.pumpWidget(a.app());
    await settle(tester);
    await goTo(tester, '/settings');
    await reveal(tester, find.byKey(const Key('settings.backup')));
    expect(find.textContaining('Zaxira hali yaratilmagan'), findsOneWidget);

    await tester.tap(find.byKey(const Key('backup.create')));
    await settle(tester);
    await enterPassword(tester, 'qisqa', repeat: true);
    expect(find.text('Kamida 10 belgi'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('password.value')), 'zaxira-paroli-1');
    await tester.enterText(find.byKey(const Key('password.repeat')), 'zaxira-paroli-2');
    await tester.tap(find.byKey(const Key('password.confirm')));
    await settle(tester);
    expect(find.text('Parollar mos emas'), findsOneWidget);
    await enterPassword(tester, 'zaxira-paroli-1', repeat: true);

    expect(a.fileActions.saved, hasLength(1));
    final (name, bytes) = a.fileActions.saved.single;
    expect(name, matches(RegExp(r'^zanjir-\d{4}-\d{2}-\d{2}-\d{4}\.zanjir$')));
    expect(readBackupHeader(bytes).createdAt, testNow);
    expect(find.text('Zaxira saqlandi'), findsOneWidget);
    expect(find.textContaining('Oxirgi zaxira:'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await a.dispose(tester);

    // 2-telefon: bo'sh ilova → zaxiradan tiklash.
    final b = TestEnv()..fileActions.toPick = bytes;
    await tester.pumpWidget(b.app());
    await settle(tester);
    await tester.tap(find.byKey(const Key('start.restore')));
    await settle(tester);
    expect(find.textContaining('Zaxira sanasi:'), findsOneWidget);
    await enterPassword(tester, 'noto\'g\'ri-parol');
    expect(find.text('Parol noto\'g\'ri yoki fayl o\'zgartirilgan'), findsOneWidget);

    await tester.tap(find.byKey(const Key('start.restore')));
    await settle(tester);
    await enterPassword(tester, 'zaxira-paroli-1');
    expect(find.text('Savdo markazi'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);

    final repos = await b.repos(tester);
    final old = await b.io(tester, () => b.db.select(b.db.devices).get());
    expect(old, hasLength(2), reason: 'eski qurilma + tiklangan telefon');
    expect(old.map((d) => d.id), contains(b.profile!.deviceId));
    final chains = await b.io(tester, () => verifyOrgChains(repos.ctx));
    expect(chains.values.every((c) => c.ok), isTrue);
    await b.dispose(tester);
  });

  testWidgets('ZANJIR zaxirasi bo\'lmagan fayl — parol so\'ralmaydi', (tester) async {
    final env = TestEnv()..fileActions.toPick = Uint8List.fromList(List.filled(64, 7));
    await tester.pumpWidget(env.app());
    await settle(tester);
    await tester.tap(find.byKey(const Key('start.restore')));
    await settle(tester);
    expect(find.byKey(const Key('password.value')), findsNothing);
    expect(find.text('Bu ZANJIR zaxira fayli emas yoki u buzilgan'), findsOneWidget);
    await env.dispose(tester);
  });
}
