/// Qurilma auditi qoidalari (T1 o'rnatilgandan keyin, T7). Kirish — DeviceAuditor.kt.
library;

import '../core/db.dart';
import '../core/risk.dart';
import 'apk_rules.dart' show brandMatch, installerName;

enum Source { system, store, messenger, unknown }

class AppAudit {
  AppAudit(this.facts, this.source, this.sourceName, this.findings);
  final Map<String, dynamic> facts;
  final Source source;
  final String sourceName;
  final List<Finding> findings;

  String get packageName => facts['packageName'] as String;
  String get label => (facts['label'] as String?) ?? packageName;
  Severity get severity => worstOf(findings);
}

class DeviceAudit {
  DeviceAudit(this.apps, this.deviceFindings, this.scannedAt);
  final List<AppAudit> apps;
  final List<Finding> deviceFindings;
  final DateTime scannedAt;

  Severity get severity => worstOf([...deviceFindings, for (final a in apps) ...a.findings]);
  List<AppAudit> get flagged => apps.where((a) => a.severity >= Severity.medium).toList()
    ..sort((a, b) => b.severity.index.compareTo(a.severity.index));
}

List<String> _list(Object? v) => [for (final x in (v as List? ?? const [])) x as String];

Source _sourceOf(Map<String, dynamic> app, RostorDb db) {
  if (app['system'] == true) return Source.system;
  final inst = Map<String, dynamic>.from((app['installer'] as Map?) ?? const {});
  final installing = inst['installing'] as String?;
  final initiating = inst['initiating'] as String?;
  if (installing != null && db.trustedInstallers.containsKey(installing)) return Source.store;
  if (initiating != null && db.messengerInstallers.containsKey(initiating)) return Source.messenger;
  return Source.unknown;
}

