import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';

/// Tashkilot yozuvi (sozlash va sinxronlash uchun; tashkilot kontekstidan tashqarida).
class OrganizationRepository {
  OrganizationRepository(this._db, {DateTime Function()? clock, String Function()? newId})
    : _clock = clock ?? DateTime.now,
      _newId = newId ?? uuidV7;

  final ZanjirDatabase _db;
  final DateTime Function() _clock;
  final String Function() _newId;

  Future<String> create({required String name, String? licenseNo, DateTime? licenseValidUntil}) async {
    final now = _clock().toUtc();
    final id = _newId();
    await _db
        .into(_db.organizations)
        .insert(
          OrganizationsCompanion.insert(
            id: id,
            name: name,
            licenseNo: Value(licenseNo),
            licenseValidUntil: Value(licenseValidUntil?.toUtc()),
            createdAt: now,
            updatedAt: now,
          ),
        );
    return id;
  }
}
