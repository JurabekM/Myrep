import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:omborai_mobile/src/app_session.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/screens/login_screen.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  setUpAll(() => sqfliteFfiInit());

  Future<AppSession> sessionWith({bool store = false}) async {
    final db = await LocalDb.open(
      inMemoryDatabasePath,
      factory: databaseFactoryFfi,
    );
    if (store) {
      await db.setState('store_id', '11111111-2222-3333-4444-555555555555');
    }
    final session = AppSession(db: db, keys: StoreKeyStore());
    await session
        .restore(); // do'kon id'sini lokal holatdan oladi (tarmoq kerak emas)
    return session;
  }

  testWidgets("do'kon yo'q bo'lsa yaratish yoki qo'shilish taklif qilinadi", (
    tester,
  ) async {
    final session = await tester.runAsync(() => sessionWith());
    await tester.pumpWidget(MaterialApp(home: LoginScreen(session: session!)));

    expect(find.text("Yangi do'kon yaratish"), findsOneWidget);
    expect(find.text("Do'konga qo'shilish (juftlash kodi)"), findsOneWidget);
  });

  testWidgets("do'kon bor bo'lsa bo'sh login bilan xato xabari beriladi", (
    tester,
  ) async {
    final session = await tester.runAsync(() => sessionWith(store: true));
    await tester.pumpWidget(MaterialApp(home: LoginScreen(session: session!)));

    await tester.tap(find.text('Kirish'));
    await tester.pump();

    expect(find.text('Login va parolni kiriting'), findsOneWidget);
  });
}
