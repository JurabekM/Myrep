import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

Future<void> openStaff(WidgetTester tester, TestEnv env) async {
  await tester.pumpWidget(env.app());
  await settle(tester);
  await goTo(tester, '/staff');
}

void main() {
  testWidgets('LEAD xodim qo\'shadi va taklif qiladi → yangi telefon qo\'shiladi → fayl almashinadi → bekor qilinadi', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    // 1-telefon (LEAD): xodim qo'shish.
    final a = TestEnv();
    await a.createProfile(tester);
    await openStaff(tester, a);
    await tester.tap(find.byKey(const Key('staff.add')));
    await settle(tester);
    await tester.enterText(find.byKey(const Key('staff.name')), 'Toshmatov B.');
    await tester.tap(find.byKey(const Key('staff.save')));
    await settle(tester);
    expect(find.text('Toshmatov B.'), findsOneWidget);
    final aRepos = await a.repos(tester);
    final user = (await a.io(tester, aRepos.staff.users)).singleWhere((u) => u.fullName == 'Toshmatov B.');
    expect(user.role, 'ENGINEER');

    // Taklif: fayl saqlanadi, parol himoyalangan ekranda ko'rsatiladi.
    await tester.tap(find.byKey(Key('staff.invite.${user.id}')));
    await settle(tester, frames: 40);
    final (inviteName, invite) = a.fileActions.saved.single;
    expect(inviteName, endsWith('.zanjirx'));
    expect(readExchangeHeader(invite).kind, ExchangeKind.invite);
    final password = tester.widget<SelectableText>(find.byKey(const Key('invite.password'))).data!;
    expect(password, hasLength(invitePasswordLength));
    expect(a.secureScreen.enabled, isTrue);
    await tester.tap(find.text('Yopish'));
    await settle(tester);
    expect(a.secureScreen.calls, ['enable', 'disable']);
    await tester.pumpWidget(const SizedBox());

    // 2-telefon: taklif bilan qo'shilish (noto'g'ri parol — rad).
    final b = TestEnv()..fileActions.toPick = invite;
    await tester.pumpWidget(b.app());
    await settle(tester);
    await tester.tap(find.byKey(const Key('start.join')));
    await settle(tester);
    await tester.enterText(find.byKey(const Key('password.value')), 'NOTOGRIPAROL');
    await tester.tap(find.byKey(const Key('password.confirm')));
    await settle(tester, frames: 40);
    expect(find.text('Taklif paroli noto\'g\'ri yoki fayl o\'zgartirilgan'), findsOneWidget);
    await tester.tap(find.byKey(const Key('start.join')));
    await settle(tester);
    await tester.enterText(find.byKey(const Key('password.value')), password.toLowerCase());
    await tester.tap(find.byKey(const Key('password.confirm')));
    await settle(tester, frames: 40);
    final bProfile = await b.io(tester, () => ProfileServiceLoader.load(b));
    expect(bProfile.$1, user.id);

    // 2-telefon fayl yuboradi.
    await goTo(tester, '/staff');
    await tester.tap(find.byKey(const Key('exchange.export')));
    await settle(tester, frames: 40);
    final (exportName, exported) = b.fileActions.saved.single;
    expect(exportName, startsWith('zanjir-almashish-'));
    expect(find.text('Almashish fayli saqlandi'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());

    // 1-telefon qabul qiladi va 2-telefonni bekor qiladi.
    a.fileActions.toPick = exported;
    await openStaff(tester, a);
    await tester.tap(find.byKey(const Key('exchange.import')));
    await settle(tester, frames: 40);
    expect(find.textContaining('ta yozuv qabul qilindi'), findsOneWidget);
    await reveal(tester, find.byKey(Key('device.revoke.${bProfile.$2}')));
    await tester.tap(find.byKey(Key('device.revoke.${bProfile.$2}')));
    await settle(tester);
    await tester.tap(find.byKey(const Key('device.revokeConfirm')));
    await settle(tester);
    await reveal(tester, find.textContaining('Bekor qilingan'));
    expect(find.textContaining('Bekor qilingan'), findsOneWidget);

    // Taklif fayli almashish sifatida qabul qilinmaydi.
    a.fileActions.toPick = invite;
    await reveal(tester, find.byKey(const Key('exchange.import')));
    await tester.tap(find.byKey(const Key('exchange.import')));
    await settle(tester);
    expect(find.textContaining('Bu taklif fayli'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await a.dispose(tester);
    await b.dispose(tester);
  });
}

/// 2-telefon profili bazadan: (foydalanuvchi, qurilma).
abstract final class ProfileServiceLoader {
  static Future<(String, String)> load(TestEnv env) async {
    final prefs = LocalPrefRepository(env.db);
    return ((await prefs.get(LocalPrefRepository.userId))!, (await prefs.get(LocalPrefRepository.deviceId))!);
  }
}
