import 'dart:convert';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';

import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:meta/meta.dart';

export 'package:baraka_daftari/core/domain/enums.dart'
    show AgreementSource, AgreementStatus, AgreementType;

/// Kelishuvning 9 asosiy savoli (SPEC 2F.2), tartib bilan.
enum AgreementQuestion {
  parties,
  contributions,
  duties,
  profitRule,
  lossRule,
  custody,
  exitClause,
  arbiter,
  term;

  /// 1–9.
  int get number => index + 1;
}

/// Savol holati: javob berilgan yoki «tegishli emas» (izoh bilan).
enum QuestionState { empty, answered, notApplicable }

/// Hissa turi (2-savol).
enum ContributionKind { money, goods, labor, network }

@immutable
final class AgreementParty {
  const AgreementParty({
    required this.id,
    required this.name,
    this.role = '',
    this.relation = '',
    this.isMe = false,
  });

  factory AgreementParty.fromJson(Map<String, dynamic> j) => AgreementParty(
    id: j['id'] as String,
    name: j['name'] as String,
    role: j['role'] as String? ?? '',
    relation: j['relation'] as String? ?? '',
    isMe: j['isMe'] as bool? ?? false,
  );

  final String id;
  final String name;
  final String role;
  final String relation;

  /// Ilova egasining oilasi.
  final bool isMe;

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'role': role,
    'relation': relation,
    'isMe': isMe,
  };
}

@immutable
final class AgreementContribution {
  const AgreementContribution({
    required this.partyId,
    required this.kind,
    this.amount,
    this.description = '',
  });

  factory AgreementContribution.fromJson(Map<String, dynamic> j) =>
      AgreementContribution(
        partyId: j['partyId'] as String,
        kind: ContributionKind.values.byName(j['kind'] as String),
        amount: _moneyFrom(j['amount']),
        description: j['description'] as String? ?? '',
      );

  final String partyId;
  final ContributionKind kind;
  final Money? amount;
  final String description;

  Map<String, dynamic> toJson() => {
    'partyId': partyId,
    'kind': kind.name,
    'amount': _moneyJson(amount),
    'description': description,
  };
}

/// Vazifa (3-savol): **yagona mas'ul** va «bajarilmasa» bandi.
@immutable
final class AgreementDuty {
  const AgreementDuty({
    required this.id,
    required this.title,
    this.ownerPartyId,
    this.breachClause = '',
  });

  factory AgreementDuty.fromJson(Map<String, dynamic> j) => AgreementDuty(
    id: j['id'] as String,
    title: j['title'] as String,
    ownerPartyId: j['ownerPartyId'] as String?,
    breachClause: j['breachClause'] as String? ?? '',
  );

  final String id;
  final String title;

  /// `null` — egasiz («hamma») — qabul qilinmaydi.
  final String? ownerPartyId;
  final String breachClause;

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'ownerPartyId': ownerPartyId,
    'breachClause': breachClause,
  };
}

/// Foyda qoidasi (4-savol): faqat bp. [fixedAmount] — so'mda qat'iy summa
/// kiritishga urinish (sheriklikda taqiqlangan, validatsiya ushlaydi).
@immutable
final class ProfitRule {
  const ProfitRule({this.shares = const {}, this.fixedAmount, this.text = ''});

  factory ProfitRule.fromJson(Map<String, dynamic> j) => ProfitRule(
    shares: {
      for (final e in (j['shares'] as Map? ?? const {}).entries)
        e.key as String: e.value as int,
    },
    fixedAmount: _moneyFrom(j['fixedAmount']),
    text: j['text'] as String? ?? '',
  );

  /// Tomon ID → ulush (bp).
  final Map<String, int> shares;
  final Money? fixedAmount;
  final String text;

  Map<String, dynamic> toJson() => {
    'shares': shares,
    'fixedAmount': _moneyJson(fixedAmount),
    'text': text,
  };
}

