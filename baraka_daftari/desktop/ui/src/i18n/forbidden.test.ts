import ru from './ru.json';
import uz from './uz.json';

/**
 * Ribo filtri (SPEC 2C.5): ilova foizli omonat, obligatsiya yoki «kafolatlangan foiz»ni tavsiya
 * ham, reklama ham qilmaydi va foizni «muqobil daromad» deb ko'rsatmaydi.
 */
export const FORBIDDEN: RegExp[] = [
  /foizli\s+(omonat|depozit|obligatsiya)/i,
  /kafolatlangan\s+(foiz|daromad|foyda)/i,
  /(foiz|bank)\s+(stavka|daromad)\w*\s+(oling|ishlang|toping)/i,
  /muqobil\s+(daromad|foiz)/i,
  /(процентн\p{L}*|депозитн\p{L}*)\s+(вклад|депозит|облигаци)\p{L}*/iu,
  /гарантированн\p{L}*\s+(процент|доход|прибыл)\p{L}*/iu,
  /альтернативн\p{L}*\s+(доход|процент)\p{L}*/iu,
  /(микрозайм|быстр\p{L}+\s+деньги|tez\s+pul\s+kredit|mikroqarz)/iu,
];

function flatten(node: unknown, path = ''): [string, string][] {
  if (typeof node === 'string') return [[path, node]];
  if (node && typeof node === 'object') {
    return Object.entries(node).flatMap(([k, v]) => flatten(v, path ? `${path}.${k}` : k));
  }
  return [];
}

describe('taqiqlangan iboralar (ribo filtri)', () => {
  it.each([
    ['uz', uz],
    ['ru', ru],
  ])('%s: matnlarda foizli mahsulot tavsiyasi yo‘q', (_lng, dict) => {
    const hits = flatten(dict).filter(([, text]) => FORBIDDEN.some((re) => re.test(text)));
    expect(hits).toEqual([]);
  });

  it('filtr o‘zi ishlaydi (taqiqlangan namunalarni tutadi)', () => {
    for (const bad of [
      'Foizli omonat oching',
      'Kafolatlangan foiz bilan daromad',
      'Bu — muqobil daromad manbai',
      'Выгодный процентный вклад',
      'Гарантированный процент',
      'Альтернативный доход',
    ]) {
      expect(FORBIDDEN.some((re) => re.test(bad))).toBe(true);
    }
  });

  it('halol matnlar (qarz va ribo haqida ogohlantirish) to‘siqqa tushmaydi', () => {
    for (const ok of ['Foizli qarzim bor', 'Foizli daromad (ribo)', 'Процентный долг']) {
      expect(FORBIDDEN.some((re) => re.test(ok))).toBe(false);
    }
  });
});
