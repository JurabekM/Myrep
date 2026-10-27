import 'package:baraka_daftari/app/app.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Ilovani ishga tushirish nuqtasi. Shifrlangan baza (kalit + SQLCipher)
/// `appDatabaseProvider` orqali birinchi murojaatda ochiladi.
Future<void> bootstrap() async {
  WidgetsFlutterBinding.ensureInitialized();
  AppLog.configureForBuildMode();
  runApp(const ProviderScope(child: BarakaApp()));
}