/// 6-savol: pul qayerda, hisobni kim yuritadi, qachon ko'riladi.
@immutable
final class CustodyRule {
  const CustodyRule({
    this.where = '',
    this.keeperPartyId,
    this.keeperDeviceId,
    this.reviewEveryDays = 30,
  });

  factory CustodyRule.fromJson(Map<String, dynamic> j) => CustodyRule(
    where: j['where'] as String? ?? '',
    keeperPartyId: j['keeperPartyId'] as String?,
    keeperDeviceId: j['keeperDeviceId'] as String?,
    reviewEveryDays: j['reviewEveryDays'] as int? ?? 30,
  );

  final String where;
  final String? keeperPartyId;

  /// Jurnalga yozadigan yagona qurilma (SPEC 2F.6).
  final String? keeperDeviceId;

  /// Ko'rik davriyligi (kun); standart — oyiga 1 marta.
  final int reviewEveryDays;

  Map<String, dynamic> toJson() => {
    'where': where,
    'keeperPartyId': keeperPartyId,
    'keeperDeviceId': keeperDeviceId,
    'reviewEveryDays': reviewEveryDays,
  };
}

/// 7-savol: qanday ajralib chiqiladi.
@immutable
final class ExitClause {
  const ExitClause({
    this.noticeDays,
    this.valuation = '',
    this.payout = '',
    this.assets = '',
  });

  factory ExitClause.fromJson(Map<String, dynamic> j) => ExitClause(
    noticeDays: j['noticeDays'] as int?,
    valuation: j['valuation'] as String? ?? '',
    payout: j['payout'] as String? ?? '',
    assets: j['assets'] as String? ?? '',
  );

  final int? noticeDays;
  final String valuation;
  final String payout;
  final String assets;

  Map<String, dynamic> toJson() => {
    'noticeDays': noticeDays,
    'valuation': valuation,
    'payout': payout,
    'assets': assets,
  };
}

/// 8-savol: hakam.
@immutable
final class ArbiterInfo {
  const ArbiterInfo({required this.name, this.role = ''});

  factory ArbiterInfo.fromJson(Map<String, dynamic> j) =>
      ArbiterInfo(name: j['name'] as String, role: j['role'] as String? ?? '');

  final String name;
  final String role;

  Map<String, dynamic> toJson() => {'name': name, 'role': role};
}

/// 9-savol: muddat va yangilash sanasi.
@immutable
final class TermRule {
  const TermRule({this.termMonths, this.reviewDate});

  factory TermRule.fromJson(Map<String, dynamic> j) => TermRule(
    termMonths: j['termMonths'] as int?,
    reviewDate: j['reviewDate'] == null
        ? null
        : LocalDate.parse(j['reviewDate'] as String),
  );

  final int? termMonths;
  final LocalDate? reviewDate;

  Map<String, dynamic> toJson() => {
    'termMonths': termMonths,
    'reviewDate': reviewDate?.toString(),
  };
}

/// Bitta savolning holati va (tegishli emas bo'lsa) izohi.
@immutable
final class QuestionStatus {
  const QuestionStatus(this.state, [this.reason = '']);

  static const empty = QuestionStatus(QuestionState.empty);
  static const answered = QuestionStatus(QuestionState.answered);

  final QuestionState state;
  final String reason;

  Map<String, dynamic> toJson() => {'state': state.name, 'reason': reason};
}

/// 9 savolning javoblari (bitta versiyaning surati, JSON'da saqlanadi).
@immutable
final class AgreementAnswers {
  const AgreementAnswers({
    this.status = const {},
    this.parties = const [],
    this.contributions = const [],
    this.duties = const [],
    this.profit = const ProfitRule(),
    this.lossText = '',
    this.lossAuto,
    this.custody = const CustodyRule(),
    this.exit = const ExitClause(),
    this.arbiter,
    this.term = const TermRule(),
    this.witnesses = const [],
  });

