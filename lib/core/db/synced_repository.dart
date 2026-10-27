import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:drift/drift.dart';

export 'package:baraka_daftari/core/domain/repository.dart';

/// [SyncedRepository] ning Drift implementatsiyasi. Har aggregate faqat
/// qator ↔ domen o'girishini yozadi.
abstract class DriftSyncedRepository<
  T extends SyncColumns,
  R extends DataClass,
  E extends Synced
>
    implements SyncedRepository<E> {
  DriftSyncedRepository(this.db, this.clock);

  final AppDatabase db;
  final Clock clock;

  TableInfo<T, R> get table;

  /// Xatolar uchun nom.
  String get entityName;

  E fromRow(R row);

  /// Barcha ustunlar, shu jumladan meta.
  Insertable<R> toRow(E entity);

  E withMeta(E entity, SyncMeta meta);

  /// Faol yozuvlarning standart tartibi (yangilari birinchi).
  List<OrderingTerm Function(T)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.createdAt),
    (t) => OrderingTerm.desc(t.id),
  ];

  @override
  Future<E> add(E entity) async {
    await db.into(table).insert(toRow(entity));
    return entity;
  }

  @override
  Future<E> update(E entity) async {
    final old = entity.meta;
    final next = withMeta(
      entity,
      old.copyWith(updatedAt: clock.nowUtc(), version: old.version + 1),
    );
    final changed =
        await (db.update(table)..where(
              (t) =>
                  t.id.equals(old.id) &
                  t.version.equals(old.version) &
                  t.deletedAt.isNull(),
            ))
            .write(toRow(next));
    if (changed == 0) throw ConcurrentModificationException(entityName, old.id);
    return next;
  }

  /// Soft delete'ni bekor qilish («Bekor qilish»): `deletedAt` tozalanadi.
  /// Faqat o'chirilgan yozuv uchun; boshqa holatda hech narsa qilinmaydi.
  Future<void> restoreDeleted(String id) async {
    final now = clock.nowUtc();
    await db.customUpdate(
      'UPDATE ${table.actualTableName} '
      'SET deleted_at = NULL, updated_at = ?, version = version + 1 '
      'WHERE id = ? AND deleted_at IS NOT NULL',
      variables: [Variable<DateTime>(now), Variable<String>(id)],
      updates: {table},
      updateKind: UpdateKind.update,
    );
  }

  @override
  Future<void> softDelete(String id) async {
    final now = clock.nowUtc();
    final changed = await db.customUpdate(
      'UPDATE ${table.actualTableName} '
      'SET deleted_at = ?, updated_at = ?, version = version + 1 '
      'WHERE id = ? AND deleted_at IS NULL',
      variables: [
        Variable<DateTime>(now),
        Variable<DateTime>(now),
        Variable<String>(id),
      ],
      updates: {table},
      updateKind: UpdateKind.update,
    );
    if (changed == 0) throw ConcurrentModificationException(entityName, id);
  }

  @override
  Future<E?> findById(String id) async {
    final row = await (db.select(
      table,
    )..where((t) => t.id.equals(id))).getSingleOrNull();
    return row == null ? null : fromRow(row);
  }

  /// Uy xo'jaligining faol yozuvlari uchun asosiy so'rov.
  SimpleSelectStatement<T, R> activeQuery(String householdId) =>
      db.select(table)
        ..where((t) => t.householdId.equals(householdId) & t.deletedAt.isNull())
        ..orderBy(defaultOrder);

  @override
  Future<List<E>> listActive(String householdId) async =>
      (await activeQuery(householdId).get()).map(fromRow).toList();

  @override
  Stream<List<E>> watchActive(String householdId) => activeQuery(
    householdId,
  ).watch().map((rows) => rows.map(fromRow).toList());

  /// Qatordagi meta ustunlarini o'qish (vaqtlar UTC'ga keltiriladi).
  static SyncMeta metaOf({
    required String id,
    required String householdId,
    required DateTime createdAt,
    required DateTime updatedAt,
    required DateTime? deletedAt,
    required int version,
  }) => SyncMeta(
    id: id,
    householdId: householdId,
    createdAt: createdAt.toUtc(),
    updatedAt: updatedAt.toUtc(),
    deletedAt: deletedAt?.toUtc(),
    version: version,
  );
}
