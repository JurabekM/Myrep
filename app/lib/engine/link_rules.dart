/// Havola Qalqoni (T2, T5, T6, T7): URL'ni internetga chiqmasdan tahlil qiladi.
library;

import '../core/db.dart';
import '../core/risk.dart';
import 'domain_tools.dart';

class LinkReport {
  LinkReport(this.input, this.host, this.findings);
  final String input;
  final String? host;
  final List<Finding> findings;
  Severity get severity => worstOf(findings);
}

/// Brend nomi bilan birga kelganda shubhali bo'ladigan qo'shimchalar ("clickuz", "paymebonus").
const _brandSuffixLures = {
  'uz', 'pay', 'bonus', 'sovga', 'gift', 'bank', 'card', 'karta', 'online', 'login',
  'verify', 'secure', 'app', 'promo', 'aksiya', 'prize', 'support', 'help', 'money',
};

const _telegramHosts = {'t.me', 'telegram.me', 'telegram.dog'};
const _telegramLures = ['vote', 'golos', 'ovoz', 'bonus', 'premium', 'prize', 'sovga', 'gift', 'konkurs', 'aksiya', 'free', 'tekin'];

final RegExp _urlInText = RegExp(
  r'''(?:https?://|www\.)[^\s<>"']+|(?<![@\w.])(?:[a-z0-9-]+\.)+(?:uz|com|ru|net|org|me|top|xyz|site|online|shop|click|info|io|app|link|live|store|icu|buzz|cc|biz|pro|tk|ly|su|gd|id|to|at|gl|kz|tj|kg|co|ws|pw)(?:/[^\s<>"']*)?''',
  caseSensitive: false,
);

/// Matndan havolalarni ajratib oladi (oxiridagi tinish belgilarisiz).
List<String> extractUrls(String text) {
  final out = <String>[];
  for (final m in _urlInText.allMatches(text)) {
    var u = m.group(0)!;
    while (u.isNotEmpty && '.,;:!?)»"\''.contains(u[u.length - 1])) {
      u = u.substring(0, u.length - 1);
    }
    if (u.isNotEmpty && !out.contains(u)) out.add(u);
  }
  return out;
}

