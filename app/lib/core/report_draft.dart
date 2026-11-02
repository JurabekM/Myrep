/// F3: hisobot qoralamasi — tekshiruv natijasidan (xabar, APK, qo'ng'iroq) forma maydonlarini
/// oldindan to'ldirish. Imzolash va normallashtirish Kotlin'da (report/ReportCodec.kt).
library;

import '../engine/apk_rules.dart';
import '../engine/text_rules.dart';
import 'phone.dart';
import 'risk.dart';

class EvidenceItem {
  EvidenceItem(this.kind, this.value, {this.include = true});
  final String kind; // sms_text | url | call | apk | note
  final String value;
  bool include;
}

class ReportDraft {
  ReportDraft({
    this.category,
    this.targetType = 'phone',
    this.targetValue = '',
    this.claimedOrg = '',
    List<EvidenceItem>? evidence,
    this.findings = const [],
  }) : evidence = evidence ?? [];

  String? category;
  String targetType;
  String targetValue;
  String claimedOrg;
  final List<EvidenceItem> evidence;
  /// ROSTOR-2 topilmalari: {code, title}. Kod — tahlil uchun, sarlavha — hisobotni o'qiydigan odam uchun.
  final List<Map<String, String>> findings;
}

const reportCategories = {
  'T1': "Messenjerda kelgan zararli APK",
  'T2': "\"Bank xavfsizlik xizmati\" qo'ng'irog'i",
  'T3': "Davlat idorasi nomidan qo'rqitish",
  'T4': "SIM-kartani almashtirish",
  'T5': "OLX va bozordagi soxta xaridor",
  'T6': "Oson daromad va investitsiya",
  'T7': "Telegram akkauntini egallash",
  'other': "Boshqa firibgarlik",
};

const reportTargetTypes = {
  'phone': 'Telefon raqami',
  'link': 'Havola yoki sayt',
  'apk': 'APK fayl (SHA-256)',
  'card': 'Firibgarning kartasi',
  'telegram': 'Telegram akkaunt',
  'other': 'Boshqa',
};

/// Topilma kodlaridan firibgarlik turini taxmin qilish (foydalanuvchi o'zgartira oladi).
String? guessCategory(Iterable<String> codes) {
  final c = codes.toSet();
  bool any(List<String> xs) => xs.any(c.contains);
  if (any(['text.receive_money_trap'])) return 'T5';
  if (any(['text.telegram_takeover', 'link.telegram_lure', 'link.telegram_bot'])) return 'T7';
  if (any(['text.apk_lure', 'link.apk'])) return 'T1';
  if (any(['text.authority_threat'])) return 'T3';
  if (any(['text.easy_money', 'text.prize'])) return 'T6';
  if (any(['text.otp_request', 'text.card_secret', 'text.account_blocked', 'text.phone_not_official'])) return 'T2';
  return null;
}

List<Map<String, String>> _signals(Iterable<Finding> fs) {
  final seen = <String>{};
  return [
    for (final f in sortFindings(fs.toList()))
      if (f.severity >= Severity.low && seen.add(f.code)) {'code': f.code, 'title': f.title},
  ];
}

ReportDraft draftFromText(TextReport r) {
  final codes = [...r.findings.map((f) => f.code), for (final l in r.links) ...l.findings.map((f) => f.code)];
  final phones = extractPhones(r.text);
  final badLink = r.links.where((l) => l.severity >= Severity.medium && l.host != null).firstOrNull;
  final org = r.findings.where((f) => f.code == 'text.phone_not_official').firstOrNull;
  return ReportDraft(
    category: guessCategory(codes),
    targetType: badLink != null && phones.isEmpty ? 'link' : (phones.isNotEmpty ? 'phone' : (badLink != null ? 'link' : 'phone')),
    targetValue: phones.isNotEmpty ? displayPhone(phones.first) : (badLink?.host ?? ''),
    claimedOrg: org == null ? '' : org.title.split(' nomidan').first,
    evidence: [
      EvidenceItem('sms_text', r.text),
      for (final l in r.links.where((l) => l.severity >= Severity.medium)) EvidenceItem('url', l.input),
    ],
    findings: _signals([...r.findings, for (final l in r.links) ...l.findings]),
  );
}

ReportDraft draftFromApk(ApkReport r) {
  final f = r.facts;
  return ReportDraft(
    category: 'T1',
    targetType: 'apk',
    targetValue: (f['fileSha256'] as String?) ?? '',
    claimedOrg: r.findings.any((x) => x.code.contains('brand') || x.code.contains('label_clone')) ? (r.label ?? '') : '',
    evidence: [
      EvidenceItem('apk', [
        if (f['fileName'] != null) 'fayl ${f['fileName']}',
        if (r.label != null) 'nomi "${r.label}"',
        if (r.packageName != null) 'paket ${r.packageName}',
        for (final s in (f['signers'] as List? ?? const [])) 'sertifikat ${(s as Map)['sha256']}',
      ].join(', ')),
    ],
    findings: _signals(r.findings),
  );
}

ReportDraft draftFromCall(Map<String, dynamic> entry, String when) => ReportDraft(
      category: 'T2',
      targetType: 'phone',
      targetValue: (entry['number'] as String?) ?? '',
      evidence: [EvidenceItem('call', "${entry['display']} — $when, ROSTOR-2: ${entry['title']}")],
      findings: [
        if (entry['code'] != null) {'code': entry['code'] as String, 'title': (entry['title'] as String?) ?? ''},
      ],
    );
