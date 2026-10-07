import i18n from '../i18n';

import {
  ApiError,
  errorMessage,
  formatBp,
  formatMilli,
  formatSignedBp,
  formatX100,
  unwrap,
} from './api';

describe('formatBp', () => {
  it("bazis punktni foizga o'giradi", () => {
    expect(formatBp(500)).toBe('5%');
    expect(formatBp(1000)).toBe('10%');
    expect(formatBp(550)).toBe('5,5%');
    expect(formatBp(505)).toBe('5,05%');
    expect(formatBp(0)).toBe('0%');
  });
});

describe('unwrap / errorMessage', () => {
  const t = i18n.getFixedT('uz');

  it("xatoda ApiError tashlaydi, muvaffaqiyatda ma'lumotni qaytaradi", async () => {
    await expect(unwrap(Promise.resolve({ status: 'ok' as const, data: 7 }))).resolves.toBe(7);
    await expect(
      unwrap(Promise.resolve({ status: 'error' as const, error: { kind: 'WrongPin' as const } })),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it('xato turlari uchun mos matn beradi', () => {
    expect(errorMessage(t, new ApiError({ kind: 'WrongPin' }))).toBe("PIN noto'g'ri.");
    expect(errorMessage(t, new ApiError({ kind: 'Cooling', remaining_secs: 42 }))).toContain('42');
    expect(errorMessage(t, new ApiError({ kind: 'Invalid', message: 'Sababni yozing' }))).toBe(
      'Sababni yozing',
    );
    expect(errorMessage(t, new Error('boom'))).toBe(t('errors.Internal'));
  });
});

describe('matn formatlari', () => {
  it('ishorali bazis punkt', () => {
    expect(formatSignedBp(6250)).toBe('+62,5%');
    expect(formatSignedBp(-550)).toBe('−5,5%');
    expect(formatSignedBp(0)).toBe('0%');
  });
  it('oylar x100', () => {
    expect(formatX100(140)).toBe('1,4');
    expect(formatX100(600)).toBe('6');
    expect(formatX100(5)).toBe('0,05');
  });
  it('miqdor 1/1000', () => {
    expect(formatMilli('12345')).toBe('12,3');
    expect(formatMilli('2000')).toBe('2');
    expect(formatMilli('99')).toBe('0');
  });
});
