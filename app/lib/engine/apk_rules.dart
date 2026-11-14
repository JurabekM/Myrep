/// APK Qalqon (T1) qoidalari. Kirish — ApkInspector.kt yig'gan faktlar; chiqish —
/// izohli topilmalar. Asosiy g'oya (ROSTOR-1 §16): ishonch nomga emas, Android imzo
/// sertifikatiga bog'lanadi.
library;

import '../core/db.dart';
import '../core/risk.dart';
import 'normalize.dart';

class ApkReport {
  ApkReport(this.facts, this.findings);
  final Map<String, dynamic> facts;
  final List<Finding> findings;
  Severity get severity => worstOf(findings);

  String? get label => facts['label'] as String?;
  String? get packageName => facts['packageName'] as String?;
}

const _smsPerms = {'android.permission.RECEIVE_SMS', 'android.permission.READ_SMS', 'android.permission.SEND_SMS'};
const _callPerms = {
  'android.permission.READ_CALL_LOG', 'android.permission.CALL_PHONE',
  'android.permission.PROCESS_OUTGOING_CALLS', 'android.permission.ANSWER_PHONE_CALLS',
};
const _lureWords = [
  'soliq', 'mygov', 'yangilanish', 'rasm', 'foto', 'video', 'hujjat', 'jarima', 'sud', 'iiv', 'iib',
  'bank', 'click', 'payme', 'uzum', 'humo', 'uzcard', 'tekshiruv', 'document', 'update', 'photo', 'pdf',
  'shtraf', 'dokument', 'kompensatsiya', 'yordam', 'nafaqa', 'subsidiya',
];

List<String> _list(Object? v) => [for (final x in (v as List? ?? const [])) x as String];
List<Map<String, dynamic>> _maps(Object? v) => [for (final x in (v as List? ?? const [])) Map<String, dynamic>.from(x as Map)];

