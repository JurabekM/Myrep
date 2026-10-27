import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:baraka_daftari/features/content/domain/content_records.dart';
import 'package:drift/drift.dart';

SyncMeta _meta(
  String id,
  String householdId,
  DateTime createdAt,
  DateTime updatedAt,
  DateTime? deletedAt,
  int version,
) => DriftSyncedRepository.metaOf(
  id: id,
  householdId: householdId,
  createdAt: createdAt,
  updatedAt: updatedAt,
  deletedAt: deletedAt,
  version: version,
);

class DriftDaftarPageRepository
    extends DriftSyncedRepository<$DaftarPagesTable, DaftarPageRow, DaftarPage>
    implements DaftarPageRepository {
  DriftDaftarPageRepository(super.db, super.clock);

  @override
  TableInfo<$DaftarPagesTable, DaftarPageRow> get table => db.daftarPages;

  @override
  String get entityName => 'daftar_page';

  @override
  DaftarPage fromRow(DaftarPageRow r) => DaftarPage(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    chapterId: r.chapterId,
    lawNumber: r.lawNumber,
    body: r.body,
  );

  @override
  Insertable<DaftarPageRow> toRow(DaftarPage e) => DaftarPagesCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    chapterId: e.chapterId,
    lawNumber: e.lawNumber,
    body: e.body,
  );

  @override
  DaftarPage withMeta(DaftarPage e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<DaftarPage?> forChapter(String householdId, String chapterId) async {
    final row =
        await (activeQuery(householdId)
              ..where((t) => t.chapterId.equals(chapterId))
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

class DriftTaskCompletionRepository
    extends
        DriftSyncedRepository<
          $TaskCompletionsTable,
          TaskCompletionRow,
          TaskCompletion
        >
    implements TaskCompletionRepository {
  DriftTaskCompletionRepository(super.db, super.clock);

  @override
  TableInfo<$TaskCompletionsTable, TaskCompletionRow> get table =>
      db.taskCompletions;

  @override
  String get entityName => 'task_completion';

  @override
  TaskCompletion fromRow(TaskCompletionRow r) => TaskCompletion(
    meta: _meta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    taskId: r.taskId,
    weekStart: r.weekStart,
    isAuto: r.isAuto,
  );

  @override
  Insertable<TaskCompletionRow> toRow(TaskCompletion e) =>
      TaskCompletionsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        taskId: e.taskId,
        weekStart: e.weekStart,
        isAuto: Value(e.isAuto),
      );

  @override
  TaskCompletion withMeta(TaskCompletion e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<TaskCompletion>> forWeek(
    String householdId,
    LocalDate weekStart,
  ) async {
    final rows = await (activeQuery(
      householdId,
    )..where((t) => t.weekStart.equalsValue(weekStart))).get();
    return rows.map(fromRow).toList();
  }

  @override
  Future<Map<String, DateTime>> firstCompletions(String householdId) async {
    final t = db.taskCompletions;
    final first = t.createdAt.min();
    final rows =
        await (db.selectOnly(t)
              ..addColumns([t.taskId, first])
              ..where(t.householdId.equals(householdId))
              ..groupBy([t.taskId]))
            .get();
    return {for (final r in rows) r.read(t.taskId)!: r.read(first)!};
  }
}
