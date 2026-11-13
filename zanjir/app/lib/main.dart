import 'package:drift_flutter/drift_flutter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'app.dart';
import 'core/key_store.dart';
import 'core/providers.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final db = ZanjirDatabase(driftDatabase(name: 'zanjir'));
  runApp(
    ProviderScope(
      // Xato bo'lsa avtomatik qayta urinish yo'q — foydalanuvchi "Qayta urinish" ni bosadi.
      retry: (_, _) => null,
      overrides: [databaseProvider.overrideWithValue(db), keyStoreProvider.overrideWithValue(SecureDeviceKeyStore())],
      child: const ZanjirApp(),
    ),
  );
}
