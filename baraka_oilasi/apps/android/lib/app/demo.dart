import 'dart:typed_data';

import '../bindings/third_party/baraka_app.dart';

/// Demo yig'ma (`--dart-define=BARAKA_DEMO=true`): o'rtadagi odamga ko'rsatish uchun. Har ekranda
/// «DEMO» belgisi, muddati tugagach ilova ochilmaydi, PDF va `.baraka` fayllarni saqlash yoki
/// yuborish o'chirilgan. Paket nomi boshqa (`.demo`) — Gradle'dagi `baraka.demo` bilan birga.
const bool kDemo = bool.fromEnvironment('BARAKA_DEMO');

/// Oxirgi ishlaydigan kun, `YYYY-MM-DD` (`--dart-define=BARAKA_DEMO_EXPIRES=...`); bo'sh — muddatsiz.
const String demoExpires = String.fromEnvironment('BARAKA_DEMO_EXPIRES');

/// Demo muddati o'tganmi (shu qurilma soati bo'yicha).
bool demoExpired(DateTime now) {
  if (!kDemo || demoExpires.isEmpty) return false;
  final last = DateTime.parse(demoExpires);
  return !now.isBefore(DateTime(last.year, last.month, last.day + 1));
}

/// Demoda fayl ulashish o'rniga: yadro xatosi kabi `error.DEMO_DISABLED` xabari chiqadi.
Future<void> demoShareDisabled(Uint8List bytes, String name, String mime) async =>
    throw const AppError(code: 'DEMO_DISABLED');
