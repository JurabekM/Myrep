import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'integrity_service.g.dart';

enum IntegrityRisk { rooted, emulator, debugger, signatureMismatch, debuggable }

/// Native belgilardan foydalanuvchiga ko'rsatiladigan xavflar ro'yxati.
///
/// [releaseMode] — debug build doim `debuggable` bo'ladi, bu xavf emas.
Set<IntegrityRisk> risksFrom(IntegritySignals s, {required bool releaseMode}) =>
    {
      if (s.isRooted) IntegrityRisk.rooted,
      if (s.isEmulator) IntegrityRisk.emulator,
      if (s.isDebuggerAttached) IntegrityRisk.debugger,
      if (s.isSignatureValid == false) IntegrityRisk.signatureMismatch,
      if (releaseMode && s.isDebuggableBuild) IntegrityRisk.debuggable,
    };

/// Signallar lokal logi: `<app support>/security/integrity.log`, JSON qatorlar.
/// Faqat vaqt va xavf kodlari yoziladi — shaxsiy ma'lumot yo'q.
class IntegrityLog {
  IntegrityLog(this._directory, this._clock);

  static const maxLines = 200;

  final Future<Directory> Function() _directory;
  final Clock _clock;

  Future<File> _file() async {
    final dir = Directory('${(await _directory()).path}/security');
    await dir.create(recursive: true);
    return File('${dir.path}/integrity.log');
  }

  Future<void> append(Set<IntegrityRisk> risks) async {
    final file = await _file();
    final line = jsonEncode({
      'ts': _clock.nowUtc().toIso8601String(),
      'risks': [for (final r in risks) r.name],
    });
    final existing = file.existsSync() ? await file.readAsLines() : <String>[];
    final kept = [...existing, line];
    final tail = kept.length > maxLines
        ? kept.sublist(kept.length - maxLines)
        : kept;
    await file.writeAsString('${tail.join('\n')}\n', flush: true);
  }

  Future<List<String>> readLines() async {
    final file = await _file();
    return file.existsSync() ? file.readAsLines() : const [];
  }
}

@Riverpod(keepAlive: true)
IntegrityLog integrityLog(Ref ref) =>
    IntegrityLog(getApplicationSupportDirectory, ref.watch(clockProvider));

/// Ilova ishga tushganda bir marta tekshiriladi. Xato bo'lsa — xavf yo'q deb
/// emas, shunchaki bo'sh natija (ilova bloklanmaydi).
@Riverpod(keepAlive: true)
Future<Set<IntegrityRisk>> integrityRisks(Ref ref) async {
  try {
    final signals = await ref.watch(securityApiProvider).getIntegritySignals();
    final risks = risksFrom(signals, releaseMode: kReleaseMode);
    if (risks.isNotEmpty) {
      AppLog.event('integrity_risks_detected');
      // Log ogohlantirishni kechiktirmasin.
      unawaited(
        ref
            .read(integrityLogProvider)
            .append(risks)
            .catchError((Object _) => AppLog.event('integrity_log_failed')),
      );
    }
    return risks;
  } on Object {
    AppLog.event('integrity_check_failed');
    return const {};
  }
}

/// Foydalanuvchi ogohlantirishni shu sessiyada yopdimi.
@Riverpod(keepAlive: true)
class IntegrityWarningDismissed extends _$IntegrityWarningDismissed {
  @override
  bool build() => false;

  void dismiss() => state = true;
}
