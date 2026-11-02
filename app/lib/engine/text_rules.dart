/// Xabar tekshiruvi (T2, T3, T5, T6, T7): SMS yoki messenjer matnidagi firibgarlik
/// naqshlari. Matn o'zbek (lotin/kirill) va rus tilida bo'lishi mumkin — normalize.dart
/// hammasini lotin ko'rinishiga keltiradi, shuning uchun naqshlar lotincha yozilgan.
library;

import '../core/db.dart';
import '../core/phone.dart';
import '../core/risk.dart';
import 'link_rules.dart';
import 'normalize.dart';

class TextReport {
  TextReport(this.text, this.findings, this.links);
  final String text;
  final List<Finding> findings;
  final List<LinkReport> links;
  Severity get severity {
    final all = [...findings, for (final l in links) ...l.findings];
    return worstOf(all);
  }
}

class _Rule {
  const _Rule(this.code, this.severity, this.title, this.explain, this.patterns);
  final String code;
  final Severity severity;
  final String title;
  final String explain;
  final List<String> patterns;
}

const _verbsRequest = r"(ayt|yubor|yoz|kirit|ber|jo'nat|nazovi|soobshch|prodiktu|skazhi|otprav|napishi|vvedi)";

const List<_Rule> _rules = [
  _Rule(
    'text.otp_request', Severity.critical,
    "SMS kodni so'rash",
    "Bank, IIV, operator yoki boshqa hech bir tashkilot xodimi SMS kodni so'ramaydi. Kodni aytsangiz, firibgar sizning nomingizdan pul o'tkazadi yoki akkauntingizga kiradi.",
    [
      "(sms|tasdiqlash|bir martalik|maxfiy|kelgan)\\s+kod\\w*\\s+(\\w+\\s+)?$_verbsRequest",
      "kod\\w*\\s+(bizga\\s+|menga\\s+)?$_verbsRequest\\w*",
      "kod iz sms",
      "(nazovite|soobshchite|prodiktuyte|skazhite)\\s+(nam\\s+|mne\\s+)?(kod|parol|tsifr)",
    ],
  ),
  _Rule(
    'text.card_secret', Severity.critical,
    "Karta maxfiy ma'lumotini so'rash",
    "Kartaning amal qilish muddati, CVV/CVC yoki orqasidagi 3 raqam faqat siz to'lov qilganingizda kerak. Ularni so'ragan odam pulingizni yechib olmoqchi.",
    [
      "\\bcvv\\b", "\\bcvc\\b", "amal qilish muddat", "srok deystviya",
      "orqa(si|sidagi|dagi)\\s+(3|uch)", "kod na oborote", "tri tsifry",
    ],
  ),
  _Rule(
    'text.receive_money_trap', Severity.critical,
    "\"Pul olish uchun\" karta ma'lumoti",
    "Pul QABUL qilish uchun faqat karta raqami yetarli. Muddat, CVV yoki SMS kod hech qachon kerak emas (ROSTOR-1 P5 invarianti). Bu OLX va bozorlardagi klassik firibgarlik.",
    [
      "pul(ni)?\\s+(olish|qabul qilish|olishingiz)\\s+uchun",
      "to'lov(ni)?\\s+qabul qil",
      "(poluchit|poluchenie|polucheniya)\\s+(deneg|dengi|oplat|perevod|sredstv)",
      "dlya polucheniya",
    ],
  ),
  _Rule(
    'text.authority_threat', Severity.high,
    "Davlat idorasi nomidan qo'rqitish",
    "\"Jinoiy ish\", \"sud\", \"militsiya\" kabi so'zlar bilan qo'rqitib, shoshilinch to'lov yoki ma'lumot so'rash — firibgarlik. Rasmiy idoralar bunday xabar yubormaydi; 102 ga o'zingiz qo'ng'iroq qilib tekshiring.",
    [
      "jinoiy ish", "sudga (chaqiril|beril|oshir)", "ugolovn(oe|ogo) del", "qamoq", "hibsga",
      "(iib|iiv|militsiya|prokuratura|mvd|fsb|politsiya|davlat xavfsizlik).{0,60}(to'la|o'tkaz|karta|kod|hisob|shubhali)",
    ],
  ),
  _Rule(
    'text.account_blocked', Severity.high,
    "\"Hisobingiz bloklandi\" bahonasi",
    "Bank xavotirga solib, \"shubhali operatsiyani bekor qilish\" uchun kod yoki o'tkazma so'rasa — bu firibgarlik. Bankka kartaning orqasidagi raqam orqali o'zingiz qo'ng'iroq qiling.",
    [
      "(hisob|karta|akkaunt)\\w*\\s+(bloklan|muzlatil|to'xtatil|o'chiril)",
      "shubhali (operatsiya|tranzaksiya|to'lov|o'tkazma)",
      "(kart|schet)\\w*\\s+zablokir", "podozritel'?n\\w*\\s+operats",
    ],
  ),
  _Rule(
    'text.prize', Severity.high,
    "Yutuq yoki sovg'a va'dasi",
    "Siz qatnashmagan tanlovdan \"yutuq\" — firibgarlik. Odatda \"sovg'ani olish uchun\" to'lov yoki karta ma'lumoti so'raladi.",
    ["yutib oldingiz", "g'olib bo'ldingiz", "sovrin", "yutuq(ni|ingiz)", "vy vyigrali", "vash priz", "sovg'a(ni|ngiz)? olish"],
  ),
  _Rule(
    'text.easy_money', Severity.high,
    "Oson daromad yoki investitsiya va'dasi",
    "Kafolatlangan yuqori daromad, \"kuniga 100\$\" yoki oldindan to'lov talab qiladigan ish — firibgarlik sxemasi. Pulingiz qaytmaydi.",
    [
      "kafolatlangan (foyda|daromad)", "garantirovann\\w+ (doxod|pribyl)", "passiv daromad",
      "kuniga.{0,20}(\\\$|dollar|ming|so'm)", "uydan turib.{0,20}(ish|daromad)", "oldindan to'lov", "predoplat",
      "investitsiya.{0,40}(foyda|daromad|%)", "kripto.{0,40}(foyda|daromad|x2|ikki baravar)",
    ],
  ),
  _Rule(
    'text.apk_lure', Severity.high,
    "Ilova faylini o'rnatishga undash",
    "Xabar orqali kelgan .apk fayl Telegram orqali tarqaladigan SMS-o'g'ri troyanlarning asosiy yo'li. Ilovalarni faqat Google Play'dan o'rnating.",
    ["\\.apk\\b", "ilova(ni)?\\s+(o'rnating|yuklab oling|o'rnatib oling)", "ustanovite prilojenie", "skachayte prilojenie"],
  ),
  _Rule(
    'text.telegram_takeover', Severity.high,
    "Telegram akkauntini o'g'irlash usuli",
    "\"Ovoz bering\" yoki \"Premium tekin\" degan havolalar sizdan telefon raqami va Telegram kirish kodini so'raydi. Kodni hech qayerga kiritmang.",
    ["ovoz ber", "golosu", "progolosu", "telegram premium.{0,20}(tekin|bepul|besplat|sovg'a)", "kirish kodi", "kod dlya vxoda"],
  ),
  _Rule(
    'text.isolation', Severity.high,
    "Yaqinlaringizga aytmaslikni so'rash",
    "Firibgar sizni yakkalashga urinadi: \"bankka ham, oilangizga ham aytmang\". Haqiqiy xodim bunday talab qilmaydi.",
    ["(bank|oila|yaqin|ota-ona|politsiya|militsiya)\\w*.{0,25}(aytmang|bildirmang|xabar bermang)", "nikomu ne (govorite|rasskazyvayte)"],
  ),
  _Rule(
    'text.urgency', Severity.medium,
    "Shoshiltirish",
    "\"Zudlik bilan\", \"24 soat ichida\" kabi bosim o'ylab ko'rishga vaqt qoldirmaslik uchun ishlatiladi. To'xtang va mustaqil tekshiring.",
    ["zudlik bilan", "darhol", "hoziroq", "24 soat ichida", "srochno", "nemedlenno", "v techenie 24"],
  ),
  _Rule(
    'text.move_messenger', Severity.medium,
    "Suhbatni messenjerga ko'chirish",
    "Bozor va e'lon saytlaridagi firibgar suhbatni Telegram yoki WhatsApp'ga ko'chiradi — u yerda sayt himoyasi ishlamaydi.",
    ["telegram(ga|da)\\s+(yozing|o'ting|bog'lan)", "whatsapp(ga|da)\\s+(yozing|o'ting|bog'lan)", "pishite v (telegram|whatsapp)", "perey?dem v (telegram|whatsapp)"],
  ),
];

