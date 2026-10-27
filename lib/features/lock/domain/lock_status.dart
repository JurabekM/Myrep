enum LockStatus {
  /// PIN mavjudligi tekshirilmoqda.
  loading,

  /// Birinchi ishga tushirish — PIN hali o'rnatilmagan.
  needsSetup,

  locked,
  unlocked,
}
