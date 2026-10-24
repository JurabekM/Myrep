// Umumiy oltin test vektorlari (`spec/test-vectors/`, DESKTOP_PROMPT.md 5):
// mobil (Dart) va desktop (Rust) bir xil kirishga bitma-bit bir xil natija
// beradi. Har bir fayl — bitta suite; noma'lum suite yoki keraksiz kalit
// bo'lsa runner yiqiladi. 6-qonun suite'lari o'z vazifasigacha «kutilmoqda».
import 'dart:convert';
import 'dart:io';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/fx_rate.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/money/money_format.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/completeness.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:baraka_daftari/features/audit/domain/month_ledger.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:baraka_daftari/features/debts/domain/recovery_service.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/partnerships/domain/distribution.dart';
import 'package:baraka_daftari/features/partnerships/domain/offer_check.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:baraka_daftari/features/partnerships/domain/profit_spike.dart';
import 'package:baraka_daftari/features/partnerships/domain/scam_math.dart';
import 'package:baraka_daftari/features/prices/domain/price_math.dart';
import 'package:baraka_daftari/features/vault/domain/lump_sum.dart';
import 'package:baraka_daftari/features/vault/domain/reserve.dart';
import 'package:flutter_test/flutter_test.dart';

typedef Json = Map<String, dynamic>;

/// Hali implementatsiya qilinmagan suite'lar — qaysi vazifada yoziladi.
/// Hozircha bo'sh: barcha suite'larda runner bor.
const pending = <String, String>{};

CurrencyCode currency(Object? code) =>
    CurrencyCode.values.byName((code! as String).toLowerCase());

Money money(Object? minor, Object? code) =>
    Money(int.parse(minor! as String), currency(code));

List<String> minors(Iterable<Money> list) => [
  for (final m in list) '${m.minorUnits}',
];

/// Domen xato kodlari → umumiy (platformadan mustaqil) kodlar.
String? sharedCode(Object e) => switch (e) {
  DomainRuleException(code: PartnershipRules.errNotPartnership) =>
    'GUARANTEED_RETURN_FORBIDDEN',
  DomainRuleException(code: RecoveryService.errSavingsRequired) =>
    'SAVINGS_BELOW_MINIMUM',
  DomainRuleException(code: RecoveryService.errSplitInvalid) =>
    'SPLIT_NOT_100_PERCENT',
  CurrencyMismatchException() => 'CURRENCY_MISMATCH',
  _ => null,
};

/// [run] natijasi yoki xato kodi (`{'error': CODE}`).
Json guarded(Json Function() run) {
  try {
    return run();
  } on Object catch (e) {
    final code = sharedCode(e);
    if (code == null) rethrow;
    return {'error': code};
  }
}

PartnerRole role(String r) => switch (r) {
  'CAPITAL_PROVIDER' => PartnerRole.capitalProvider,
  'WORKER' => PartnerRole.worker,
  'BOTH' => PartnerRole.both,
  _ => throw ArgumentError(r),
};

/// Vektordagi yozuvlardan zanjir (xeshlar qayta hisoblanadi).
List<JournalEntry> chainOf(List<Json> raw) {
  var prev = genesisHash;
  final out = <JournalEntry>[];
  for (final (i, e) in raw.indexed) {
    final amount = e['amount'] as Json?;
    final draft = JournalEntry(
      meta: SyncMeta(
        id: e['id'] as String,
        householdId: 'h',
        createdAt: DateTime.utc(2026),
        updatedAt: DateTime.utc(2026),
      ),
      agreementId: e['agreementId'] as String,
      seq: i + 1,
      kind: JournalKind.fromCode(e['kind'] as String),
      partyId: e['partyId'] as String?,
      amount: amount == null
          ? null
          : money(amount['minor'], amount['currency']),
      date: LocalDate.parse(e['date'] as String),
      note: e['note'] as String?,
      prevHash: prev,
      hash: '',
    );
    prev = chainHash(prev, draft.canonical);
    out.add(
      JournalEntry(
        meta: draft.meta,
        agreementId: draft.agreementId,
        seq: draft.seq,
        kind: draft.kind,
        partyId: draft.partyId,
        amount: draft.amount,
        date: draft.date,
        note: draft.note,
        prevHash: draft.prevHash,
        hash: prev,
      ),
    );
  }
  return out;
}

Json? journalBase;