LinkReport analyzeUrl(String raw, RostorDb db) {
  final input = raw.trim();
  final findings = <Finding>[];
  final withScheme = RegExp(r'^[a-z][a-z0-9+.-]*://', caseSensitive: false).hasMatch(input) ? input : 'http://$input';
  final uri = Uri.tryParse(withScheme);
  if (uri == null || uri.host.isEmpty) {
    return LinkReport(input, null, [
      const Finding(code: 'link.unparsable', severity: Severity.info, title: "Bu havola emas", explain: "Matnda tekshiriladigan veb-manzil topilmadi."),
    ]);
  }

  var host = uri.host.toLowerCase();
  if (host.endsWith('.')) host = host.substring(0, host.length - 1);
  final unicodeHost = decodeIdnHost(host);
  final reg = registrableDomain(host);
  final regLabel = firstLabel(reg);
  final official = db.orgByDomain(host);

  if (uri.userInfo.isNotEmpty) {
    findings.add(Finding(
      code: 'link.userinfo',
      severity: Severity.critical,
      title: "Manzil aldamchi tuzilgan",
      explain: "'@' belgisidan oldingi qism hech narsani anglatmaydi. Brauzer aslida $host saytini ochadi. Bu usul ishonchli nomni ko'rsatib, boshqa saytga olib borish uchun ishlatiladi.",
      evidence: uri.userInfo,
    ));
  }

  if (db.maliciousDomains.contains(host) || db.maliciousDomains.contains(reg)) {
    findings.add(Finding(
      code: 'link.malicious',
      severity: Severity.critical,
      title: "Firibgarlik sayti (bazada)",
      explain: "Bu domen ROSTOR-2 bazasida firibgarlik sayti sifatida qayd etilgan. Ochmang va hech qanday ma'lumot kiritmang.",
      evidence: reg,
    ));
  }

  if (isIpv4(host)) {
    findings.add(const Finding(
      code: 'link.ip',
      severity: Severity.high,
      title: "Sayt nomi o'rniga IP manzil",
      explain: "Rasmiy bank va davlat saytlari raqamli IP manzildan foydalanmaydi. Bunday havolalar odatda vaqtinchalik firibgarlik sahifalariga olib boradi.",
    ));
  }

  // Gomoglif: boshqa alifbo harflari yoki raqamlar bilan rasmiy domenni taqlid qilish.
  if (official == null) {
    final hostSkel = skeleton(unicodeHost);
    final regSkel = skeleton(decodeIdnHost(reg));
    for (final d in db.officialDomains) {
      if (hostSkel == skeleton(d) || regSkel == skeleton(d)) {
        findings.add(Finding(
          code: 'link.homoglyph',
          severity: Severity.critical,
          title: "Rasmiy saytning soxta nusxasi",
          explain: "Bu manzil ko'zga $d ga juda o'xshaydi, lekin u emas: ba'zi harflar boshqa alifbodan yoki raqam bilan almashtirilgan. Ochmang.",
          evidence: hasNonAscii(unicodeHost) ? '$unicodeHost ($host)' : host,
        ));
        break;
      }
    }
  }
  if (hasNonAscii(unicodeHost) && unicodeHost.split('.').any(mixedScripts)) {
    findings.add(Finding(
      code: 'link.mixed_script',
      severity: Severity.high,
      title: "Lotin va kirill harflari aralash",
      explain: "Domen nomida turli alifbo harflari aralashtirilgan. Bu ko'pincha mashhur sayt nomini taqlid qilish uchun qilinadi.",
      evidence: '$unicodeHost ($host)',
    ));
  }

  if (official == null && !findings.any((f) => f.code == 'link.homoglyph')) {
    // O'xshash nom va brend nomini suiiste'mol qilish.
    final labels = host.split('.').expand((l) => l.split('-')).toList();
    Organization? brandHit;
    String? brandWord;
    var exactToken = false;
    for (final o in db.organizations) {
      // Kalit so'zlar (3+ harf, aniq tokenda) va rasmiy domen nomlari (5+ harf: "mobi" kabi
      // qisqa nomlar tasodifiy saytlarga ham mos kelib qoladi).
      final words = {
        for (final k in o.brandKeywords) k.replaceAll(RegExp('[^a-z0-9]'), ''),
        for (final d in o.domains) firstLabel(registrableDomain(d)),
      }.where((w) => w.length >= 3 && (o.brandKeywords.any((k) => k.replaceAll(RegExp('[^a-z0-9]'), '') == w) || w.length >= 5));
      for (final w in words) {
        if (labels.contains(w)) {
          brandHit = o;
          brandWord = w;
          exactToken = true;
          break;
        }
        for (final l in labels) {
          if (w.length >= 4 && l.length > w.length && (l.startsWith(w) || l.endsWith(w))) {
            final rest = l.startsWith(w) ? l.substring(w.length) : l.substring(0, l.length - w.length);
            if (_brandSuffixLures.contains(rest)) {
              brandHit = o;
              brandWord = w;
            }
          }
        }
      }
      if (exactToken) break;
    }
    if (brandHit != null) {
      findings.add(Finding(
        code: 'link.brand_abuse',
        severity: Severity.high,
        title: "${brandHit.name} nomi begona saytda",
        explain: "Manzilda \"$brandWord\" so'zi bor, lekin bu ${brandHit.name}ning rasmiy domeni emas."
            "${brandHit.domains.isEmpty ? '' : ' Rasmiy manzil: ${brandHit.domains.join(', ')}.'}",
        evidence: host,
      ));
    } else if (regLabel.length >= 4) {
      for (final d in db.officialDomains) {
        final ol = firstLabel(registrableDomain(d));
        if (ol.length < 5 || ol == regLabel) continue;
        final dist = levenshtein(regLabel, ol);
        if (dist > 0 && dist <= (ol.length >= 7 ? 2 : 1)) {
          findings.add(Finding(
            code: 'link.lookalike',
            severity: Severity.high,
            title: "Rasmiy saytga o'xshash nom",
            explain: "\"$reg\" nomi rasmiy $d dan bir-ikki harf bilan farq qiladi. Firibgarlar shunday nomlarni ataylab tanlaydi.",
            evidence: '$reg ~ $d',
          ));
          break;
        }
      }
    }
  }

  if (db.shorteners.contains(host)) {
    findings.add(const Finding(
      code: 'link.shortener',
      severity: Severity.medium,
      title: "Haqiqiy manzil yashirilgan",
      explain: "Bu qisqartirilgan havola. U qaysi saytga olib borishini oldindan bilib bo'lmaydi. Bank yoki davlat xabarlarida bunday havolalar ishlatilmaydi.",
    ));
  }

  final tld = host.contains('.') ? host.substring(host.lastIndexOf('.') + 1) : '';
  if (db.riskyTlds.contains(tld)) {
    findings.add(Finding(
      code: 'link.risky_tld',
      severity: Severity.medium,
      title: "Arzon va shubhali domen zonasi",
      explain: ".$tld zonasidagi domenlar juda arzon va ko'pincha bir martalik firibgarlik saytlari uchun olinadi.",
      evidence: '.$tld',
    ));
  }

  if (_telegramHosts.contains(host)) {
    final path = uri.path.toLowerCase();
    final full = '$path?${uri.query}'.toLowerCase();
    final lure = _telegramLures.where(full.contains).toList();
    if (lure.isNotEmpty) {
      findings.add(Finding(
        code: 'link.telegram_lure',
        severity: Severity.high,
        title: "Telegram akkauntini o'g'irlash usuli",
        explain: "\"Ovoz bering\", \"bonus\" yoki \"Premium\" va'dasi bilan kelgan bot sizdan telefon raqami va Telegram kirish kodini so'raydi. Kodni kiritsangiz, akkaunt firibgarga o'tadi.",
        evidence: lure.join(', '),
      ));
    } else if (RegExp(r'^/[a-z0-9_]+bot\b').hasMatch(path)) {
      findings.add(const Finding(
        code: 'link.telegram_bot',
        severity: Severity.low,
        title: "Telegram bot havolasi",
        explain: "Botga hech qachon Telegram kirish kodini, karta ma'lumotini yoki SMS kodni yubormang.",
      ));
    }
  }

  if (uri.path.toLowerCase().endsWith('.apk')) {
    findings.add(const Finding(
      code: 'link.apk',
      severity: Severity.high,
      title: "To'g'ridan-to'g'ri APK yuklab olish",
      explain: "Havola ilova faylini yuklaydi. Ilovalarni faqat Google Play yoki ishlab chiqaruvchining do'konidan o'rnating.",
    ));
  }

  if (uri.scheme == 'http' && RegExp(r'^https?://', caseSensitive: false).hasMatch(input)) {
    findings.add(const Finding(
      code: 'link.no_tls',
      severity: Severity.medium,
      title: "Shifrlanmagan aloqa (http)",
      explain: "Sahifaga kiritilgan ma'lumotlar ochiq holda uzatiladi. Bunday sahifada parol yoki karta ma'lumotini kiritmang.",
    ));
  }

  if (host.split('.').length > 5 || '-'.allMatches(reg).length >= 3) {
    findings.add(const Finding(
      code: 'link.complex',
      severity: Severity.low,
      title: "G'ayrioddiy murakkab manzil",
      explain: "Juda ko'p nuqta yoki chiziqchali manzillar haqiqiy nomni yashirish uchun ishlatiladi.",
    ));
  }

  if (official != null && !findings.any((f) => f.severity >= Severity.high)) {
    findings.add(Finding(
      code: 'link.official',
      severity: Severity.ok,
      title: "Rasmiy domen: ${official.name}",
      explain: "Bu manzil ${official.name}ning bazadagi rasmiy domeniga tegishli. Shunga qaramay, sahifa sizdan SMS kod yoki CVV so'rasa, to'xtang.",
      evidence: host,
    ));
  }

  if (findings.isEmpty) {
    findings.add(const Finding(
      code: 'link.no_signal',
      severity: Severity.info,
      title: "Ma'lum xavf belgisi topilmadi",
      explain: "Bu xavfsizlik kafolati emas: yangi firibgarlik saytlari bazada bo'lmasligi mumkin. Sayt SMS kod, karta muddati yoki CVV so'rasa, kiritmang.",
    ));
  }
  return LinkReport(input, host, sortFindings(findings));
}