AppAudit evaluateApp(Map<String, dynamic> app, RostorDb db) {
  final src = _sourceOf(app, db);
  final inst = Map<String, dynamic>.from((app['installer'] as Map?) ?? const {});
  final srcName = src == Source.system ? 'Tizim ilovasi' : installerName(inst, db);
  final pkg = app['packageName'] as String;
  final label = (app['label'] as String?) ?? pkg;
  final sideloaded = src == Source.messenger || src == Source.unknown;
  final granted = _list(app['granted']).toSet();
  final certs = _list(app['certSha256']).map((s) => s.toLowerCase()).toList();
  final out = <Finding>[];
  final details = FindingAction("Ilova sozlamalari", 'openAppDetails', pkg);

  Severity by({required Severity side, required Severity store, Severity system = Severity.info}) =>
      src == Source.system ? system : (sideloaded ? side : store);

  if (certs.any(db.maliciousCerts.contains)) {
    out.add(Finding(
      code: 'app.malicious_cert', severity: Severity.critical,
      title: "Zararli dasturchi kaliti (bazada)",
      explain: "Bu ilova bazada zararli deb qayd etilgan kalit bilan imzolangan. Darhol o'chiring.",
      evidence: certs.first, action: details,
    ));
  }

  final official = db.officialPackage(pkg);
  final org = db.orgByPackage(pkg);
  if (official != null && official.certSha256.isNotEmpty && certs.isNotEmpty && !certs.any(official.certSha256.contains)) {
    out.add(Finding(
      code: 'app.official_mismatch', severity: Severity.critical,
      title: "${org!.name} ilovasi soxta kalit bilan imzolangan",
      explain: "Paket nomi rasmiy, lekin imzo ${org.name}niki emas. Bu almashtirilgan ilova: o'chirib, Play'dan qayta o'rnating.",
      evidence: certs.first, action: details,
    ));
  } else if (official != null && sideloaded) {
    out.add(Finding(
      code: 'app.official_sideloaded', severity: Severity.medium,
      title: "Rasmiy ilova do'kondan emas, fayldan o'rnatilgan",
      explain: "${org!.name} ilovasi $srcName. Xavfsizlik uchun uni o'chirib, Google Play'dan qayta o'rnating.",
      action: details,
    ));
  }

  final look = db.lookalikes[pkg];
  if (look != null) {
    out.add(Finding(
      code: 'app.lookalike', severity: look.infoOnly ? Severity.info : Severity.medium,
      title: "${look.claims}ning rasmiy ilovasi emas",
      explain: "Bu ilova o'zini ${look.claims} bilan bog'liq ko'rsatadi, lekin rasmiy emas: ${look.reason}. Unga shaxsiy yoki karta ma'lumotlarini kiritmang.",
      evidence: pkg, action: details,
    ));
  } else if (official == null && src != Source.system) {
    final o = brandMatch(label, db);
    if (o != null) {
      out.add(Finding(
        code: 'app.brand_impersonation', severity: sideloaded ? Severity.critical : Severity.medium,
        title: "${o.name} nomini ishlatadi, lekin rasmiy emas",
        explain: "Ilova nomi \"$label\", lekin u ${o.name}ning rasmiy ilovasi emas (rasmiy paket: ${o.packages.map((p) => p.id).join(', ')}).",
        evidence: pkg, action: details,
      ));
    }
  }

  if (app['accessibilityOn'] == true) {
    out.add(Finding(
      code: 'app.accessibility_on',
      severity: by(side: Severity.critical, store: Severity.medium),
      title: "Maxsus imkoniyatlar yoqilgan",
      explain: sideloaded
          ? "Fayldan o'rnatilgan bu ilova ekrandagi hamma narsani o'qiy oladi va siz uchun tugma bosa oladi. Bank troyanlari aynan shu bilan ishlaydi. O'zingiz yoqmagan bo'lsangiz, darhol o'chiring."
          : "Ilova ekranni o'qiy oladi va boshqara oladi. Agar bu sizga kerakli yordamchi ilova bo'lmasa, Maxsus imkoniyatlarda o'chiring.",
      action: const FindingAction("Maxsus imkoniyatlar", 'openAccessibility'),
    ));
  }
  if (app['notificationListenerOn'] == true) {
    out.add(Finding(
      code: 'app.notification_listener_on',
      severity: by(side: Severity.high, store: Severity.low),
      title: "Bildirishnomalarni o'qiydi",
      explain: "Ilova barcha bildirishnomalarni, jumladan bank SMS kodlarini o'qiy oladi.",
      action: const FindingAction("Bildirishnoma ruxsati", 'openNotificationAccess'),
    ));
  }
  if (app['deviceAdminOn'] == true) {
    out.add(Finding(
      code: 'app.device_admin_on',
      severity: by(side: Severity.critical, store: Severity.medium),
      title: "Qurilma administratori",
      explain: "Administrator huquqi ilovani o'chirishni qiyinlashtiradi. Avval Xavfsizlik → Administratorlar bo'limida huquqini oling, keyin o'chiring.",
      action: const FindingAction("Xavfsizlik sozlamalari", 'openSecurity'),
    ));
  }
  if (app['defaultSms'] == true && src != Source.system) {
    out.add(Finding(
      code: 'app.default_sms',
      severity: by(side: Severity.critical, store: Severity.medium),
      title: "Standart SMS ilovasi",
      explain: "Barcha SMS, jumladan bank kodlari, shu ilovaga keladi. Telefoningizning o'z SMS ilovasini qaytaring.",
      action: const FindingAction("Standart ilovalar", 'openDefaultApps'),
    ));
  }
  if (app['overlayAllowed'] == true && src != Source.system) {
    out.add(Finding(
      code: 'app.overlay',
      severity: by(side: Severity.high, store: Severity.low),
      title: "Boshqa ilovalar ustidan chiza oladi",
      explain: "Ilova bank ilovasi ustiga soxta kirish oynasini chiqarishi mumkin.",
      action: details,
    ));
  }
  if (app['installUnknownAllowed'] == true) {
    final isMessenger = db.messengerInstallers.containsKey(pkg);
    out.add(Finding(
      code: 'app.install_unknown',
      severity: isMessenger ? Severity.medium : by(side: Severity.high, store: Severity.low),
      title: isMessenger ? "$label APK o'rnata oladi" : "Boshqa ilovalarni o'rnata oladi",
      explain: isMessenger
          ? "$label ga \"noma'lum ilovalarni o'rnatish\" ruxsati berilgan. Telegram orqali kelgan troyan aynan shu ruxsat bilan bir bosishda o'rnatiladi. O'chirib qo'yish tavsiya etiladi."
          : "Ilova o'zi boshqa ilovalarni o'rnatishi mumkin (dropper belgisi).",
      action: FindingAction("Ruxsatni o'chirish", 'openUnknownSources', pkg),
    ));
  }

  final sms = granted.intersection({'android.permission.READ_SMS', 'android.permission.RECEIVE_SMS', 'android.permission.SEND_SMS'});
  if (sms.isNotEmpty && sideloaded && app['defaultSms'] != true) {
    out.add(Finding(
      code: 'app.sms_granted', severity: Severity.high,
      title: "SMS'larga ruxsat berilgan",
      explain: "Fayldan o'rnatilgan ilova SMS'larni o'qiy oladi. Bank kodlari xavf ostida.",
      evidence: sms.join(', '), action: details,
    ));
  }
  if (app['hasLauncher'] != true && sideloaded &&
      (app['accessibilityOn'] == true || sms.isNotEmpty || app['notificationListenerOn'] == true || app['deviceAdminOn'] == true)) {
    out.add(Finding(
      code: 'app.hidden_icon', severity: Severity.high,
      title: "Ikonkasi yashirilgan",
      explain: "Ilovaning bosh ekranda ikonkasi yo'q, lekin kuchli ruxsatlarga ega. Troyanlar o'zini shunday yashiradi.",
      action: details,
    ));
  }
  if (app['certDebug'] == true && sideloaded) {
    out.add(Finding(
      code: 'app.debug_cert', severity: Severity.medium,
      title: "Sinov (debug) kaliti bilan imzolangan",
      explain: "Rasmiy ilovalar debug kalit bilan tarqatilmaydi.",
      action: details,
    ));
  }
  return AppAudit(app, src, srcName, sortFindings(out));
}

