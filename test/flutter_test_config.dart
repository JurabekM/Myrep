import 'dart:async';
import 'dart:ffi';
import 'dart:io';

import 'package:sqlite3/open.dart';

/// Barcha testlardan oldin: hostʼda (flutter_tester) SQLite kutubxonasini
/// topish. Androidʼda ilova oʻz SQLCipherʼini olib keladi; host testlari
/// uchun esa tizimdagi kutubxona kerak.
///
/// * Linux (CI): `libsqlite3.so` (apt: libsqlite3-dev) — standart yoʻl.
/// * Windows: `SQLITE3_LIBRARY` muhit oʻzgaruvchisi yoki PATHʼdagi
///   `sqlite3.dll` (Python oʻrnatmasidagi `DLLs/sqlite3.dll` ham).
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  if (Platform.isWindows) {
    final dll = _findWindowsSqlite();
    if (dll != null) {
      open.overrideFor(OperatingSystem.windows, () => DynamicLibrary.open(dll));
    }
  }
  await testMain();
}

String? _findWindowsSqlite() {
  final explicit = Platform.environment['SQLITE3_LIBRARY'];
  if (explicit != null && File(explicit).existsSync()) return explicit;
  final dirs = (Platform.environment['PATH'] ?? '').split(';');
  for (final dir in dirs.where((d) => d.trim().isNotEmpty)) {
    for (final candidate in ['$dir\\sqlite3.dll', '$dir\\DLLs\\sqlite3.dll']) {
      if (File(candidate).existsSync()) return candidate;
    }
  }
  return null;
}
