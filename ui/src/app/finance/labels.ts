/**
 * Backend kodlari → tarjima kalitlari. Kod va matn bir joyda: yangi kod qo'shilsa, bu yerda ham qo'shiladi
 * (TypeScript `as const` orqali tekshiradi).
 */

export const OWNER_KEYS = {
  LANDLORD: "owners.LANDLORD",
  BANK: "owners.BANK",
  SHOP: "owners.SHOP",
  UTILITIES: "owners.UTILITIES",
  FUEL: "owners.FUEL",
  SELF: "owners.SELF",
  SADAQA: "owners.SADAQA",
  OTHER: "owners.OTHER",
  UNEXPLAINED: "owners.UNEXPLAINED",
} as const;

export const CATEGORY_KEYS = {
  RENT: "categories.RENT",
  CREDIT: "categories.CREDIT",
  GROCERIES: "categories.GROCERIES",
  DAILY_SMALL: "categories.DAILY_SMALL",
  SNACKS: "categories.SNACKS",
  UTILITIES: "categories.UTILITIES",
  PHONE: "categories.PHONE",
  FUEL: "categories.FUEL",
  TRANSPORT: "categories.TRANSPORT",
  SADAQA: "categories.SADAQA",
  CHILDREN: "categories.CHILDREN",
  CAFE: "categories.CAFE",
  OTHER: "categories.OTHER",
} as const;

export const OBLIGATION_KIND_KEYS = {
  RENT: "obligationKinds.RENT",
  CREDIT: "obligationKinds.CREDIT",
  UTILITY: "obligationKinds.UTILITY",
  PHONE: "obligationKinds.PHONE",
  FUEL: "obligationKinds.FUEL",
  OTHER: "obligationKinds.OTHER",
} as const;

/** Majburiyat turi kodi (`RENT`, …) uchun tarjima kaliti; noma'lum kod — «Boshqa». */
export function obligationKindKey(
  code: string,
): (typeof OBLIGATION_KIND_KEYS)[keyof typeof OBLIGATION_KIND_KEYS] {
  return code in OBLIGATION_KIND_KEYS
    ? OBLIGATION_KIND_KEYS[code as keyof typeof OBLIGATION_KIND_KEYS]
    : OBLIGATION_KIND_KEYS.OTHER;
}

/** Tizim kategoriyasi bo'lsa — tarjima kaliti; aks holda `null` (foydalanuvchi nomi ishlatiladi). */
export function categoryKey(
  systemKey: string | null,
): (typeof CATEGORY_KEYS)[keyof typeof CATEGORY_KEYS] | null {
  if (systemKey === null || !(systemKey in CATEGORY_KEYS)) {
    return null;
  }
  return CATEGORY_KEYS[systemKey as keyof typeof CATEGORY_KEYS];
}

/** Egasi kodi uchun tarjima kaliti; noma'lum kod — «Boshqa». */
export function ownerKey(code: string): (typeof OWNER_KEYS)[keyof typeof OWNER_KEYS] {
  return code in OWNER_KEYS ? OWNER_KEYS[code as keyof typeof OWNER_KEYS] : OWNER_KEYS.OTHER;
}
