import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'audit_repository.dart';
import 'context.dart';
import 'norm_set_repository.dart';
import 'user_repository.dart';

/// Laboratoriya sozlamalari (ADR-0009). Effektiv zaxira = max(normalar to'plami, laboratoriya).
class LabSettings {
  const LabSettings({this.kCorr = 1.0, this.marginPct = 0, this.activeNormSetVersion});
  final double kCorr;
  final double marginPct;
  final String? activeNormSetVersion;

  EvalSettings get evalSettings => EvalSettings(kCorr: kCorr, marginPct: marginPct);
}

/// Sozlamalarni faqat LEAD/ADMIN o'zgartiradi; har bir o'zgarish audit zanjiriga yoziladi.
class SettingsRepository {
  SettingsRepository(this._ctx, {this._audit});
  final DataContext _ctx;
  final AuditRepository? _audit;
  ZanjirDatabase get _db => _ctx.db;

  static const editorRoles = {'LEAD', 'ADMIN'};

  Future<LabSettings> current() async {
    final row = await _row();
    if (row == null) return const LabSettings();
    return LabSettings(kCorr: row.kCorr, marginPct: row.marginPct, activeNormSetVersion: row.activeNormSetVersion);
  }

  Future<LabSettings> update({
    required String byUserId,
    double? kCorr,
    double? marginPct,
    String? activeNormSetVersion,
  }) => _db.transaction(() async {
    await requireRole(_ctx, byUserId, editorRoles);
    final audit = _audit ?? (throw StateError('SettingsRepository: audit kerak'));
    final old = await current();
    final next = LabSettings(
      kCorr: kCorr ?? old.kCorr,
      marginPct: marginPct ?? old.marginPct,
      activeNormSetVersion: activeNormSetVersion ?? old.activeNormSetVersion,
    );
    if (!(next.kCorr > 0 && next.kCorr <= 1)) throw DataRuleException('invalid_k_corr', '${next.kCorr}');
    if (!(next.marginPct >= 0 && next.marginPct <= 50)) throw DataRuleException('invalid_margin', '${next.marginPct}');
    final version = next.activeNormSetVersion;
    if (version != null) await NormSetRepository(_ctx).load(version);

    final now = _ctx.now();
    final row = await _row();
    if (row == null) {
      await _db
          .into(_db.orgSettings)
          .insert(
            OrgSettingsCompanion.insert(
              id: _ctx.newId(),
              orgId: _ctx.orgId,
              kCorr: Value(next.kCorr),
              marginPct: Value(next.marginPct),
              activeNormSetVersion: Value(version),
              createdAt: now,
              updatedAt: now,
            ),
          );
    } else {
      await _db
          .update(_db.orgSettings)
          .replace(
            row.copyWith(
              kCorr: next.kCorr,
              marginPct: next.marginPct,
              activeNormSetVersion: Value(version),
              updatedAt: now,
              rev: row.rev + 1,
            ),
          );
    }
    await audit.append(
      eventType: 'SETTINGS_CHANGED',
      entityId: _ctx.orgId,
      payload: {'k_corr': next.kCorr, 'margin_pct': next.marginPct, 'active_norm_set_version': version},
    );
    return next;
  });

  Future<OrganizationRow> organization() async =>
      await (_db.select(
        _db.organizations,
      )..where((o) => o.id.equals(_ctx.orgId) & o.deleted.equals(false))).getSingleOrNull() ??
      (throw NotFoundException('organization', _ctx.orgId));

  /// Laboratoriya rekvizitlari (nomi, litsenziya) — faqat LEAD/ADMIN.
  Future<OrganizationRow> updateLab({
    required String byUserId,
    required String name,
    String? licenseNo,
    DateTime? licenseValidUntil,
  }) => _db.transaction(() async {
    await requireRole(_ctx, byUserId, editorRoles);
    final audit = _audit ?? (throw StateError('SettingsRepository: audit kerak'));
    final org = await organization();
    final row = org.copyWith(
      name: name,
      licenseNo: Value(licenseNo),
      licenseValidUntil: Value(licenseValidUntil?.toUtc()),
      updatedAt: _ctx.now(),
      rev: org.rev + 1,
    );
    await _db.update(_db.organizations).replace(row);
    await audit.append(
      eventType: 'LAB_UPDATED',
      entityId: org.id,
      payload: {'name': name, 'license_no': licenseNo, 'license_valid_until': row.licenseValidUntil},
    );
    return row;
  });

  Future<OrgSettingRow?> _row() =>
      (_db.select(_db.orgSettings)..where((s) => s.orgId.equals(_ctx.orgId))).getSingleOrNull();
}

/// Foydalanuvchi shu tashkilotda va ruxsat etilgan rolda; aks holda NotFound / `forbidden_role`.
Future<AppUserRow> requireRole(DataContext ctx, String userId, Set<String> roles) async {
  final user = await UserRepository(ctx).require(userId);
  if (!roles.contains(user.role)) throw DataRuleException('forbidden_role', user.role);
  return user;
}

/// Qurilmaga xos sozlamalar (sinxronlanmaydi): joriy profil, til, katta shrift.
class LocalPrefRepository {
  LocalPrefRepository(this._db);
  final ZanjirDatabase _db;

  static const orgId = 'profile.org_id';
  static const userId = 'profile.user_id';
  static const deviceId = 'profile.device_id';
  static const locale = 'ui.locale';
  static const largeText = 'ui.large_text';

  /// Oxirgi muvaffaqiyatli saqlangan zaxira vaqti (ISO, UTC) — eslatma uchun.
  static const lastBackupAt = 'backup.last_at';

  Future<String?> get(String key) async =>
      (await (_db.select(_db.localPrefs)..where((p) => p.key.equals(key))).getSingleOrNull())?.value;

  Future<void> set(String key, String value) =>
      _db.into(_db.localPrefs).insertOnConflictUpdate(LocalPrefsCompanion.insert(key: key, value: value));

  Future<void> remove(String key) => (_db.delete(_db.localPrefs)..where((p) => p.key.equals(key))).go();
}