/// Haqiqiy bank SMS'larida uchraydigan "kodni hech kimga aytmang" ogohlantirishi.
final RegExp _benignOtpWarning = RegExp(
  "(hech kimga|xodimlarga ham|nikomu|nikomu ne)\\s*(\\w+\\s+)?(aytmang|bermang|ma'lum qilmang|ne soobshch|ne govori)",
);

TextReport analyzeText(String text, RostorDb db) {
  final norm = normalizeText(text);
  final findings = <Finding>[];
  final benignOtp = _benignOtpWarning.hasMatch(norm);

  for (final r in _rules) {
    String? hit;
    for (final p in r.patterns) {
      final m = RegExp(p).firstMatch(norm);
      if (m != null) {
        hit = m.group(0);
        break;
      }
    }
    if (hit == null) continue;
    if (r.code == 'text.otp_request' && benignOtp) continue;
    findings.add(Finding(code: r.code, severity: r.severity, title: r.title, explain: r.explain, evidence: '"$hit"'));
  }

  if (benignOtp && findings.every((f) => f.severity < Severity.high)) {
    findings.add(const Finding(
      code: 'text.benign_otp',
      severity: Severity.info,
      title: "Oddiy tasdiqlash SMS'iga o'xshaydi",
      explain: "Matnda \"kodni hech kimga aytmang\" ogohlantirishi bor — bu odatda haqiqiy bank SMS'i. Shu kodni so'rab qo'ng'iroq qilishsa yoki yozishsa, bermang.",
    ));
  }

  findings.addAll(_phoneFindings(text, norm, db, findings));

  // Kombinatsiya: ikki va undan ortiq yuqori darajali belgi birga kelsa, bu tayyor ssenariy.
  final highCount = findings.where((f) => f.severity == Severity.high).length;
  if (highCount >= 2 && !findings.any((f) => f.severity == Severity.critical)) {
    findings.add(const Finding(
      code: 'text.combo',
      severity: Severity.critical,
      title: "Bir nechta firibgarlik belgisi birga",
      explain: "Xabarda bir vaqtning o'zida bir nechta tipik firibgarlik usuli bor. Javob bermang, havolani ochmang, pul o'tkazmang.",
    ));
  }

  final links = [for (final u in extractUrls(text)) analyzeUrl(u, db)];

  if (findings.isEmpty && links.every((l) => l.severity < Severity.medium)) {
    findings.add(const Finding(
      code: 'text.no_signal',
      severity: Severity.info,
      title: "Ma'lum firibgarlik naqshi topilmadi",
      explain: "Bu kafolat emas. Sizdan SMS kod, karta muddati, CVV yoki oldindan to'lov so'ralsa, bu firibgarlik.",
    ));
  }
  return TextReport(text, sortFindings(findings), links);
}

