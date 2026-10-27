import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement_service.dart';
import 'package:baraka_daftari/features/agreements/domain/completeness.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';

String agQuestion(AppLocalizations l, AgreementQuestion q) => switch (q) {
  AgreementQuestion.parties => l.agQ1,
  AgreementQuestion.contributions => l.agQ2,
  AgreementQuestion.duties => l.agQ3,
  AgreementQuestion.profitRule => l.agQ4,
  AgreementQuestion.lossRule => l.agQ5,
  AgreementQuestion.custody => l.agQ6,
  AgreementQuestion.exitClause => l.agQ7,
  AgreementQuestion.arbiter => l.agQ8,
  AgreementQuestion.term => l.agQ9,
};

String agQuestionHint(AppLocalizations l, AgreementQuestion q) => switch (q) {
  AgreementQuestion.parties => l.agQ1Hint,
  AgreementQuestion.contributions => l.agQ2Hint,
  AgreementQuestion.duties => l.agQ3Hint,
  AgreementQuestion.profitRule => l.agQ4Hint,
  AgreementQuestion.lossRule => l.agQ5Hint,
  AgreementQuestion.custody => l.agQ6Hint,
  AgreementQuestion.exitClause => l.agQ7Hint,
  AgreementQuestion.arbiter => l.agQ8Hint,
  AgreementQuestion.term => l.agQ9Hint,
};

String agType(AppLocalizations l, AgreementType t) => switch (t) {
  AgreementType.partnership => l.agTypePartnership,
  AgreementType.loan => l.agTypeLoan,
  AgreementType.rent => l.agTypeRent,
  AgreementType.service => l.agTypeService,
  AgreementType.family => l.agTypeFamily,
  AgreementType.other => l.agTypeOther,
};

String agStatus(AppLocalizations l, AgreementStatus s) => switch (s) {
  AgreementStatus.draft => l.agStatusDraft,
  AgreementStatus.signed => l.agStatusSigned,
  AgreementStatus.active => l.agStatusActive,
  AgreementStatus.inDispute => l.agStatusDispute,
  AgreementStatus.closed => l.agStatusClosed,
};

String agContributionKind(AppLocalizations l, ContributionKind k) =>
    switch (k) {
      ContributionKind.money => l.agContribMoney,
      ContributionKind.goods => l.agContribGoods,
      ContributionKind.labor => l.agContribLabor,
      ContributionKind.network => l.agContribNetwork,
    };

String agReviewEvery(AppLocalizations l, int days) => switch (days) {
  7 => l.agEveryWeek,
  14 => l.agEvery2Weeks,
  30 => l.agEveryMonth,
  90 => l.agEveryQuarter,
  365 => l.agEveryYear,
  _ => l.agEveryDays(days),
};

String agIssue(AppLocalizations l, String code) => switch (code) {
  AgreementIssue.partiesMin2 => l.agErrPartiesMin2,
  AgreementIssue.contributionMissing => l.agErrContribution,
  AgreementIssue.dutyWithoutOwner => l.agErrDutyOwner,
  AgreementIssue.dutyWithoutBreachClause => l.agErrDutyBreach,
  AgreementIssue.profitSharesNot100 => l.agErrShares,
  AgreementIssue.guaranteedReturnForbidden => l.agErrGuaranteed,
  AgreementIssue.arbiterIsParty => l.agErrArbiterParty,
  AgreementIssue.naReasonRequired => l.agErrNaReason,
  AgreementIssue.reviewTooRare => l.agReviewTooRare,
  _ => l.genericError,
};

/// Avtomatik zarar qoidasi matni.
String agLossAuto(AppLocalizations l, String code) => switch (code) {
  'mudaraba' => l.pnLossRuleMudaraba,
  'musharaka' => l.agLossMusharaka,
  _ => l.agLossLoan,
};

String agJournalKind(AppLocalizations l, JournalKind k) => switch (k) {
  JournalKind.contribution => l.agJContribution,
  JournalKind.profitDistribution => l.agJProfit,
  JournalKind.lossDistribution => l.agJLoss,
  JournalKind.loanPayment => l.agJLoanPayment,
  JournalKind.ventureIncome => l.agJIncome,
  JournalKind.ventureExpense => l.agJExpense,
  JournalKind.forceMajeure => l.agJForceMajeure,
  JournalKind.buyout => l.agJBuyout,
  JournalKind.openingBalance => l.agJOpening,
  JournalKind.correction => l.agJCorrection,
  JournalKind.dutyIncident => l.agJDutyIncident,
  JournalKind.reviewOpened => l.agJReviewOpened,
  JournalKind.reviewAck => l.agJReviewAck,
  JournalKind.accountReview => l.agJAccountReview,
  JournalKind.profitSpikeAck => l.agJProfitSpikeAck,
  JournalKind.disputeOpened => l.agJDisputeOpened,
  JournalKind.arbiterDecision => l.agJArbiterDecision,
};

String agError(AppLocalizations l, String code) => switch (code) {
  AgreementService.errTitleRequired => l.agErrTitle,
  AgreementService.errIncomplete => l.agErrIncomplete,
  AgreementService.errNotEditable => l.agErrSigned,
  AgreementService.errFutureDate => l.agErrFuture,
  AgreementService.errNameRequired => l.receiptErrName,
  AgreementService.errEmptySignature => l.receiptErrSignature,
  AgreementService.errNotSigned => l.agErrNotSigned,
  AgreementService.errAlreadySigned => l.agAlreadySigned,
  AccountabilityErrors.reviewLocked => l.agErrReviewLocked,
  AccountabilityErrors.reviewOpen => l.agErrReviewOpen,
  AccountabilityErrors.noReview => l.agErrNoReview,
  AccountabilityErrors.reviewNotAllAcked => l.agErrReviewIncomplete,
  AccountabilityErrors.reviewAlreadyAcked => l.agErrReviewAcked,
  AccountabilityErrors.objectionRequired => l.agErrObjection,
  AccountabilityErrors.reasonRequired => l.agErrReasonRequired,
  AccountabilityErrors.dutyNotFound => l.agErrDutyNotFound,
  AccountabilityErrors.partyNotFound => l.agErrPartyNotFound,
  AccountabilityErrors.inDispute => l.agErrInDispute,
  AccountabilityErrors.disputeNotFound => l.agErrDisputeNotFound,
  AccountabilityErrors.disputeDecided => l.agErrDisputeDecided,
  AccountabilityErrors.claimRequired => l.agErrClaimRequired,
  AccountabilityErrors.decisionRequired => l.agErrDecisionRequired,
  AccountabilityErrors.spikeAckRequired => l.agErrSpikeAck,
  AccountabilityErrors.alreadyAcked => l.agErrAcked,
  _ => l.genericError,
};
