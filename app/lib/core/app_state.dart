/// Ilova holati: tekshirilgan baza, o'z-o'zini isbotlash ma'lumoti, oxirgi audit.
library;

import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../engine/audit_rules.dart';
import 'db.dart';
import 'native.dart';

class DbStatus {
  const DbStatus({required this.ok, this.error, this.version = 0, this.keyId = '', this.issuedAt = 0});
  final bool ok;
  final String? error;
  final int version;
  final String keyId;
  final int issuedAt;
}

class AppState extends ChangeNotifier {
  AppState._();
  static final AppState instance = AppState._();

  RostorDb db = RostorDb.empty();
  DbStatus dbStatus = const DbStatus(ok: false, error: 'yuklanmoqda');
  Map<String, dynamic>? self;
  DeviceAudit? lastAudit;
  int auditSequence = 0;
  List<String> changedPackages = const [];
  bool firstRun = true;
  Set<String> trustedApps = {};

  Future<void> init() async {
    try {
      final r = await Native.loadDb();
      if (r['ok'] == true) {
        db = RostorDb.fromPayload(r['payload'] as String, (r['version'] as num).toInt());
        dbStatus = DbStatus(
          ok: true,
          version: (r['version'] as num).toInt(),
          keyId: (r['keyId'] as String?) ?? '',
          issuedAt: (r['issuedAt'] as num?)?.toInt() ?? 0,
        );
      } else {
        dbStatus = DbStatus(ok: false, error: r['error'] as String?);
      }
    } catch (e) {
      dbStatus = DbStatus(ok: false, error: '$e');
    }
    try {
      self = await Native.selfInfo();
      final t = await Native.kvGet('trusted_apps');
      if (t != null) trustedApps = (jsonDecode(t) as List).cast<String>().toSet();
      await refreshChanges();
    } catch (_) {}
    notifyListeners();
  }

  Future<void> refreshChanges() async {
    final c = await Native.changedSinceLast();
    firstRun = c['first'] == true;
    changedPackages = [for (final p in (c['packages'] as List? ?? const [])) p as String];
    auditSequence = (c['sequence'] as num?)?.toInt() ?? 0;
    notifyListeners();
  }

  Future<DeviceAudit> runAudit() async {
    final raw = await Native.audit();
    final audit = evaluateAudit(raw, db);
    lastAudit = audit;
    // Audit qilingan holatni belgilaymiz: keyingi safar faqat yangi o'zgarishlar ko'rsatiladi.
    final c = await Native.changedSinceLast();
    await Native.markAudited((c['sequence'] as num?)?.toInt() ?? 0);
    changedPackages = const [];
    firstRun = false;
    notifyListeners();
    return audit;
  }

  Future<void> setTrusted(String pkg, bool trusted) async {
    trusted ? trustedApps.add(pkg) : trustedApps.remove(pkg);
    await Native.kvSet('trusted_apps', jsonEncode(trustedApps.toList()));
    notifyListeners();
  }
}
