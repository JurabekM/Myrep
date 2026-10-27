import 'dart:convert';

import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:crypto/crypto.dart';
import 'package:meta/meta.dart';

/// Jurnal yozuvi turi (SPEC 2F.6). Kanonik shaklda SCREAMING_SNAKE_CASE.
enum JournalKind {
  /// Tomonning hissasi (kapital, qarz berilishi).
  contribution,

  /// Taqsimlangan foyda ulushi.
  profitDistribution,

  /// Taqsimlangan zarar ulushi.
  lossDistribution,

  /// Qarz to'lovi (tilxat).
  loanPayment,

  /// Kassa daftari: kirim, xarajat, fors-major.
  ventureIncome,
  ventureExpense,
  forceMajeure,

  /// Kamayib boruvchi musharaka: ulush sotib olish.
  buyout,

  /// Og'zaki kelishuvni yozib olishda «shu kungacha» holat (SPEC 2F.9).
  openingBalance,

  /// Tuzatuvchi yozuv — eski yozuv o'zgarmaydi, o'chirilmaydi.
  correction,

  /// «Vazifamni bajara olmayapman» (SPEC 2F.4). `refId` — vazifa ID si,
  /// `note` — sabab va taklif qilingan yechim (JSON).
  dutyIncident,

  /// Ochiq ko'rik boshlandi (SPEC 2F.5). Yozuv sanasi — kesim sanasi;
  /// `refId` — ko'rik ID si.
  reviewOpened,

  /// Tomonning ko'rikka javobi: `AGREE` yoki `OBJECT` + izoh (JSON).
  reviewAck,

  /// Ko'rik bayonnomasi. `note` — `chainHead` va e'tirozlar (JSON).
  accountReview,

  /// Tomon «katta foyda»dan keyin 4–5-bandni qayta o'qiganini belgiladi
  /// (SPEC 2F.7). `refId` — davr tugashi va foyda (kalit).
  profitSpikeAck,

  /// Nizo ochildi yoki boshqa tomon o'z talabini qo'shdi (SPEC 2F.8).
  /// Birinchi yozuv — nizo ildizi; `refId` — ildiz ID si (talablar uchun).
  disputeOpened,

  /// Hakam qarori (SPEC 2F.8); `refId` — nizo ildizi ID si.
  arbiterDecision;

  String get code =>
      name.replaceAllMapped(RegExp('[A-Z]'), (m) => '_${m[0]}').toUpperCase();

  /// Moliyaviy yozuv. Ko'rik bayonnomasidan keyin o'sha davrga faqat
  /// tuzatuvchi yozuv qo'shiladi (SPEC 2F.5); hodisa va ko'rik yozuvlari
  /// bu qoidaga kirmaydi.
  bool get isFinancial => switch (this) {
    contribution ||
    profitDistribution ||
    lossDistribution ||
    loanPayment ||
    ventureIncome ||
    ventureExpense ||
    forceMajeure ||
    buyout ||
    openingBalance => true,
    _ => false,
  };

  static JournalKind fromCode(String code) =>
      values.firstWhere((k) => k.code == code);
}

/// Genesis `prevHash` — 64 ta `0`.
const String genesisHash =
    '0000000000000000000000000000000000000000000000000000000000000000';

/// Append-only jurnal yozuvi (`JournalEntry`). Har kelishuvning o'z zanjiri:
/// `hash = SHA256(prevHash + "\n" + JCS(canonical))`.
@immutable
final class JournalEntry implements Synced {
  const JournalEntry({
    required this.meta,
    required this.agreementId,
    required this.seq,
    required this.kind,
    required this.date,
    required this.prevHash,
    required this.hash,
    this.partyId,
    this.amount,
    this.note,
    this.refId,
  });

  @override
  final SyncMeta meta;
  final String agreementId;

  /// Zanjirdagi o'rni (1 dan).
  final int seq;
  final JournalKind kind;
  final String? partyId;

  /// Ishorali (tuzatish va zarar manfiy bo'lishi mumkin).
  final Money? amount;
  final LocalDate date;
  final String? note;

  /// Manba yozuvi (qarz to'lovi, kassa yozuvi) ID si.
  final String? refId;
  final String prevHash;
  final String hash;

  /// Kanonik mazmun (xeshlanadi). `null` maydonlar kiritilmaydi; pul —
  /// `{minor: string, currency}`.
  Map<String, Object> get canonical => journalCanonical(
    id: meta.id,
    agreementId: agreementId,
    kind: kind,
    partyId: partyId,
    amount: amount,
    date: date,
    note: note,
    refId: refId,
  );
}

