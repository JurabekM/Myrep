import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:meta/meta.dart';

/// To'liqlik xatolari va ogohlantirishlari (umumiy kodlar —
/// `spec/test-vectors/agreement_completeness.json`, desktop bilan bir xil).
abstract final class AgreementIssue {
  static const partiesMin2 = 'PARTIES_MIN_2';
  static const contributionMissing = 'CONTRIBUTION_MISSING';
  static const dutyWithoutOwner = 'DUTY_WITHOUT_OWNER';
  static const dutyWithoutBreachClause = 'DUTY_WITHOUT_BREACH_CLAUSE';
  static const profitSharesNot100 = 'PROFIT_SHARES_NOT_100';
  static const guaranteedReturnForbidden = 'GUARANTEED_RETURN_FORBIDDEN';
  static const arbiterIsParty = 'ARBITER_IS_PARTY';
  static const naReasonRequired = 'NA_REASON_REQUIRED';

  /// Ogohlantirish (imzolashni to'xtatmaydi): ko'rik oyiga 1 martadan
  /// siyrak.
  static const reviewTooRare = 'REVIEW_TOO_RARE';
}

@immutable
final class Issue {
  const Issue(this.code, this.question);

  final String code;
  final AgreementQuestion question;
}

/// «N / 9 savolga javob berildi» va xatolar.
@immutable
final class Completeness {
  const Completeness({
    required this.missing,
    required this.errors,
    required this.warnings,
  });

  /// Javobsiz (yoki xatoli) savollar, tartib bilan.
  final List<AgreementQuestion> missing;
  final List<Issue> errors;
  final List<Issue> warnings;

  int get answered => AgreementQuestion.values.length - missing.length;

  /// 9/9 va xatosiz — imzolash ochiladi.
  bool get complete => missing.isEmpty && errors.isEmpty;

  bool isAnswered(AgreementQuestion q) => !missing.contains(q);
}

/// Har bir tur uchun soddalashtirish (strategy, SPEC 2F.2):
/// * `LOAN` — 3-savol = qaytarish jadvali ([hasSchedule]), 4–5 = «foiz
///   yo'q» (avtomatik);
/// * `PARTNERSHIP` — foyda faqat bp, yig'indi 100 %, qat'iy summa taqiq
///   (SPEC 2E.1);
/// * `FAMILY` — hakam ixtiyoriy (izohsiz ham).
Completeness checkCompleteness(
  AgreementType type,
  AgreementAnswers a, {
  bool hasSchedule = false,
}) {
  final missing = <AgreementQuestion>[];
  final errors = <Issue>[];
  final warnings = <Issue>[];
  final partyIds = {for (final p in a.parties) p.id};

  bool optional(AgreementQuestion q) =>
      type == AgreementType.family && q == AgreementQuestion.arbiter;

  bool auto(AgreementQuestion q) =>
      type == AgreementType.loan &&
      (q == AgreementQuestion.profitRule ||
          q == AgreementQuestion.lossRule ||
          (q == AgreementQuestion.duties && hasSchedule));

  /// Mazmun bo'yicha tekshiruv: `null` — bo'sh; aks holda xatolar.
  List<String>? content(AgreementQuestion q) {
    switch (q) {
      case AgreementQuestion.parties:
        if (a.parties.isEmpty) return null;
        return [
          if (a.parties.length < 2 ||
              a.parties.any((p) => p.name.trim().isEmpty))
            AgreementIssue.partiesMin2,
        ];
      case AgreementQuestion.contributions:
        if (a.contributions.isEmpty) return null;
        final givers = {for (final c in a.contributions) c.partyId};
        return [
          if (partyIds.any((id) => !givers.contains(id)))
            AgreementIssue.contributionMissing,
        ];
      case AgreementQuestion.duties:
        if (a.duties.isEmpty) return null;
        return [
          if (a.duties.any(
            (d) => d.ownerPartyId == null || !partyIds.contains(d.ownerPartyId),
          ))
            AgreementIssue.dutyWithoutOwner,
          if (a.duties.any((d) => d.breachClause.trim().isEmpty))
            AgreementIssue.dutyWithoutBreachClause,
        ];
      case AgreementQuestion.profitRule:
        final p = a.profit;
        if (type == AgreementType.partnership) {
          if (p.fixedAmount != null) {
            return [AgreementIssue.guaranteedReturnForbidden];
          }
          if (p.shares.isEmpty) return null;
          final total = p.shares.values.fold(0, (s, v) => s + v);
          return [
            if (total != basisPointsWhole ||
                p.shares.values.any((v) => v < 0) ||
                p.shares.keys.any((id) => !partyIds.contains(id)))
              AgreementIssue.profitSharesNot100,
          ];
        }
        if (p.shares.isEmpty && p.text.trim().isEmpty) return null;
        if (p.shares.isNotEmpty) {
          final total = p.shares.values.fold(0, (s, v) => s + v);
          if (total != basisPointsWhole) {
            return [AgreementIssue.profitSharesNot100];
          }
        }
        return const [];
      case AgreementQuestion.lossRule:
        return a.lossText.trim().isEmpty && a.lossAuto == null
            ? null
            : const [];
      case AgreementQuestion.custody:
        final c = a.custody;
        if (c.where.trim().isEmpty || c.keeperPartyId == null) return null;
        if (!partyIds.contains(c.keeperPartyId)) return null;
        return const [];
      case AgreementQuestion.exitClause:
        final e = a.exit;
        return e.valuation.trim().isEmpty || e.payout.trim().isEmpty
            ? null
            : const [];
      case AgreementQuestion.arbiter:
        final ar = a.arbiter;
        if (ar == null || ar.name.trim().isEmpty) return null;
        final name = ar.name.trim().toLowerCase();
        return [
          if (a.parties.any((p) => p.name.trim().toLowerCase() == name))
            AgreementIssue.arbiterIsParty,
        ];
      case AgreementQuestion.term:
        return a.term.reviewDate == null ? null : const [];
    }
  }

  for (final q in AgreementQuestion.values) {
    if (auto(q)) continue;
    final s = a.statusOf(q);
    if (s.state == QuestionState.notApplicable) {
      // Sheriklikda foyda / zarar qoidasini «tegishli emas» deb bo'lmaydi.
      final forbidden =
          type == AgreementType.partnership &&
          (q == AgreementQuestion.profitRule ||
              q == AgreementQuestion.lossRule);
      if (forbidden) {
        missing.add(q);
      } else if (s.reason.trim().isEmpty && !optional(q)) {
        missing.add(q);
        errors.add(Issue(AgreementIssue.naReasonRequired, q));
      }
      continue;
    }
    final issues = content(q);
    if (issues == null) {
      if (!optional(q)) missing.add(q);
      continue;
    }
    if (issues.isNotEmpty) {
      missing.add(q);
      errors.addAll([for (final code in issues) Issue(code, q)]);
    }
  }
  if (a.custody.reviewEveryDays > 31) {
    warnings.add(
      const Issue(AgreementIssue.reviewTooRare, AgreementQuestion.custody),
    );
  }
  return Completeness(missing: missing, errors: errors, warnings: warnings);
}