/// "Qo'ng'iroq qiling", "bog'laning", "pozvonite" — matn raqamga qo'ng'iroq qilishga undaydi.
final RegExp _callToAction = RegExp(
  "qo'ng'iroq|telefon qil|bog'lan|murojaat|raqamga|zvoni|pozvoni|svya[zj]|nabe?rite|po nomeru|po telefonu",
);

/// Matn tashkilot xodimi yoki xizmati nomidan yozilgan ("uzum" — meva ham, "soliq" — oddiy so'z ham).
final RegExp _serviceContext = RegExp(
  "bank|karta|hisob|xizmat|operator|mijoz|xavfsizlik|qo'llab|abonent|ilova|sluzhb|kart|schet|bezopasnost|podderzhk|klient|abonent",
);

/// F2: xabardagi telefon raqamlari. Firibgar SMS'da bank nomi va "shu raqamga qo'ng'iroq qiling"
/// bo'ladi, lekin raqam bankning rasmiy raqami emas.
List<Finding> _phoneFindings(String text, String norm, RostorDb db, List<Finding> prior) {
  final phones = extractPhones(text);
  if (phones.isEmpty) return const [];
  final out = <Finding>[];
  final claimed = <Organization>[
    for (final o in db.organizations)
      if (o.phones.isNotEmpty &&
          {...o.brandKeywords, normalizeText(o.name)}
              .where((w) => w.length >= 3)
              .any((w) => RegExp('(^|[^a-z0-9])${RegExp.escape(w)}(\$|[^a-z0-9])').hasMatch(norm)))
        o,
  ];
  final cta = _callToAction.hasMatch(norm) &&
      (_serviceContext.hasMatch(norm) || prior.any((f) => f.severity >= Severity.medium));
  for (final n in phones) {
    final shown = displayPhone(n);
    if (db.maliciousPhones.contains(n)) {
      out.add(Finding(
        code: 'text.phone_malicious',
        severity: Severity.critical,
        title: 'Firibgar raqam',
        explain: "Xabardagi $shown raqami ROSTOR-2 bazasida firibgarlik raqami sifatida qayd etilgan. Qo'ng'iroq qilmang va javob bermang.",
        evidence: shown,
      ));
      continue;
    }
    final owners = db.orgsByPhone(n);
    final mismatched = [for (final o in claimed) if (!owners.contains(o)) o];
    if (cta && mismatched.isNotEmpty) {
      final o = mismatched.first;
      out.add(Finding(
        code: 'text.phone_not_official',
        severity: Severity.high,
        title: "${o.name} nomidan rasmiy bo'lmagan raqam",
        explain: "Xabarda ${o.name} nomi bor va $shown raqamiga qo'ng'iroq qilish so'ralgan, lekin bu raqam ${o.name}ning rasmiy "
            "raqamlari ro'yxatida yo'q. Rasmiy raqamlar: ${o.phones.join(', ')}. Faqat shu raqamlarga o'zingiz qo'ng'iroq qiling.",
        evidence: shown,
      ));
    } else if (owners.isNotEmpty) {
      out.add(Finding(
        code: 'text.phone_official',
        severity: Severity.info,
        title: "${owners.map((o) => o.name).join(', ')} rasmiy raqami",
        explain: "$shown — ${owners.map((o) => o.name).join(', ')}ning rasmiy saytida ko'rsatilgan raqam. "
            "Shunda ham telefonda SMS kod, karta muddati yoki CVV ni aytmang.",
        evidence: shown,
      ));
    }
  }
  return out;
}
