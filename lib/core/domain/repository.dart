import 'package:baraka_daftari/core/domain/sync_meta.dart';

/// Barcha aggregate repository'lari uchun umumiy amallar (domen tomoni).
abstract interface class SyncedRepository<E extends Synced> {
  /// Yangi yozuv; `meta` `SyncMetaFactory` bilan oldindan yaratiladi.
  Future<E> add(E entity);

  /// Optimistik yangilash: bazadagi versiya `entity.meta.version` ga teng
  /// bo'lmasa — `ConcurrentModificationException`. Natijada versiya +1.
  Future<E> update(E entity);

  /// Soft delete: `deletedAt` qo'yiladi, yozuv o'chirilmaydi.
  Future<void> softDelete(String id);

  /// O'chirilgan yozuv ham qaytariladi (tarix uchun).
  Future<E?> findById(String id);

  /// Faol (o'chirilmagan) yozuvlar.
  Future<List<E>> listActive(String householdId);

  Stream<List<E>> watchActive(String householdId);
}
