import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:omborai_mobile/src/api/api_client.dart';
import 'package:omborai_mobile/src/app_session.dart';
import 'package:omborai_mobile/src/offline/local_db.dart';
import 'package:omborai_mobile/src/screens/login_screen.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class _MemoryTokens implements TokenStorage {
  Tokens? _value;

  @override
  Future<Tokens?> read() async => _value;

  @override
  Future<void> write(Tokens tokens) async => _value = tokens;

  @override
  Future<void> clear() async => _value = null;
}

void main() {
  setUpAll(() => sqfliteFfiInit());

  testWidgets("bo'sh maydonlar bilan kirish xabar beradi", (tester) async {
    final db = await tester.runAsync(
      () => LocalDb.open(inMemoryDatabasePath, factory: databaseFactoryFfi),
    );
    final session = AppSession(
      api: ApiClient(
        baseUrl: 'http://api.test',
        client: MockClient((_) async => throw UnimplementedError()),
      ),
      db: db!,
      tokens: _MemoryTokens(),
      keys: StoreKeyStore(),
    );
    await tester.pumpWidget(MaterialApp(home: LoginScreen(session: session)));

    await tester.tap(find.text('Kirish'));
    await tester.pump();

    expect(find.text('Email va parolni kiriting'), findsOneWidget);
  });
}
