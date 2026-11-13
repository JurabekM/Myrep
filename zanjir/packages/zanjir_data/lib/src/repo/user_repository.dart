import 'package:drift/drift.dart';

import '../db/database.dart';
import 'context.dart';

class UserRepository {
  UserRepository(this._ctx);
  final DataContext _ctx;
  ZanjirDatabase get _db => _ctx.db;

  /// Parol xeshi qurilmada saqlanmaydi — autentifikatsiya serverda (7-faza).
  Future<AppUserRow> create({
    required String fullName,
    required String phone,
    required String role,
    String? safetyGroup,
  }) async {
    final now = _ctx.now();
    return _db
        .into(_db.appUsers)
        .insertReturning(
          AppUsersCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            fullName: fullName,
            phone: phone,
            role: role,
            safetyGroup: Value(safetyGroup),
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<AppUserRow?> get(String id) => (_db.select(
    _db.appUsers,
  )..where((u) => u.id.equals(id) & u.orgId.equals(_ctx.orgId) & u.deleted.equals(false))).getSingleOrNull();

  Future<AppUserRow> require(String id) async => await get(id) ?? (throw NotFoundException('app_user', id));
}

class DeviceRepository {
  DeviceRepository(this._ctx);
  final DataContext _ctx;
  ZanjirDatabase get _db => _ctx.db;

  /// Qurilmani ochiq kaliti bilan ro'yxatdan o'tkazadi (maxfiy kalit qurilmadan chiqmaydi).
  Future<DeviceRow> register({required String userId, required String publicKeyHex, required String sigAlg}) async {
    await UserRepository(_ctx).require(userId);
    final now = _ctx.now();
    return _db
        .into(_db.devices)
        .insertReturning(
          DevicesCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            userId: userId,
            publicKeyEd25519: publicKeyHex,
            sigAlg: sigAlg,
            registeredAt: now,
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  Future<DeviceRow?> get(String id) => (_db.select(
    _db.devices,
  )..where((d) => d.id.equals(id) & d.orgId.equals(_ctx.orgId) & d.deleted.equals(false))).getSingleOrNull();

  Future<DeviceRow> revoke(String id) async {
    final d = await get(id) ?? (throw NotFoundException('device', id));
    final now = _ctx.now();
    final updated = d.copyWith(revokedAt: Value(now), updatedAt: now, rev: d.rev + 1);
    await _db.update(_db.devices).replace(updated);
    return updated;
  }
}