ApkReport evaluateApk(Map<String, dynamic> f, RostorDb db) {
  final out = <Finding>[];
  if (f['ok'] != true) {
    out.add(Finding(
      code: 'apk.read_error',
      severity: Severity.info,
      title: "Faylni tekshirib bo'lmadi",
      explain: (f['error'] as String?) ?? "Noma'lum xato",
    ));
    return ApkReport(f, out);
  }

  final fileName = (f['fileName'] as String?) ?? '';
  final lowerName = fileName.toLowerCase();
  final signers = _maps(f['signers']);
  final certs = [for (final s in signers) (s['sha256'] as String).toLowerCase()];
  final lineage = _list(f['lineage']).map((s) => s.toLowerCase()).toSet();
  final perms = _list(f['permissions']).toSet();
  final pkg = f['packageName'] as String?;
  final label = (f['label'] as String?) ?? '';

  if (f['parsed'] != true && f['sigVerified'] != true) {
    final bundle = lowerName.endsWith('.xapk') || lowerName.endsWith('.apks') || lowerName.endsWith('.apkm');
    out.add(Finding(
      code: bundle ? 'apk.bundle_format' : 'apk.invalid',
      severity: bundle ? Severity.medium : Severity.high,
      title: bundle ? "Bo'lingan APK to'plami (XAPK/APKS)" : "Yaroqli APK emas",
      explain: bundle
          ? "Bunday to'plamlar Play'dan emas, uchinchi tomon saytlaridan keladi. Ichidagi fayllarni alohida tekshirib bo'lmaydi; o'rnatmang."
          : "Fayl shikastlangan yoki APK sifatida niqoblangan boshqa fayl. O'rnatishga urinmang.",
      evidence: fileName,
    ));
    return ApkReport(f, sortFindings(out));
  }

  // --- Imzo -------------------------------------------------------------------------------
  if (f['sigVerified'] != true) {
    out.add(Finding(
      code: 'apk.sig_invalid',
      severity: Severity.critical,
      title: "Imzo buzilgan",
      explain: "Fayl imzolangandan keyin o'zgartirilgan yoki umuman imzolanmagan. Bunday ilovaga mutlaqo ishonib bo'lmaydi.",
      evidence: _list(f['sigErrors']).take(2).join('; '),
    ));
  }

  final hash = (f['fileSha256'] as String?)?.toLowerCase();
  if (hash != null && db.maliciousApk.contains(hash)) {
    out.add(Finding(
      code: 'apk.malicious_hash',
      severity: Severity.critical,
      title: "Ma'lum zararli fayl (bazada)",
      explain: "Bu aynan ROSTOR-2 bazasida zararli deb qayd etilgan fayl. O'rnatmang va o'chiring.",
      evidence: hash,
    ));
  }
  final badCert = certs.where(db.maliciousCerts.contains).toList();
  if (badCert.isNotEmpty) {
    out.add(Finding(
      code: 'apk.malicious_cert',
      severity: Severity.critical,
      title: "Zararli dasturchi kaliti (bazada)",
      explain: "Fayl ilgari zararli ilovalarni imzolagan kalit bilan imzolangan.",
      evidence: badCert.first,
    ));
  }

  // --- Rasmiy nashriyotchi va o'rnatilgan nusxa (TOFU) --------------------------------------
  var trustedSigner = false;
  final official = pkg == null ? null : db.officialPackage(pkg);
  final officialOrg = pkg == null ? null : db.orgByPackage(pkg);
  if (official != null && official.certSha256.isNotEmpty && certs.isNotEmpty) {
    final match = certs.any(official.certSha256.contains) || lineage.any(official.certSha256.contains);
    if (match) {
      trustedSigner = true;
      out.add(Finding(
        code: 'apk.official_signer',
        severity: Severity.ok,
        title: "Rasmiy nashriyotchi imzosi: ${officialOrg!.name}",
        explain: "Imzo sertifikati bazadagi ${officialOrg.name} sertifikatiga mos keladi.",
        evidence: certs.first,
      ));
    } else {
      out.add(Finding(
        code: 'apk.official_mismatch',
        severity: Severity.critical,
        title: "${officialOrg!.name} ilovasining soxta nusxasi",
        explain: "Paket nomi ${officialOrg.name}niki, lekin imzo boshqa kalit bilan qo'yilgan. Haqiqiy ilova faqat rasmiy kalit bilan imzolanadi. O'rnatmang.",
        evidence: certs.first,
      ));
    }
  }

  final installed = f['installed'] == null ? null : Map<String, dynamic>.from(f['installed'] as Map);
  if (installed != null && certs.isNotEmpty) {
    final known = {..._list(installed['certSha256']), ..._list(installed['historySha256'])}.map((s) => s.toLowerCase()).toSet();
    final same = certs.any(known.contains) || lineage.any(known.contains);
    final inst = Map<String, dynamic>.from((installed['installer'] as Map?) ?? const {});
    final where = _installerName(inst, db);
    // TOFU faqat do'kondan kelgan nusxaga ishonadi: fayldan o'rnatilgan nusxa bilan bir xil
    // imzo hech narsani isbotlamaydi (zararli ilovaning o'z yangilanishi ham shunday bo'ladi).
    final fromStore = db.trustedInstallers.containsKey(inst['installing']);
    if (same && fromStore) {
      trustedSigner = true;
      out.add(Finding(
        code: 'apk.same_as_installed',
        severity: Severity.ok,
        title: "Telefoningizdagi ilova bilan bir xil imzo",
        explain: "Bu fayl $where'dan o'rnatilgan \"$label\" bilan bir xil kalit bilan imzolangan, ya'ni uning yangilanishi bo'lishi mumkin.",
        evidence: certs.first,
      ));
    } else if (same) {
      out.add(Finding(
        code: 'apk.same_as_sideloaded',
        severity: Severity.info,
        title: "Bu ilova telefoningizda allaqachon bor",
        explain: "\"$label\" ilgari ham do'kondan emas, fayldan o'rnatilgan ($where). Bir xil imzo uning haqiqiyligini isbotlamaydi — quyidagi belgilarga qarang.",
        evidence: certs.first,
      ));
    } else {
      out.add(Finding(
        code: 'apk.installed_mismatch',
        severity: Severity.critical,
        title: "O'rnatilgan ilovaning soxta nusxasi",
        explain: "Telefoningizda shu paket nomli \"$label\" bor ($where), lekin bu fayl boshqa kalit bilan imzolangan. Bu ilovani almashtirishga urinish.",
        evidence: certs.first,
      ));
    }
  }

  for (final other in _maps(f['sameLabelInstalled'])) {
    final where = _installerName(Map<String, dynamic>.from((other['installer'] as Map?) ?? const {}), db);
    out.add(Finding(
      code: 'apk.label_clone',
      severity: Severity.critical,
      title: "\"${other['label']}\" ilovasini taqlid qiladi",
      explain: "Telefoningizda xuddi shu nomli ilova bor ($where), lekin bu fayl boshqa paket. Firibgarlar mashhur ilova nomini aynan shunday ko'chiradi.",
      evidence: "${other['packageName']} ≠ $pkg",
    ));
  }

  final look = pkg == null ? null : db.lookalikes[pkg];
  if (look != null) {
    out.add(Finding(
      code: 'apk.lookalike',
      severity: look.infoOnly ? Severity.info : Severity.high,
      title: "${look.claims}ning rasmiy ilovasi emas",
      explain: "Bu ilova o'zini ${look.claims} bilan bog'liq ko'rsatadi, lekin tekshiruvda rasmiy emasligi aniqlangan: ${look.reason}.",
      evidence: pkg,
    ));
  } else if (official == null && pkg != null) {
    final o = brandMatch(label, db);
    if (o != null) {
      out.add(Finding(
        code: 'apk.brand_impersonation',
        severity: Severity.critical,
        title: "${o.name} nomini suiiste'mol qiladi",
        explain: "Ilova nomi \"$label\", lekin uning paketi ${o.name}ning rasmiy ilovasi emas. Rasmiy paket: ${o.packages.map((p) => p.id).join(', ')}.",
        evidence: pkg,
      ));
    }
  }

  // --- Imzo sifati --------------------------------------------------------------------------
  if (signers.any((s) => s['debug'] == true)) {
    out.add(const Finding(
      code: 'apk.debug_cert',
      severity: Severity.high,
      title: "Sinov (debug) kaliti bilan imzolangan",
      explain: "Rasmiy ilovalar hech qachon debug kalit bilan tarqatilmaydi. Bunday fayl tez-tez qo'lda yasalgan zararli dastur bo'ladi.",
    ));
  }
  final schemes = _list(f['sigSchemes']);
  if (schemes.length == 1 && schemes.first == 'v1') {
    out.add(const Finding(
      code: 'apk.v1_only',
      severity: Severity.medium,
      title: "Eskirgan imzo sxemasi (faqat v1)",
      explain: "Zamonaviy ilovalar v2/v3 imzodan foydalanadi. Faqat v1 imzo eski yoki qo'lda o'zgartirilgan faylga xos.",
    ));
  }
  final target = f['targetSdk'] as int?;
  if (target != null && target < 26) {
    out.add(Finding(
      code: 'apk.old_target',
      severity: Severity.medium,
      title: "Eski Android uchun yozilgan (targetSdk $target)",
      explain: "Zararli dasturlar ruxsatlarni so'rovsiz olish uchun ataylab eski Android versiyasini nishonga oladi. Play bunday ilovalarni qabul qilmaydi.",
    ));
  }

  // --- Xavfli imkoniyatlar ------------------------------------------------------------------
  final a11y = _list(f['accessibilityServices']);
  final sms = perms.intersection(_smsPerms);
  if (a11y.isNotEmpty && sms.isNotEmpty) {
    out.add(Finding(
      code: 'apk.banker_combo',
      severity: trustedSigner ? Severity.medium : Severity.critical,
      title: "Bank troyani belgisi: SMS + Maxsus imkoniyatlar",
      explain: "Ilova SMS'larni o'qish va ekrandagi hamma narsani boshqarish imkoniyatini birga so'raydi. Bu SMS kodlarni o'g'irlab, kartadan pul yechadigan troyanlarning aniq belgisi.",
      evidence: [...sms, 'AccessibilityService'].join(', '),
    ));
  } else {
    if (a11y.isNotEmpty) {
      out.add(Finding(
        code: 'apk.accessibility',
        severity: trustedSigner ? Severity.low : Severity.high,
        title: "Maxsus imkoniyatlar xizmati",
        explain: "Ilova ekrandagi matnni o'qish va siz uchun tugmalarni bosish imkoniyatini so'raydi. O'rnatilgach, uni \"Maxsus imkoniyatlar\"da yoqishni so'rasa, rad eting.",
        evidence: a11y.first,
      ));
    }
    if (sms.isNotEmpty) {
      out.add(Finding(
        code: 'apk.sms',
        severity: trustedSigner ? Severity.low : Severity.high,
        title: "SMS'larni o'qish yoki yuborish",
        explain: "Ilova SMS'larga kirish so'raydi. Bank kodlari SMS orqali keladi, shuning uchun bu ruxsat o'g'rilar uchun eng qimmatli.",
        evidence: sms.join(', '),
      ));
    }
  }
  if (_list(f['notificationListeners']).isNotEmpty) {
    out.add(Finding(
      code: 'apk.notification_listener',
      severity: trustedSigner ? Severity.low : Severity.high,
      title: "Bildirishnomalarni o'qish",
      explain: "Ilova barcha bildirishnomalarni, jumladan bank SMS kodlarini o'qiy oladi.",
    ));
  }
  if (_list(f['deviceAdmins']).isNotEmpty) {
    out.add(Finding(
      code: 'apk.device_admin',
      severity: trustedSigner ? Severity.low : Severity.high,
      title: "Qurilma administratori",
      explain: "Administrator huquqi ilovani oddiy usul bilan o'chirib bo'lmaydigan qiladi va ekranni qulflay oladi.",
    ));
  }
  if (perms.contains('android.permission.REQUEST_INSTALL_PACKAGES')) {
    out.add(Finding(
      code: 'apk.dropper',
      severity: trustedSigner ? Severity.low : Severity.high,
      title: "Boshqa ilovalarni o'rnata oladi",
      explain: "Bu \"dropper\" belgisi: bir zararsiz ko'rinadigan ilova keyin asl troyanni yuklab o'rnatadi.",
    ));
  }
  if (perms.contains('android.permission.SYSTEM_ALERT_WINDOW')) {
    out.add(Finding(
      code: 'apk.overlay',
      severity: trustedSigner ? Severity.info : Severity.medium,
      title: "Boshqa ilovalar ustidan oyna",
      explain: "Ilova bank ilovasi ustiga soxta kirish oynasini chizishi mumkin.",
    ));
  }
  final calls = perms.intersection(_callPerms);
  if (calls.isNotEmpty) {
    out.add(Finding(
      code: 'apk.calls',
      severity: trustedSigner ? Severity.info : Severity.medium,
      title: "Qo'ng'iroqlarni boshqarish",
      explain: "Ilova qo'ng'iroqlar jurnalini o'qiydi yoki qo'ng'iroqqa aralasha oladi.",
      evidence: calls.join(', '),
    ));
  }

  // --- Fayl nomi ----------------------------------------------------------------------------
  if (RegExp(r'\.(jpe?g|png|pdf|docx?|mp4|txt)\.apk$').hasMatch(lowerName)) {
    out.add(Finding(
      code: 'apk.double_ext',
      severity: Severity.high,
      title: "Ikki kengaytmali fayl nomi",
      explain: "\"$fileName\" rasm yoki hujjat bo'lib ko'rinadi, lekin aslida ilova. Bu ataylab aldash.",
      evidence: fileName,
    ));
  } else if (!trustedSigner && _lureWords.any(normalizeText(fileName).contains)) {
    out.add(Finding(
      code: 'apk.lure_name',
      severity: Severity.medium,
      title: "Ishonch uyg'otuvchi fayl nomi",
      explain: "Fayl nomi rasmiy idora, bank yoki shaxsiy rasm/hujjatga o'xshatib tanlangan. Telegram orqali tarqaladigan troyanlar aynan shunday nomlanadi.",
      evidence: fileName,
    ));
  }

  if (out.every((x) => x.severity <= Severity.low)) {
    out.add(const Finding(
      code: 'apk.no_signal',
      severity: Severity.info,
      title: "Jiddiy xavf belgisi topilmadi",
      explain: "Bu ilovaning xavfsizligiga kafolat emas. Ilovalarni Google Play'dan o'rnatish eng ishonchli yo'l.",
    ));
  }
  return ApkReport(f, sortFindings(out));
}

String _installerName(Map<String, dynamic> inst, RostorDb db) {
  final installing = inst['installing'] as String?;
  final initiating = inst['initiating'] as String?;
  if (installing != null && db.trustedInstallers.containsKey(installing)) return db.trustedInstallers[installing]!;
  if (initiating != null && db.messengerInstallers.containsKey(initiating)) return "${db.messengerInstallers[initiating]} orqali kelgan fayldan";
  if (installing == null && initiating == null) return "manbasi noma'lum";
  return 'APK fayldan';
}

String installerName(Map<String, dynamic> inst, RostorDb db) => _installerName(inst, db);

/// Ilova nomida rasmiy ilovasi bor tashkilot brendi so'z sifatida uchraydimi ("Click Bonus").
Organization? brandMatch(String label, RostorDb db) {
  final normLabel = normalizeText(label);
  if (normLabel.isEmpty) return null;
  for (final o in db.organizations) {
    if (o.packages.isEmpty) continue;
    final words = {...o.brandKeywords, normalizeText(o.name)}.where((w) => w.length >= 3);
    if (words.any((w) => RegExp('(^|[^a-z0-9])${RegExp.escape(w)}(\$|[^a-z0-9])').hasMatch(normLabel))) return o;
  }
  return null;
}
