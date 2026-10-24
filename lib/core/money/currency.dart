/// Qo'llab-quvvatlanadigan valyutalar (SPEC 4.2). Asosiy valyuta — `uzs`.
///
/// Bazada enum nomi (`uzs`, `usd` …) saqlanadi — nomlarni o'zgartirish
/// migratsiya talab qiladi.
enum CurrencyCode {
  /// So'm; minor birlik — tiyin.
  uzs(minorDigits: 2, iso: 'UZS'),
  usd(minorDigits: 2, iso: 'USD'),
  eur(minorDigits: 2, iso: 'EUR'),
  rub(minorDigits: 2, iso: 'RUB');

  const CurrencyCode({required this.minorDigits, required this.iso});

  /// Kasr qismidagi raqamlar soni (UZS uchun 2 — tiyin).
  final int minorDigits;

  /// ISO 4217 kodi.
  final String iso;

  /// 1 major birlikdagi minor birliklar soni (masalan, 1 so'm = 100 tiyin).
  int get minorPerMajor => _pow10(minorDigits);

  static CurrencyCode fromIso(String iso) => values.firstWhere(
    (c) => c.iso == iso.toUpperCase(),
    orElse: () => throw ArgumentError.value(iso, 'iso', "Noma'lum valyuta"),
  );
}

int _pow10(int n) {
  var r = 1;
  for (var i = 0; i < n; i++) {
    r *= 10;
  }
  return r;
}
