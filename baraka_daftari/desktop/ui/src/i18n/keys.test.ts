import i18n from './index';

const sources = import.meta.glob<string>('../**/*.tsx', {
  query: '?raw',
  import: 'default',
  eager: true,
});

/** Kodda statik yozilgan har bir `t('kalit')` ikkala tilda ham mavjud bo'lishi shart. */
describe('i18n kalitlari', () => {
  const used = new Set<string>();
  for (const [file, text] of Object.entries(sources)) {
    if (file.endsWith('.test.tsx')) continue;
    for (const m of text.matchAll(/\bt\(\s*'([\w.]+)'/g)) {
      if (m[1]) used.add(m[1]);
    }
  }

  const dynamic = [
    ...['DAILY_WORK', 'ORDER', 'SALARY', 'OTHER'].map((k) => `source.${k}`),
    ...['CASH', 'CARD'].map((k) => `channel.${k}`),
    ...['LANDLORD', 'BANK', 'SHOP', 'STATE', 'FUEL', 'OTHER'].map((k) => `owner.${k}`),
    ...[
      'InvalidPin',
      'WrongPin',
      'Locked',
      'NotInitialized',
      'AlreadyInitialized',
      'KeyringMissing',
      'InvalidAmount',
      'NotFound',
      'InsufficientFunds',
      'OpeningBalanceExists',
      'Cooling',
      'Internal',
      'WrongPassword',
      'WeakPassword',
    ].map((k) => `errors.${k}`),
    ...['TER', 'MOL', 'TAVAKKAL', 'RIBO'].map((k) => `incomeType.${k}`),
    ...['GUARD_BELOW_TARGET', 'INTEREST_DEBT_NO_PLAN'].map((k) => `gate.reason.${k}`),
    ...['BANK', 'SHOP', 'RELATIVE', 'FRIEND', 'OTHER'].map((k) => `debts.creditorTypes.${k}`),
    ...['MANUAL', 'ANNUITY', 'DIFFERENTIATED', 'FIXED_MARKUP'].map((k) => `debts.kinds.${k}`),
    ...['NEED', 'LUXURY'].map((k) => `debts.friction.needOptions.${k}`),
    ...['NONE', 'GUARD', 'RELATIVE', 'SELL_ITEM'].map((k) => `debts.friction.alternatives.${k}`),
    ...['PRINT', 'DRAW'].map((k) => `receipt.mode.${k}`),
    ...['STANDARD', 'DEBT_RECOVERY'].map((k) => `recovery.modes.${k}`),
    ...['month', 'interest', 'principal', 'extra', 'balance'].map((k) => `calc.cols.${k}`),
    ...['WEDDING', 'BESHIK', 'SUNNAT', 'MARAKA', 'OTHER'].map((k) => `cer.kinds.${k}`),
    ...['DRAFT', 'CONFIRMED'].map((k) => `cer.statuses.${k}`),
    ...['SAVINGS', 'FAMILY', 'EXPECTED_GIFTS', 'DEBT'].map((k) => `cer.sources.${k}`),
    ...['smaller', 'longer', 'gifts', 'sell', 'family'].map((k) => `cer.prompts.${k}`),
    ...['DISCUSSION_REQUIRED', 'DATE_REQUIRED'].map((k) => `cer.blockers.${k}`),
    ...['DIVERGED', 'CLOSED_PERIOD', 'SIGNED_CONTRACT', 'JOURNAL', 'REJECTED'].map(
      (k) => `exchange.kinds.${k}`,
    ),
    ...['KEPT_LOCAL', 'TOOK_INCOMING', 'SKIPPED'].map((k) => `exchange.resolutions.${k}`),
    ...['welcome', 'income', 'vault', 'havas', 'safety'].flatMap((k) => [
      `onboarding.steps.${k}.title`,
      `onboarding.steps.${k}.body`,
    ]),
    ...['pess', 'avg', 'opt'].map((k) => `craft.scenarios.${k}`),
    ...['GREEN', 'YELLOW', 'RED'].flatMap((k) => [`offer.verdicts.${k}`, `offer.verdictText.${k}`]),
    ...[
      'GUARANTEED_PROFIT',
      'NO_LOSS_SHARING',
      'NO_REAL_ACTIVITY',
      'RECRUITMENT_REQUIRED',
      'PRESSURE',
      'NO_WRITTEN_CONTRACT',
    ].map((k) => `offer.flags.${k}`),
    ...['INCOME', 'EXPENSE'].map((k) => `ledger.kinds.${k}`),
    ...['MUDARABA', 'MUSHARAKA'].map((k) => `partner.kinds.${k}`),
    ...['MONTHLY', 'QUARTERLY', 'YEARLY'].map((k) => `partner.periods.${k}`),
    ...['CAPITAL_PROVIDER', 'WORKER', 'PARTNER'].map((k) => `partner.roles.${k}`),
    ...['CASH', 'EQUIPMENT'].map((k) => `partner.capKinds.${k}`),
    ...['DRAFT', 'ACTIVE', 'ENDED'].map((k) => `partner.statuses.${k}`),
    ...['PARTY_SIGNATURES', 'WITNESS_SIGNATURES', 'FAMILY_CONSENT', 'GATE_CLOSED'].map(
      (k) => `partner.blockers.${k}`,
    ),
    'audit.previous',
    'audit.current',
  ];

  it('kodda kalitlar topildi (regex ishlayapti)', () => {
    expect(used.size).toBeGreaterThan(40);
  });

  it.each(['uz', 'ru'])('%s: barcha kalitlar mavjud', (lng) => {
    const t = i18n.getFixedT(lng);
    const missing = [...used, ...dynamic].filter((k) => !i18n.exists(k, { lng }));
    expect(missing).toEqual([]);
    expect(t('nav.home')).not.toBe('nav.home');
  });
});
