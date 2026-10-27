import 'dart:convert';

import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/partnerships/domain/partnership_rules.dart';
import 'package:meta/meta.dart';

/// Shablon tekshiruvi (yurist va ulamo, SPEC 2E.2): faqat `approved`
/// shablon ogohlantirishsiz chiqadi.
enum TemplateReviewStatus { pending, approved }

/// Shartnoma shabloni.
@immutable
final class ContractTemplate {
  const ContractTemplate(this.id, this.type, this.reviewStatus);

  final String id;
  final PartnershipType type;
  final TemplateReviewStatus reviewStatus;

  bool get isPending => reviewStatus == TemplateReviewStatus.pending;

  static const mudarabaV1 = ContractTemplate(
    'mudaraba-v1',
    PartnershipType.mudaraba,
    TemplateReviewStatus.pending,
  );
  static const musharakaV1 = ContractTemplate(
    'musharaka-v1',
    PartnershipType.musharaka,
    TemplateReviewStatus.pending,
  );

  static const List<ContractTemplate> all = [mudarabaV1, musharakaV1];

  static ContractTemplate forType(PartnershipType t) =>
      all.firstWhere((x) => x.type == t);

  static ContractTemplate byId(String id) =>
      all.firstWhere((x) => x.id == id, orElse: () => mudarabaV1);
}

/// Shartnoma shartlarining surati (versiya o'zgarmasligi uchun JSON).
@immutable
final class ContractTerms {
  const ContractTerms({
    required this.title,
    required this.type,
    required this.currency,
    required this.termMonths,
    required this.reportPeriod,
    required this.endTerms,
    required this.disputeTerms,
    required this.partners,
    required this.witnesses,
  });

  factory ContractTerms.fromJson(String json) {
    final m = jsonDecode(json) as Map<String, dynamic>;
    final c = CurrencyCode.values.byName(m['currency'] as String);
    return ContractTerms(
      title: m['title'] as String,
      type: PartnershipType.values.byName(m['type'] as String),
      currency: c,
      termMonths: m['termMonths'] as int,
      reportPeriod: ReportPeriod.values.byName(m['reportPeriod'] as String),
      endTerms: m['endTerms'] as String,
      disputeTerms: m['disputeTerms'] as String,
      partners: [
        for (final p in (m['partners'] as List).cast<Map<String, dynamic>>())
          ContractParty(
            name: p['name'] as String,
            role: PartnerRole.values.byName(p['role'] as String),
            shareBp: p['shareBp'] as int,
            capital: [
              for (final x
                  in (p['capital'] as List).cast<Map<String, dynamic>>())
                CapitalItem(
                  kind: CapitalKind.values.byName(x['kind'] as String),
                  title: x['title'] as String,
                  amount: Money(x['amount'] as int, c),
                ),
            ],
          ),
      ],
      witnesses: (m['witnesses'] as List).cast<String>(),
    );
  }

  final String title;
  final PartnershipType type;
  final CurrencyCode currency;
  final int termMonths;
  final ReportPeriod reportPeriod;
  final String endTerms;
  final String disputeTerms;
  final List<ContractParty> partners;
  final List<String> witnesses;

  String toJson() => jsonEncode({
    'title': title,
    'type': type.name,
    'currency': currency.name,
    'termMonths': termMonths,
    'reportPeriod': reportPeriod.name,
    'endTerms': endTerms,
    'disputeTerms': disputeTerms,
    'partners': [
      for (final p in partners)
        {
          'name': p.name,
          'role': p.role.name,
          'shareBp': p.shareBp,
          'capital': [
            for (final x in p.capital)
              {
                'kind': x.kind.name,
                'title': x.title,
                'amount': x.amount.minorUnits,
              },
          ],
        },
    ],
    'witnesses': witnesses,
  });
}

@immutable
final class ContractParty {
  const ContractParty({
    required this.name,
    required this.role,
    required this.shareBp,
    required this.capital,
  });

  final String name;
  final PartnerRole role;
  final int shareBp;
  final List<CapitalItem> capital;

  Money capitalTotal(CurrencyCode c) =>
      Money.sum(capital.map((x) => x.amount), c);
}
