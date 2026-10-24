import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'sync_meta.freezed.dart';
part 'sync_meta.g.dart';

/// Har bir yozuvdagi umumiy maydonlar (SPEC 4.4) — kelajakdagi
/// sinxronlash uchun.
@freezed
abstract class SyncMeta with _$SyncMeta {
  const factory SyncMeta({
    /// UUIDv7.
    required String id,
    required String householdId,

    /// UTC.
    required DateTime createdAt,

    /// UTC.
    required DateTime updatedAt,

    /// Soft delete (UTC). `null` — faol yozuv.
    DateTime? deletedAt,

    /// Optimistik versiya: har o'zgarishda +1.
    @Default(1) int version,
  }) = _SyncMeta;

  const SyncMeta._();

  bool get isDeleted => deletedAt != null;
}

/// Sinx maydonlari bor domen obyekti.
// Interfeys: repository'lar umumiy kodi uchun.
// ignore: one_member_abstracts
abstract interface class Synced {
  SyncMeta get meta;
}

/// Yangi yozuv uchun meta (ID + vaqt) yaratadi.
class SyncMetaFactory {
  const SyncMetaFactory(this._ids, this._clock);

  final UuidV7Generator _ids;
  final Clock _clock;

  SyncMeta create(String householdId) {
    final now = _clock.nowUtc();
    return SyncMeta(
      id: _ids.next(),
      householdId: householdId,
      createdAt: now,
      updatedAt: now,
    );
  }

  /// Uy xo'jaligining o'zi: `householdId == id`.
  SyncMeta createHousehold() {
    final now = _clock.nowUtc();
    final id = _ids.next();
    return SyncMeta(id: id, householdId: id, createdAt: now, updatedAt: now);
  }
}

@Riverpod(keepAlive: true)
SyncMetaFactory syncMetaFactory(Ref ref) =>
    SyncMetaFactory(ref.watch(idGeneratorProvider), ref.watch(clockProvider));
