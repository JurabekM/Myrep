/** Backend kodlari → tarjima kalitlari (typed i18n: faqat literal kalitlar). */

export function kindKey(kind: string) {
  switch (kind) {
    case "LOAN":
      return "agreements.kind.LOAN" as const;
    case "FAMILY":
      return "agreements.kind.FAMILY" as const;
    case "OTHER":
      return "agreements.kind.OTHER" as const;
    default:
      return "agreements.kind.PARTNERSHIP" as const;
  }
}

export function statusKey(status: string) {
  switch (status) {
    case "SIGNED":
      return "agreements.status.SIGNED" as const;
    case "IN_DISPUTE":
      return "agreements.status.IN_DISPUTE" as const;
    case "ENDED":
      return "agreements.status.ENDED" as const;
    default:
      return "agreements.status.DRAFT" as const;
  }
}

export function journalKindKey(kind: string) {
  switch (kind) {
    case "OPENING_BALANCE":
      return "agreements.journalKind.OPENING_BALANCE" as const;
    case "PROFIT_DISTRIBUTION":
      return "agreements.journalKind.PROFIT_DISTRIBUTION" as const;
    case "LOAN_PAYMENT":
      return "agreements.journalKind.LOAN_PAYMENT" as const;
    case "CORRECTION":
      return "agreements.journalKind.CORRECTION" as const;
    case "VENTURE_INCOME":
      return "agreements.journalKind.VENTURE_INCOME" as const;
    case "VENTURE_EXPENSE":
      return "agreements.journalKind.VENTURE_EXPENSE" as const;
    case "FORCE_MAJEURE":
      return "agreements.journalKind.FORCE_MAJEURE" as const;
    case "LOSS_DISTRIBUTION":
      return "agreements.journalKind.LOSS_DISTRIBUTION" as const;
    case "BUYOUT_PAYMENT":
      return "agreements.journalKind.BUYOUT_PAYMENT" as const;
    default:
      return "agreements.journalKind.CONTRIBUTION" as const;
  }
}

export const QUESTION_KEYS = {
  1: { title: "agreements.q1.title", hint: "agreements.q1.hint", advice: "agreements.q1.advice" },
  2: { title: "agreements.q2.title", hint: "agreements.q2.hint", advice: "agreements.q2.advice" },
  3: { title: "agreements.q3.title", hint: "agreements.q3.hint", advice: "agreements.q3.advice" },
  4: { title: "agreements.q4.title", hint: "agreements.q4.hint", advice: "agreements.q4.advice" },
  5: { title: "agreements.q5.title", hint: "agreements.q5.hint", advice: "agreements.q5.advice" },
  6: { title: "agreements.q6.title", hint: "agreements.q6.hint", advice: "agreements.q6.advice" },
  7: { title: "agreements.q7.title", hint: "agreements.q7.hint", advice: "agreements.q7.advice" },
  8: { title: "agreements.q8.title", hint: "agreements.q8.hint", advice: "agreements.q8.advice" },
  9: { title: "agreements.q9.title", hint: "agreements.q9.hint", advice: "agreements.q9.advice" },
} as const;