Map<String, Object> journalCanonical({
  required String id,
  required String agreementId,
  required JournalKind kind,
  required LocalDate date,
  String? partyId,
  Money? amount,
  String? note,
  String? refId,
}) => {
  'id': id,
  'agreementId': agreementId,
  'kind': kind.code,
  'partyId': ?partyId,
  if (amount != null)
    'amount': {
      'minor': '${amount.minorUnits}',
      'currency': amount.currency.name.toUpperCase(),
    },
  'date': '$date',
  'note': ?note,
  'ref': ?refId,
};

/// RFC 8785 (JCS): kalitlar UTF-16 kod birliklari bo'yicha tartiblangan, bo'sh
/// joy yo'q, satrlar ECMAScript `JSON.stringify` qoidasida. Sonlar faqat
/// butun (pul va sonlar satr sifatida beriladi).
String jcs(Object? value) {
  final b = StringBuffer();
  void write(Object? v) {
    switch (v) {
      case null:
        b.write('null');
      case bool():
        b.write(v ? 'true' : 'false');
      case int():
        b.write(v);
      case String():
        _writeString(b, v);
      case List<Object?>():
        b.write('[');
        for (var i = 0; i < v.length; i++) {
          if (i > 0) b.write(',');
          write(v[i]);
        }
        b.write(']');
      case Map<Object?, Object?>():
        final keys = [for (final k in v.keys) k! as String]..sort();
        b.write('{');
        for (var i = 0; i < keys.length; i++) {
          if (i > 0) b.write(',');
          _writeString(b, keys[i]);
          b.write(':');
          write(v[keys[i]]);
        }
        b.write('}');
      default:
        throw ArgumentError.value(v, 'value', "JCS: qo'llab-quvvatlanmaydi");
    }
  }

  write(value);
  return b.toString();
}

void _writeString(StringBuffer b, String s) {
  b.write('"');
  for (final unit in s.codeUnits) {
    switch (unit) {
      case 0x22:
        b.write(r'\"');
      case 0x5C:
        b.write(r'\\');
      case 0x08:
        b.write(r'\b');
      case 0x0C:
        b.write(r'\f');
      case 0x0A:
        b.write(r'\n');
      case 0x0D:
        b.write(r'\r');
      case 0x09:
        b.write(r'\t');
      default:
        if (unit < 0x20) {
          b.write('\\u${unit.toRadixString(16).padLeft(4, '0')}');
        } else {
          b.writeCharCode(unit);
        }
    }
  }
  b.write('"');
}

/// `hex(SHA256(prevHash + "\n" + JCS(canonical)))`, kichik harflarda.
String chainHash(String prevHash, Map<String, Object?> canonical) =>
    sha256.convert(utf8.encode('$prevHash\n${jcs(canonical)}')).toString();

/// Zanjirni tekshiradi ([entries] — `seq` tartibida). Natija — birinchi
/// buzilgan yozuvning tartib raqami (1 dan) yoki `null` (butun).
int? verifyChain(List<JournalEntry> entries) {
  var prev = genesisHash;
  for (final (i, e) in entries.indexed) {
    if (e.seq != i + 1 || e.prevHash != prev) return i + 1;
    if (chainHash(prev, e.canonical) != e.hash) return i + 1;
    prev = e.hash;
  }
  return null;
}

/// Yangi yozuv (zanjir holatini repozitoriy qo'shadi).
@immutable
final class JournalDraft {
  const JournalDraft({
    required this.kind,
    required this.date,
    this.partyId,
    this.amount,
    this.note,
    this.refId,
  });

  final JournalKind kind;
  final LocalDate date;
  final String? partyId;
  final Money? amount;
  final String? note;
  final String? refId;
}

/// Faqat qo'shiladigan jurnal (SPEC 2F.6): tahrirlash va o'chirish metodi
/// YO'Q; DB darajasida trigger ham to'sadi.
abstract interface class JournalRepository {
  /// Zanjir oxiriga qo'shadi (`seq`, `prevHash`, `hash` shu yerda,
  /// tranzaksiya ichida).
  Future<JournalEntry> append(String agreementId, JournalDraft draft);

  /// `seq` tartibida.
  Future<List<JournalEntry>> forAgreement(String agreementId);
}
