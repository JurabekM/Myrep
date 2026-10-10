import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite_sqlcipher/sqflite.dart';

import 'src/app_session.dart';
import 'src/offline/local_db.dart';
import 'src/screens/home_screen.dart';
import 'src/screens/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Lokal baza SQLCipher bilan shifrlanadi; paroli Android Keystore'da saqlanadi.
  final password = await DbPasswordStore().load();
  final db = await LocalDb.open(
    p.join(await getDatabasesPath(), 'omborai_local.db'),
    password: password,
  );
  final session = AppSession(db: db, keys: StoreKeyStore());
  runApp(OmborApp(session: session));
}

class OmborApp extends StatelessWidget {
  const OmborApp({super.key, required this.session});

  final AppSession session;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OmborAI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF0F766E),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFF2DD4BF),
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: _Bootstrap(session: session),
    );
  }
}

/// Saqlangan sessiya bo'lsa, bosh sahifaga; bo'lmasa, kirish oynasiga.
class _Bootstrap extends StatelessWidget {
  const _Bootstrap({required this.session});

  final AppSession session;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: session.restore(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        return snapshot.data == true
            ? HomeScreen(session: session)
            : LoginScreen(session: session);
      },
    );
  }
}
