import { z } from "zod";
import type { AgreementAnswersDto } from "../../bindings/bindings";

/**
 * Usta formasining sxemasi (react-hook-form + zod). Bu faqat maydon shakli va oddiy chegaralar:
 * 9 savolning to'liqligi va biznes qoidalari (ulushlar 100 %, hakam tomon emas, ...) Rustda
 * (`domain::agreement::completeness`) tekshiriladi va `completeness` orqali ko'rsatiladi.
 */
export const answersSchema = z.object({
  parties: z.array(
    z.object({
      id: z.string().min(1),
      name: z.string(),
      role: z.string(),
      relation: z.string(),
      isMe: z.boolean(),
    }),
  ),
  contributions: z.array(
    z.object({
      partyId: z.string(),
      kind: z.enum(["money", "goods", "labor", "connections"]),
      amount: z.string(),
      description: z.string(),
    }),
  ),
  duties: z.array(
    z.object({
      id: z.string().min(1),
      title: z.string(),
      ownerPartyId: z.string(),
      breachClause: z.string(),
    }),
  ),
  hasSchedule: z.boolean(),
  profitShares: z.array(
    z.object({ partyId: z.string(), shareBp: z.number().int().min(0).max(10000) }),
  ),
  profitFixedAmount: z.string(),
  profitNotApplicable: z.boolean(),
  profitNaReason: z.string(),
  lossText: z.string(),
  lossNotApplicable: z.boolean(),
  lossNaReason: z.string(),
  custodyLocation: z.string(),
  keeperPartyId: z.string(),
  reviewEveryDays: z.number().int().min(1).max(365),
  exitNoticeDays: z.number().int().min(0).max(3650),
  exitValuation: z.string(),
  exitPayout: z.string(),
  exitAssets: z.string(),
  exitNotApplicable: z.boolean(),
  exitNaReason: z.string(),
  arbiterName: z.string(),
  arbiterRole: z.string(),
  termMonths: z.number().int().min(1).max(600),
  reviewDate: z.string(),
});

export type AnswersForm = z.infer<typeof answersSchema>;

/** Backend DTO → forma qiymatlari («tegishli emas» — bayroq + sabab). */
export function toForm(dto: AgreementAnswersDto): AnswersForm {
  return {
    parties: dto.parties.map((p) => ({
      id: p.id,
      name: p.name,
      role: p.role,
      relation: p.relation,
      isMe: p.isMe,
    })),
    contributions: dto.contributions.map((c) => ({
      partyId: c.partyId,
      kind: isKind(c.kind) ? c.kind : "money",
      amount: c.amount,
      description: c.description,
    })),
    duties: dto.duties.map((d) => ({
      id: d.id,
      title: d.title,
      ownerPartyId: d.ownerPartyId ?? "",
      breachClause: d.breachClause,
    })),
    hasSchedule: dto.hasSchedule,
    profitShares: dto.profitShares.map((s) => ({ partyId: s.partyId, shareBp: s.shareBp })),
    profitFixedAmount: dto.profitFixedAmount,
    profitNotApplicable: dto.profitNotApplicable !== null,
    profitNaReason: dto.profitNotApplicable ?? "",
    lossText: dto.lossText,
    lossNotApplicable: dto.lossNotApplicable !== null,
    lossNaReason: dto.lossNotApplicable ?? "",
    custodyLocation: dto.custodyLocation,
    keeperPartyId: dto.keeperPartyId ?? "",
    reviewEveryDays: dto.reviewEveryDays,
    exitNoticeDays: dto.exitNoticeDays,
    exitValuation: dto.exitValuation,
    exitPayout: dto.exitPayout,
    exitAssets: dto.exitAssets,
    exitNotApplicable: dto.exitNotApplicable !== null,
    exitNaReason: dto.exitNotApplicable ?? "",
    arbiterName: dto.arbiterName,
    arbiterRole: dto.arbiterRole,
    termMonths: dto.termMonths,
    reviewDate: dto.reviewDate,
  };
}

/** Forma qiymatlari → backend DTO. */
export function toDto(form: AnswersForm): AgreementAnswersDto {
  return {
    parties: form.parties,
    contributions: form.contributions,
    duties: form.duties.map((d) => ({
      id: d.id,
      title: d.title,
      ownerPartyId: d.ownerPartyId === "" ? null : d.ownerPartyId,
      breachClause: d.breachClause,
    })),
    hasSchedule: form.hasSchedule,
    profitShares: form.profitShares,
    profitFixedAmount: form.profitFixedAmount,
    profitNotApplicable: form.profitNotApplicable ? form.profitNaReason : null,
    lossText: form.lossText,
    lossNotApplicable: form.lossNotApplicable ? form.lossNaReason : null,
    custodyLocation: form.custodyLocation,
    keeperPartyId: form.keeperPartyId === "" ? null : form.keeperPartyId,
    reviewEveryDays: form.reviewEveryDays,
    exitNoticeDays: form.exitNoticeDays,
    exitValuation: form.exitValuation,
    exitPayout: form.exitPayout,
    exitAssets: form.exitAssets,
    exitNotApplicable: form.exitNotApplicable ? form.exitNaReason : null,
    arbiterName: form.arbiterName,
    arbiterRole: form.arbiterRole,
    termMonths: form.termMonths,
    reviewDate: form.reviewDate,
  };
}

function isKind(value: string): value is "money" | "goods" | "labor" | "connections" {
  return value === "money" || value === "goods" || value === "labor" || value === "connections";
}

/** Yangi tomon/vazifa uchun qisqa identifikator (kelishuv ichida yagona). */
export function nextId(prefix: string, existing: readonly { id: string }[]): string {
  let n = existing.length + 1;
  const taken = new Set(existing.map((e) => e.id));
  while (taken.has(`${prefix}${String(n)}`)) {
    n += 1;
  }
  return `${prefix}${String(n)}`;
}
