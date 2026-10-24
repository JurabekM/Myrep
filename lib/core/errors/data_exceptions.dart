/// Yozuv boshqa joyda o'zgartirilgan (versiya mos emas) yoki o'chirilgan.
class ConcurrentModificationException implements Exception {
  const ConcurrentModificationException(this.entity, this.id);

  final String entity;
  final String id;

  @override
  String toString() => 'ConcurrentModificationException($entity, $id)';
}

/// Domen qoidasi buzildi (masalan, pul olishda sabab ko'rsatilmagan).
class DomainRuleException implements Exception {
  const DomainRuleException(this.code);

  /// Mashina o'qiydigan kod; UI uni ARB matniga aylantiradi.
  final String code;

  @override
  String toString() => 'DomainRuleException($code)';
}
