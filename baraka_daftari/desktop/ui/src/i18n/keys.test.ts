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
    ].map((k) => `errors.${k}`),
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