  factory AgreementAnswers.fromJson(Map<String, dynamic> j) {
    List<T> list<T>(String k, T Function(Map<String, dynamic>) f) => [
      for (final x in (j[k] as List? ?? const [])) f(x as Map<String, dynamic>),
    ];
    return AgreementAnswers(
      status: {
        for (final e in (j['status'] as Map? ?? const {}).entries)
          AgreementQuestion.values.byName(e.key as String): QuestionStatus(
            QuestionState.values.byName((e.value as Map)['state'] as String),
            (e.value as Map)['reason'] as String? ?? '',
          ),
      },
      parties: list('parties', AgreementParty.fromJson),
      contributions: list('contributions', AgreementContribution.fromJson),
      duties: list('duties', AgreementDuty.fromJson),
      profit: ProfitRule.fromJson(
        j['profit'] as Map<String, dynamic>? ?? const {},
      ),
      lossText: j['lossText'] as String? ?? '',
      lossAuto: j['lossAuto'] as String?,
      custody: CustodyRule.fromJson(
        j['custody'] as Map<String, dynamic>? ?? const {},
      ),
      exit: ExitClause.fromJson(j['exit'] as Map<String, dynamic>? ?? const {}),
      arbiter: j['arbiter'] == null
          ? null
          : ArbiterInfo.fromJson(j['arbiter'] as Map<String, dynamic>),
      term: TermRule.fromJson(j['term'] as Map<String, dynamic>? ?? const {}),
      witnesses: [for (final w in (j['witnesses'] as List? ?? const [])) '$w'],
    );
  }

  factory AgreementAnswers.decode(String json) =>
      AgreementAnswers.fromJson(jsonDecode(json) as Map<String, dynamic>);

  /// Foydalanuvchi belgilagan holatlar (javob mazmunidan tashqari).
  final Map<AgreementQuestion, QuestionStatus> status;
  final List<AgreementParty> parties;
  final List<AgreementContribution> contributions;
  final List<AgreementDuty> duties;
  final ProfitRule profit;
  final String lossText;

  /// Avtomatik zarar qoidasi (`mudaraba`, `musharaka`, `loan`) — matni ARB
  /// orqali; `null` — foydalanuvchi o'zi yozgan ([lossText]).
  final String? lossAuto;
  final CustodyRule custody;
  final ExitClause exit;
  final ArbiterInfo? arbiter;
  final TermRule term;

  /// Guvohlar (imzolovchilar ro'yxatiga qo'shiladi).
  final List<String> witnesses;

  QuestionStatus statusOf(AgreementQuestion q) =>
      status[q] ?? QuestionStatus.empty;

  AgreementAnswers copyWith({
    Map<AgreementQuestion, QuestionStatus>? status,
    List<AgreementParty>? parties,
    List<AgreementContribution>? contributions,
    List<AgreementDuty>? duties,
    ProfitRule? profit,
    String? lossText,
    String? lossAuto,
    CustodyRule? custody,
    ExitClause? exit,
    ArbiterInfo? arbiter,
    bool clearArbiter = false,
    TermRule? term,
    List<String>? witnesses,
  }) => AgreementAnswers(
    status: status ?? this.status,
    parties: parties ?? this.parties,
    contributions: contributions ?? this.contributions,
    duties: duties ?? this.duties,
    profit: profit ?? this.profit,
    lossText: lossText ?? this.lossText,
    lossAuto: lossAuto ?? this.lossAuto,
    custody: custody ?? this.custody,
    exit: exit ?? this.exit,
    arbiter: clearArbiter ? null : (arbiter ?? this.arbiter),
    term: term ?? this.term,
    witnesses: witnesses ?? this.witnesses,
  );

  /// [q] savolni belgilash (javob berildi / tegishli emas + izoh).
  AgreementAnswers mark(AgreementQuestion q, QuestionStatus s) =>
      copyWith(status: {...status, q: s});

