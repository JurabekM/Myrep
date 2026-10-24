import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/partnerships/domain/contract_template.dart';

/// Tilxat (`LOAN`) tomonlari ID lari.
const String lenderPartyId = 'lender';
const String borrowerPartyId = 'borrower';

/// Yillik yangilash: [from] dan 12 oy (muddat qisqaroq bo'lsa — muddat
/// oxiri).
LocalDate defaultReviewDate(LocalDate from, {int? termMonths}) =>
    from.plusMonths(
      termMonths != null && termMonths > 0 && termMonths < 12 ? termMonths : 12,
    );

/// Tilxat javoblari (SPEC 2F.2, `LOAN`): 1, 2, 9-savollar qarz
/// yozuvidan; 3 — to'lov jadvali, 4–5 — «foiz yo'q» (avtomatik). 6, 7, 8 —
/// foydalanuvchidan ([keep] dan saqlanadi).
AgreementAnswers loanAnswers({
  required String lender,
  required String borrower,
  required bool meIsLender,
  required Money principal,
  required LocalDate start,
  LocalDate? lastDue,
  String? earlyTerms,
  AgreementAnswers? keep,
}) {
  final k = keep ?? const AgreementAnswers();
  return k.copyWith(
    parties: [
      AgreementParty(
        id: lenderPartyId,
        name: lender,
        role: 'lender',
        isMe: meIsLender,
      ),
      AgreementParty(
        id: borrowerPartyId,
        name: borrower,
        role: 'borrower',
        isMe: !meIsLender,
      ),
    ],
    contributions: [
      AgreementContribution(
        partyId: lenderPartyId,
        kind: ContributionKind.money,
        amount: principal,
      ),
      // Qarz oluvchining hissasi — o'z vaqtida qaytarish (3-savol jadvali).
      const AgreementContribution(
        partyId: borrowerPartyId,
        kind: ContributionKind.labor,
        description: 'repayment',
      ),
    ],
    lossAuto: 'loan',
    exit: k.exit.payout.isEmpty && (earlyTerms ?? '').trim().isNotEmpty
        ? ExitClause(
            noticeDays: k.exit.noticeDays,
            valuation: k.exit.valuation,
            payout: earlyTerms!.trim(),
            assets: k.exit.assets,
          )
        : k.exit,
    term: TermRule(
      reviewDate: k.term.reviewDate ?? lastDue ?? defaultReviewDate(start),
    ),
  );
}

/// Sheriklik shartnomasi javoblari (`PARTNERSHIP`): 1, 2, 4, 5, 9-savollar
/// shartnoma shartlaridan ([terms]; tomon ID lari — sheriklar qatori ID lari
/// [partyIds], `terms.partners` tartibida); 7-savolning to'lov qismi —
/// «muddat tugaganda» bandi. 3, 6, 8 va 7-savolning baholash qismi —
/// foydalanuvchidan ([keep]).
AgreementAnswers partnershipAnswers({
  required ContractTerms terms,
  required List<String> partyIds,
  required LocalDate start,
  int? myIndex,
  AgreementAnswers? keep,
}) {
  final k = keep ?? const AgreementAnswers();
  final parties = [
    for (final (i, p) in terms.partners.indexed)
      AgreementParty(
        id: partyIds[i],
        name: p.name,
        role: p.role.name,
        isMe: i == myIndex,
      ),
  ];
  return k.copyWith(
    parties: parties,
    contributions: [
      for (final (i, p) in terms.partners.indexed) ...[
        for (final c in p.capital)
          AgreementContribution(
            partyId: partyIds[i],
            kind: c.kind == CapitalKind.cash
                ? ContributionKind.money
                : ContributionKind.goods,
            amount: c.amount,
            description: c.title,
          ),
        if (p.role != PartnerRole.capitalProvider)
          AgreementContribution(
            partyId: partyIds[i],
            kind: ContributionKind.labor,
            description: 'labor',
          ),
      ],
    ],
    profit: ProfitRule(
      shares: {
        for (final (i, p) in terms.partners.indexed) partyIds[i]: p.shareBp,
      },
    ),
    lossAuto: terms.type.name,
    exit: ExitClause(
      noticeDays: k.exit.noticeDays,
      valuation: k.exit.valuation,
      payout: terms.endTerms,
      assets: k.exit.assets,
    ),
    term: TermRule(
      termMonths: terms.termMonths,
      reviewDate:
          k.term.reviewDate ??
          defaultReviewDate(start, termMonths: terms.termMonths),
    ),
    witnesses: terms.witnesses,
  );
}
