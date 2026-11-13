import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';

/// Repozitoriylar uchun umumiy kontekst. Har bir so'rov `orgId` bilan filtrlanadi (CLAUDE.md, 7-qoida).
class DataContext {
  DataContext({required this.db, required this.orgId, DateTime Function()? clock, String Function()? newId})
    : _clock = clock ?? DateTime.now,
      newId = newId ?? uuidV7;

  final ZanjirDatabase db;
  final String orgId;
  final DateTime Function() _clock;
  final String Function() newId;

  /// Joriy vaqt, har doim UTC.
  DateTime now() => _clock().toUtc();
}

/// Yozuv topilmadi yoki boshqa tashkilotga tegishli (tashkilotlar orasida farq ko'rsatilmaydi).
class NotFoundException implements Exception {
  const NotFoundException(this.entity, this.id);
  final String entity;
  final String id;

  @override
  String toString() => 'NotFoundException: $entity $id';
}

/// Biznes qoidasi buzildi. `code` — barqaror inglizcha kalit (UI l10n orqali ko'rsatadi).
class DataRuleException implements Exception {
  const DataRuleException(this.code, [this.detail]);
  final String code;
  final String? detail;

  @override
  String toString() => 'DataRuleException: $code${detail == null ? '' : ' ($detail)'}';
}