final Map<String, Json Function(Json input)> runners = {
  'allocate': (i) => {
    'parts': minors(
      allocate(money(i['total'], i['currency']), [
        for (final r in i['ratios'] as List) r as int,
      ]),
    ),
  },
  'percent_of': (i) => {
    'result': percentOf(
      money(i['amount'], i['currency']),
      i['bp'] as int,
    ).minorUnits.toString(),
  },
  'amortization': (i) {
    final c = currency(i['currency']);
    final principal = money(i['principal'], c.name);
    final rate = i['annualBp'] as int;
    final rows = buildSchedule(
      type: DebtScheduleType.annuity,
      principal: principal,
      start: LocalDate(2026, 10, 1),
      termMonths: i['termMonths'] as int,
      annualRateBp: rate,
    );
    final plan = planPayoff(
      [
        PayoffDebt(
          id: 'v',
          rows: rows,
          terms: PayoffTerms.annuity(
            annualRateBp: rate,
            annuityPayment: rows.first.amount,
          ),
        ),
      ],
      monthlyExtra: money(i['extraPerMonth'], c.name),
    ).debts.single;
    final s = plan.accelerated;
    var balance = principal;
    return {
      'payment': '${rows.first.amount.minorUnits}',
      'months': s.months,
      'totalInterest': '${s.totalInterest.minorUnits}',
      'schedule': [
        for (final (k, step) in s.steps.indexed)
          () {
            final p = step.regular - step.interest;
            balance = balance - p - step.extra;
            return {
              'month': k + 1,
              'interest': '${step.interest.minorUnits}',
              'principal': '${p.minorUnits}',
              'extra': '${step.extra.minorUnits}',
              'balance': '${balance.minorUnits}',
            };
          }(),
      ],
    };
  },
  'profit_distribution': (i) => guarded(() {
    final c = currency(i['currency']);
    final type = PartnershipType.values.byName(
      (i['type'] as String).toLowerCase(),
    );
    final parties = (i['parties'] as List).cast<Json>();
    PartnershipRules.validate(type, [
      for (final (k, p) in parties.indexed)
        PartnerDraft(
          name: 'P${k + 1}',
          role: role(p['role'] as String),
          profit: p['fixedReturn'] != null
              ? ProfitShareInput.fixed(money(p['fixedReturn'], c.name))
              : ProfitShareInput.percent(p['shareBp'] as int),
          capital: [
            if (money(p['capital'], c.name).isPositive)
              CapitalItem(
                kind: CapitalKind.cash,
                title: 'kapital',
                amount: money(p['capital'], c.name),
              ),
          ],
        ),
    ], c);
    final r = distribute(
      type: type,
      parties: [
        for (final p in parties)
          DistributionParty(
            role: role(p['role'] as String),
            shareBp: p['shareBp'] as int,
            capital: money(p['capital'], c.name),
          ),
      ],
      net: money(i['net'], c.name),
    );
    return {'shares': minors(r.shares)};
  }),
  'emergency_target': (i) {
    final t = emergencyTarget(
      monthTotals: [
        for (final m in i['months'] as List) money(m, i['currency']),
      ],
      months: i['n'] as int,
    );
    return {'target': t == null ? null : '${t.minorUnits}'};
  },
  'personal_inflation': (i) {
    final items = [
      for (final it in (i['items'] as List).cast<Json>())
        WeightedChange(
          from: money(it['from'], i['currency']),
          to: money(it['to'], i['currency']),
          weight: it['weightBp'] as int,
        ),
    ];
    return {
      'items': [for (final it in items) changeBasisPoints(it.from, it.to)],
      'index': weightedInflationBp(items),
    };
  },
  'unexplained_gap': (i) {
    Money m(String k) => money(i[k], i['currency']);
    return {
      'gap': unexplainedGap(
        income: m('income'),
        obligations: m('obligations'),
        expenses: m('expenses'),
        savings: m('savings'),
      ).minorUnits.toString(),
    };
  },
  'readiness_gate': (i) {
    final reasons = gateLockReasons(
      reserveFull:
          (i['reserveMonthsTenths'] as int) >= ReserveStatus.fullMonths * 10,
      debtReady:
          !(i['hasInterestDebt'] as bool) || (i['hasRecoveryPlan'] as bool),
    );
    return {
      'state': reasons.isEmpty ? 'OPEN' : 'LOCKED',
      'reasons': [
        for (final r in reasons)
          switch (r) {
            GateLockReason.reserveBelowTarget => 'RESERVE_BELOW_TARGET',
            GateLockReason.interestDebtWithoutPlan =>
              'INTEREST_DEBT_WITHOUT_PLAN',
          },
      ],
    };
  },
  'debt_recovery_split': (i) => guarded(() {
    final s = [for (final x in i['split'] as List) x as int];
    final split = RecoverySplit(needsBp: s[0], debtBp: s[1], savingsBp: s[2]);
    RecoveryService.validate(split);
    return {
      'parts': minors(allocate(money(i['income'], i['currency']), s)),
    };
  }),
  'fx_convert': (i) => guarded(() {
    final rate = FxRate(
      from: currency(i['rateFrom'] ?? i['from']),
      to: currency(i['to']),
      numerator: i['rateNum'] as int,
      denominator: i['rateDen'] as int,
      date: DateTime.utc(2026, 10, 2),
    );
    return {
      'result': '${convert(money(i['amount'], i['from']), rate).minorUnits}',
    };
  }),
  'journal_chain': (i) {
    if (i['base'] == null) {
      final raw = (i['entries'] as List).cast<Json>();
      journalBase = i;
      final chain = chainOf(raw);
      expect(verifyChain(chain), isNull);
      return {
        'hashes': [for (final e in chain) e.hash],
      };
    }
    // Buzish: saqlangan xeshlar o'zgarmaydi, mazmun o'zgaradi.
    final chain = chainOf((journalBase!['entries'] as List).cast<Json>());
    final t = i['tamper'] as Json;
    final k = t['index'] as int;
    final e = chain[k];
    chain[k] = JournalEntry(
      meta: e.meta,
      agreementId: e.agreementId,
      seq: e.seq,
      kind: e.kind,
      partyId: e.partyId,
      amount: money(t['amountMinor'], e.amount!.currency.name),
      date: e.date,
      note: e.note,
      prevHash: e.prevHash,
      hash: e.hash,
    );
    return {'firstBroken': verifyChain(chain)};
  },
  'agreement_completeness': (i) {
    final c = checkCompleteness(
      AgreementType.values.byName((i['type'] as String).toLowerCase()),
      AgreementAnswers.fromJson(i['answers'] as Json),
      hasSchedule: i['hasSchedule'] as bool? ?? false,
    );
    return {
      'complete': c.complete,
      'missing': [for (final q in c.missing) q.number],
      'errors': [for (final e in c.errors) e.code],
    };
  },
  'money_format': (i) => {
    'text': MoneyFormatter.format(
      money(i['amount'], i['currency']),
      languageCode: i['locale'] as String,
    ),
  },
  'promised_return': (i) {
    final m = promisedMultiple(
      i['monthlyBp'] as int,
      months: i['months'] as int,
    );
    return {'simpleMultipleBp': m.simpleBp, 'compoundMultipleBp': m.compoundBp};
  },
  'pyramid_levels': (i) {
    final p = pyramidLevels(
      recruitsPerPerson: i['recruitsPerPerson'] as int,
      population: i['population'] as int,
    );
    return {
      'levels': p.levels,
      'participants': p.participants,
      'lastLevel': p.lastLevel,
      'lastLevelShareBp': p.lastLevelShareBp,
      'lastLevelFull': p.lastLevelFull,
    };
  },
  'lump_sum_split': (i) {
    final plan = splitLumpSum(
      money(i['amount'], i['currency']),
      money(i['reserveMissing'], i['currency']),
    );
    return {
      'toReserve': '${plan.toReserve.minorUnits}',
      'toInvest': '${plan.toInvest.minorUnits}',
    };
  },
  'scam_signals': (i) {
    final e = evaluateOffer({
      for (final MapEntry(:key, :value) in (i['answers'] as Json).entries)
        OfferQuestion.values.byName(key): OfferAnswer.values.byName(
          (value as String).toLowerCase(),
        ),
    });
    return {
      'signs': [for (final s in e.signs) s.code],
      'level': e.level.name.toUpperCase(),
      'verdict': e.verdict.name.toUpperCase(),
      'categories': [for (final c in e.categories) c.name.toUpperCase()],
    };
  },
  'profit_spike': (i) => {
    'alert': ProfitSpike.evaluate(
      actual: money(i['actual'], 'uzs'),
      plan: i['plan'] == null ? null : money(i['plan'], 'uzs'),
      last3: i['last3'] == null
          ? null
          : [for (final v in i['last3'] as List) money(v, 'uzs')],
    ),
  },
};

