import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'context.dart';

class SiteRepository {
  SiteRepository(this._ctx);
  final DataContext _ctx;
  ZanjirDatabase get _db => _ctx.db;

  Future<SiteRow> create({
    required String name,
    String? address,
    String? customer,
    EarthingSystem? earthingSystem,
    double? u0Volts,
  }) async {
    final now = _ctx.now();
    return _db
        .into(_db.sites)
        .insertReturning(
          SitesCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            name: name,
            address: Value(address),
            customer: Value(customer),
            earthingSystem: Value(earthingSystem),
            u0Volts: Value(u0Volts),
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<SiteRow?> get(String id) => (_db.select(
    _db.sites,
  )..where((s) => s.id.equals(id) & s.orgId.equals(_ctx.orgId) & s.deleted.equals(false))).getSingleOrNull();

  Future<SiteRow> require(String id) async => await get(id) ?? (throw NotFoundException('site', id));

  Future<List<SiteRow>> list() =>
      (_db.select(_db.sites)
            ..where((s) => s.orgId.equals(_ctx.orgId) & s.deleted.equals(false))
            ..orderBy([(s) => OrderingTerm(expression: s.name)]))
          .get();

  /// O'zgartirilgan yozuvni saqlaydi: `org_id`, `created_at` o'zgarmaydi, `rev` va `updated_at` yangilanadi.
  Future<SiteRow> update(SiteRow changed) async {
    final old = await require(changed.id);
    final row = changed.copyWith(
      orgId: _ctx.orgId,
      createdAt: old.createdAt,
      updatedAt: _ctx.now(),
      rev: old.rev + 1,
      deleted: false,
    );
    await _db.update(_db.sites).replace(row);
    return row;
  }

  Future<void> softDelete(String id) async {
    final old = await require(id);
    await _db.update(_db.sites).replace(old.copyWith(deleted: true, updatedAt: _ctx.now(), rev: old.rev + 1));
  }

  Site toCore(SiteRow row) =>
      Site(id: row.id, name: row.name, earthingSystem: row.earthingSystem, u0Volts: row.u0Volts);
}