  Map<String, dynamic> toJson() => {
    'status': {for (final e in status.entries) e.key.name: e.value.toJson()},
    'parties': [for (final p in parties) p.toJson()],
    'contributions': [for (final c in contributions) c.toJson()],
    'duties': [for (final d in duties) d.toJson()],
    'profit': profit.toJson(),
    'lossText': lossText,
    'lossAuto': ?lossAuto,
    'custody': custody.toJson(),
    'exit': exit.toJson(),
    'arbiter': arbiter?.toJson(),
    'term': term.toJson(),
    'witnesses': witnesses,
  };

  String encode() => jsonEncode(toJson());

  AgreementParty? party(String id) =>
      parties.where((p) => p.id == id).firstOrNull;
}

Money? _moneyFrom(Object? j) {
  if (j == null) return null;
  final m = j as Map;
  return Money(
    int.parse(m['minor'] as String),
    CurrencyCode.values.byName((m['currency'] as String).toLowerCase()),
  );
}

Map<String, String>? _moneyJson(Money? m) => m == null
    ? null
    : {'minor': '${m.minorUnits}', 'currency': m.currency.name.toUpperCase()};

/// Kelishuv (`Agreement`, SPEC 2F.1).
@immutable
final class Agreement implements Synced {
  const Agreement({
    required this.meta,
    required this.type,
    required this.title,
    required this.effectiveFrom,
    this.status = AgreementStatus.draft,
    this.currentVersion = 1,
    this.source,
    this.sourceId,
    this.oral = false,
    this.reviewDate,
    this.legacy = false,
  });

  @override
  final SyncMeta meta;
  final AgreementType type;
  final String title;
  final AgreementStatus status;

  /// Kuchga kirgan sana (og'zaki kelishuvda — o'tmishda).
  final LocalDate effectiveFrom;
  final int currentVersion;
  final AgreementSource? source;
  final String? sourceId;

  /// Og'zaki kelishuvdan yozib olingan (SPEC 2F.9).
  final bool oral;

  /// Keyingi yillik yangilash sanasi (9-savoldan).
  final LocalDate? reviewDate;

  /// 9A dan oldin imzolangan (tilxat / shartnoma) — ko'chirilgan; 9 savol
  /// to'liq bo'lmasligi mumkin, imzolar o'z kuchida.
  final bool legacy;

  Agreement copyWith({
    SyncMeta? meta,
    AgreementStatus? status,
    int? currentVersion,
    String? title,
    LocalDate? reviewDate,
  }) => Agreement(
    meta: meta ?? this.meta,
    type: type,
    title: title ?? this.title,
    effectiveFrom: effectiveFrom,
    status: status ?? this.status,
    currentVersion: currentVersion ?? this.currentVersion,
    source: source,
    sourceId: sourceId,
    oral: oral,
    reviewDate: reviewDate ?? this.reviewDate,
    legacy: legacy,
  );
}

/// Kelishuv versiyasi — har o'zgarish yangi versiya; imzolangani o'zgarmaydi.
/// Imzolar `loan_signers` da (`document_id` = versiya ID si).
@immutable
final class AgreementVersion implements Synced {
  const AgreementVersion({
    required this.meta,
    required this.agreementId,
    required this.version,
    required this.answers,
    this.note,
  });

  @override
  final SyncMeta meta;
  final String agreementId;
  final int version;
  final AgreementAnswers answers;

  /// Masalan, «o'zgarishsiz tasdiqlandi».
  final String? note;

  AgreementVersion copyWith({
    SyncMeta? meta,
    AgreementAnswers? answers,
    String? note,
  }) => AgreementVersion(
    meta: meta ?? this.meta,
    agreementId: agreementId,
    version: version,
    answers: answers ?? this.answers,
    note: note ?? this.note,
  );
}

abstract interface class AgreementRepository
    implements SyncedRepository<Agreement> {
  /// Mavjud modul yozuviga bog'langan faol kelishuv.
  Future<Agreement?> bySource(AgreementSource source, String sourceId);
}

abstract interface class AgreementVersionRepository
    implements SyncedRepository<AgreementVersion> {
  /// Versiyalar, eskisi birinchi.
  Future<List<AgreementVersion>> forAgreement(String agreementId);
}
