import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:zanjir_core/zanjir_core.dart';

import '../db/database.dart';
import 'context.dart';

/// Normalar to'plamlari: YAML o'zgarishsiz saqlanadi, `sha256` bilan himoyalangan.
class NormSetRepository {
  NormSetRepository(this._ctx);
  final DataContext _ctx;
  final _parsed = <String, NormSet>{};
  ZanjirDatabase get _db => _ctx.db;

  /// YAML'ni tekshirib saqlaydi ([NormFormatException]). Bir xil versiya, boshqa mazmun — `norm_set_version_conflict`.
  Future<NormSetRow> import(String yaml) async {
    final set = NormSet.fromYaml(yaml);
    final sha = sha256Hex(utf8.encode(yaml));
    final existing = await _byVersion(set.version);
    if (existing != null) {
      if (existing.sha256 != sha) throw DataRuleException('norm_set_version_conflict', set.version);
      return existing;
    }
    final now = _ctx.now();
    return _db
        .into(_db.normSets)
        .insertReturning(
          NormSetsCompanion.insert(
            id: _ctx.newId(),
            orgId: _ctx.orgId,
            version: set.version,
            sha256: sha,
            yaml: yaml,
            reviewedBy: Value(set.reviewedBy.trim().isEmpty ? null : set.reviewedBy),
            reviewedAt: Value(set.reviewedAt.trim().isEmpty ? null : set.reviewedAt),
            createdAt: now,
            updatedAt: now,
          ),
        );
  }

  /// Versiya bo'yicha yuklaydi; bazadagi YAML hash'i mos kelmasa — `norm_set_tampered`.
  Future<NormSet> load(String version) async {
    final row = await _byVersion(version) ?? (throw NotFoundException('norm_set', version));
    if (sha256Hex(utf8.encode(row.yaml)) != row.sha256) throw DataRuleException('norm_set_tampered', version);
    return _parsed[row.sha256] ??= NormSet.fromYaml(row.yaml);
  }

  /// Bazadagi yozuv (YAML, sha256, `reviewed_by`) — yo'q bo'lsa `null`.
  Future<NormSetRow?> row(String version) => _byVersion(version);

  Future<NormSetRow?> _byVersion(String version) => (_db.select(
    _db.normSets,
  )..where((n) => n.version.equals(version) & n.orgId.equals(_ctx.orgId) & n.deleted.equals(false))).getSingleOrNull();
}
