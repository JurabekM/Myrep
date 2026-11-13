import 'package:drift/drift.dart';

import '../db/database.dart';
import 'context.dart';

class InstrumentRepository {
  InstrumentRepository(this._ctx);
  final DataContext _ctx;
  ZanjirDatabase get _db => _ctx.db;

  Future<InstrumentRow> create({
    required String kind,
    required String model,
    required String serialNo,
    String? verificationCertNo,
    DateTime? verifiedUntil,
  }) async {
    final now = _ctx.now();
    return _db
        .into(_db.instruments)
        .insertReturning(
          InstrumentsCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            kind: kind,
            model: model,
            serialNo: serialNo,
            verificationCertNo: Value(verificationCertNo),
            verifiedUntil: Value(verifiedUntil?.toUtc()),
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<InstrumentRow?> get(String id) => (_db.select(
    _db.instruments,
  )..where((i) => i.id.equals(id) & i.orgId.equals(_ctx.orgId) & i.deleted.equals(false))).getSingleOrNull();

  Future<List<InstrumentRow>> list() =>
      (_db.select(_db.instruments)
            ..where((i) => i.orgId.equals(_ctx.orgId) & i.deleted.equals(false))
            ..orderBy([(i) => OrderingTerm(expression: i.serialNo)]))
          .get();

  Future<InstrumentRow> update(InstrumentRow changed) async {
    final old = await get(changed.id) ?? (throw NotFoundException('instrument', changed.id));
    final row = changed.copyWith(
      orgId: _ctx.orgId,
      createdAt: old.createdAt,
      updatedAt: _ctx.now(),
      rev: old.rev + 1,
      deleted: false,
    );
    await _db.update(_db.instruments).replace(row);
    return row;
  }

  Future<void> softDelete(String id) async {
    final old = await get(id) ?? (throw NotFoundException('instrument', id));
    await _db.update(_db.instruments).replace(old.copyWith(deleted: true, updatedAt: _ctx.now(), rev: old.rev + 1));
  }

  /// Qiyoslash guvohnomasi `at` kuni amal qiladimi — [instrumentVerificationValid].
  bool isVerificationValid(InstrumentRow instrument, DateTime at) => instrumentVerificationValid(instrument, at);
}

/// Qiyoslash guvohnomasi `at` kuni amal qiladimi (oxirgi kun ham kiradi). Muddat kiritilmagan — yaroqsiz
/// (CLAUDE.md, 6-qoida: muddati o'tgan asbob bilan olingan o'lchov imzolanmaydi).
bool instrumentVerificationValid(InstrumentRow instrument, DateTime at) {
  final until = instrument.verifiedUntil?.toUtc();
  if (until == null) return false;
  final day = at.toUtc();
  return !DateTime.utc(day.year, day.month, day.day).isAfter(DateTime.utc(until.year, until.month, until.day));
}