void main() {
  final dir = Directory('spec/test-vectors');
  final files =
      dir
          .listSync()
          .whereType<File>()
          .where((f) => f.path.endsWith('.json'))
          .toList()
        ..sort((a, b) => a.path.compareTo(b.path));

  test("vektorlar papkasi va majburiy suite'lar", () {
    final suites = {
      for (final f in files)
        (jsonDecode(f.readAsStringSync()) as Json)['suite'] as String,
    };
    expect(
      suites,
      containsAll([
        'allocate',
        'percent_of',
        'amortization',
        'profit_distribution',
        'emergency_target',
        'personal_inflation',
        'unexplained_gap',
        'readiness_gate',
        'debt_recovery_split',
        'fx_convert',
        'money_format',
        'journal_chain',
        'profit_spike',
        'agreement_completeness',
        'scam_signals',
        'promised_return',
        'pyramid_levels',
        'lump_sum_split',
      ]),
    );
  });

  for (final f in files) {
    final doc = jsonDecode(f.readAsStringSync()) as Json;
    final suite = doc['suite'] as String;
    final cases = (doc['cases'] as List).cast<Json>();
    group('$suite v${doc['version']}', () {
      final ids = cases.map((c) => c['id']).toList();
      test(
        'id lar takrorlanmaydi',
        () => expect(ids.toSet(), hasLength(ids.length)),
      );
      final run = runners[suite];
      if (run == null) {
        test('runner', () {
          expect(pending, contains(suite), reason: "noma'lum suite: $suite");
        }, skip: pending[suite]);
        return;
      }
      for (final c in cases) {
        test('${c['id']}', () {
          expect(
            run(c['input'] as Json),
            c['expected'],
            reason: c['id'] as String,
          );
        });
      }
    });
  }
}