List<Finding> evaluateDevice(Map<String, dynamic> d, {DateTime? now}) {
  final out = <Finding>[];
  if (d['screenLock'] == false) {
    out.add(const Finding(
      code: 'device.no_lock', severity: Severity.high,
      title: "Ekran qulfi yo'q",
      explain: "Telefon qo'ldan ketsa, bank ilovalari va SMS kodlar ochiq qoladi. PIN, parol yoki barmoq izini o'rnating.",
      action: FindingAction("Xavfsizlik sozlamalari", 'openSecurity'),
    ));
  }
  final root = _list(d['rootIndicators']);
  if (root.isNotEmpty) {
    out.add(Finding(
      code: 'device.root', severity: Severity.high,
      title: "Root belgilari topildi",
      explain: "Tizim himoyasi o'chirilgan bo'lishi mumkin. Bunday telefonda zararli dastur istalgan ilovaning ma'lumotiga kira oladi.",
      evidence: root.join(', '),
    ));
  }
  if (d['adbEnabled'] == true) {
    out.add(const Finding(
      code: 'device.adb', severity: Severity.medium,
      title: "USB orqali sozlash (ADB) yoqilgan",
      explain: "Kerak bo'lmasa, Dasturchi sozlamalarida \"USB orqali sozlash\"ni o'chiring.",
      action: FindingAction("Dasturchi sozlamalari", 'openDeveloperOptions'),
    ));
  } else if (d['developerOptions'] == true) {
    out.add(const Finding(
      code: 'device.dev_options', severity: Severity.low,
      title: "Dasturchi sozlamalari yoqilgan",
      explain: "Oddiy foydalanish uchun kerak emas. Firibgarlar \"yordam berish\" bahonasida shu sozlamalarni yoqtiradi.",
      action: FindingAction("Dasturchi sozlamalari", 'openDeveloperOptions'),
    ));
  }
  final patch = DateTime.tryParse((d['securityPatch'] as String?) ?? '');
  final today = now ?? DateTime.now();
  if (patch != null && today.difference(patch).inDays > 365) {
    out.add(Finding(
      code: 'device.old_patch', severity: Severity.medium,
      title: "Xavfsizlik yangilanishi eskirgan",
      explain: "Oxirgi xavfsizlik yangilanishi bir yildan oldin chiqqan. Telefon sozlamalaridan tizim yangilanishini tekshiring.",
      evidence: d['securityPatch'] as String?,
    ));
  }
  final sdk = d['sdkInt'] as int?;
  if (sdk != null && sdk < 29) {
    out.add(Finding(
      code: 'device.old_android', severity: Severity.medium,
      title: "Eski Android versiyasi",
      explain: "Android ${d['release']} endi xavfsizlik yangilanishlarini olmaydi.",
    ));
  }
  return sortFindings(out);
}

DeviceAudit evaluateAudit(Map<String, dynamic> raw, RostorDb db) {
  final apps = [
    for (final a in (raw['apps'] as List? ?? const [])) evaluateApp(Map<String, dynamic>.from(a as Map), db),
  ];
  final device = evaluateDevice(Map<String, dynamic>.from((raw['device'] as Map?) ?? const {}));
  return DeviceAudit(apps, device, DateTime.fromMillisecondsSinceEpoch((raw['scannedAt'] as int?) ?? 0));
}
