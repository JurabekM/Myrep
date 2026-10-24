import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/domain/journal.dart';
import 'package:drift/drift.dart';

SyncMeta _rowMeta(
  String id,
  String hh,
  DateTime c,
  DateTime u,
  DateTime? d,
  int v,
) => DriftSyncedRepository.metaOf(
  id: id,
  householdId: hh,
  createdAt: c,
  updatedAt: u,
  deletedAt: d,
  version: v,
);

class DriftAgreementRepository
    extends DriftSyncedRepository<$AgreementsTable, AgreementRow, Agreement>
    implements AgreementRepository {
  DriftAgreementRepository(super.db, super.clock);

  @override
  TableInfo<$AgreementsTable, AgreementRow> get table => db.agreements;

  @override
  String get entityName => 'agreement';

  @override
  Agreement fromRow(AgreementRow r) => Agreement(
    meta: _rowMeta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    type: r.type,
    title: r.title,
    status: r.status,
    effectiveFrom: r.effectiveFrom,
    currentVersion: r.currentVersion,
    source: r.source,
    sourceId: r.sourceId,
    oral: r.oral,
    legacy: r.legacy,
    reviewDate: r.reviewDate,
  );

  @override
  Insertable<AgreementRow> toRow(Agreement e) => AgreementsCompanion.insert(
    id: e.meta.id,
    householdId: e.meta.householdId,
    createdAt: e.meta.createdAt,
    updatedAt: e.meta.updatedAt,
    deletedAt: Value(e.meta.deletedAt),
    version: Value(e.meta.version),
    type: e.type,
    status: e.status,
    title: e.title,
    effectiveFrom: e.effectiveFrom,
    currentVersion: Value(e.currentVersion),
    source: Value(e.source),
    sourceId: Value(e.sourceId),
    oral: Value(e.oral),
    legacy: Value(e.legacy),
    reviewDate: Value(e.reviewDate),
  );

  @override
  Agreement withMeta(Agreement e, SyncMeta meta) => e.copyWith(meta: meta);

  @override
  Future<Agreement?> bySource(AgreementSource source, String sourceId) async {
    final row =
        await (db.select(db.agreements)
              ..where(
                (t) =>
                    t.source.equalsValue(source) &
                    t.sourceId.equals(sourceId) &
                    t.deletedAt.isNull(),
              )
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}

class DriftAgreementVersionRepository
    extends
        DriftSyncedRepository<
          $AgreementVersionsTable,
          AgreementVersionRow,
          AgreementVersion
        >
    implements AgreementVersionRepository {
  DriftAgreementVersionRepository(super.db, super.clock);

  @override
  TableInfo<$AgreementVersionsTable, AgreementVersionRow> get table =>
      db.agreementVersions;

  @override
  String get entityName => 'agreement_version';

  @override
  AgreementVersion fromRow(AgreementVersionRow r) => AgreementVersion(
    meta: _rowMeta(
      r.id,
      r.householdId,
      r.createdAt,
      r.updatedAt,
      r.deletedAt,
      r.version,
    ),
    agreementId: r.agreementId,
    version: r.versionNo,
    answers: AgreementAnswers.decode(r.answersJson),
    note: r.note,
  );

  @override
  Insertable<AgreementVersionRow> toRow(AgreementVersion e) =>
      AgreementVersionsCompanion.insert(
        id: e.meta.id,
        householdId: e.meta.householdId,
        createdAt: e.meta.createdAt,
        updatedAt: e.meta.updatedAt,
        deletedAt: Value(e.meta.deletedAt),
        version: Value(e.meta.version),
        agreementId: e.agreementId,
        versionNo: e.version,
        answersJson: e.answers.encode(),
        note: Value(e.note),
      );

  @override
  AgreementVersion withMeta(AgreementVersion e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<List<AgreementVersion>> forAgreement(String agreementId) async => [
    for (final r
        in await (db.select(db.agreementVersions)
              ..where(
                (t) => t.agreementId.equals(agreementId) & t.deletedAt.isNull(),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.versionNo)]))
            .get())
      fromRow(r),
  ];
}

/// Append-only jurnal: faqat `append` va o'qish.
class DriftJournalRepository implements JournalRepository {
  DriftJournalRepository(this._db, this._meta);

  final AppDatabase _db;
  final SyncMetaFactory _meta;

  JournalEntry _fromRow(JournalEntryRow r) => JournalEntry(
    meta: _metaOf(r),
    agreementId: r.agreementId,
    seq: r.seq,
    kind: JournalKind.fromCode(r.kind),
    partyId: r.partyId,
    amount: r.amountMinor == null ? null : Money(r.amountMinor!, r.currency!),
    date: r.entryDate,
    note: r.note,
    refId: r.refId,
    prevHash: r.prevHash,
    hash: r.hash,
  );

  SyncMeta _metaOf(JournalEntryRow r) => _rowMeta(
    r.id,
    r.householdId,
    r.createdAt,
    r.updatedAt,
    r.deletedAt,
    r.version,
  );

  @override
  Future<JournalEntry> append(String agreementId, JournalDraft d) =>
      _db.transaction(() async {
        final agreement = await (_db.select(
          _db.agreements,
        )..where((t) => t.id.equals(agreementId))).getSingle();
        final last =
            await (_db.select(_db.journalEntries)
                  ..where((t) => t.agreementId.equals(agreementId))
                  ..orderBy([(t) => OrderingTerm.desc(t.seq)])
                  ..limit(1))
                .getSingleOrNull();
        final seq = (last?.seq ?? 0) + 1;
        final prev = last?.hash ?? genesisHash;
        final meta = _meta.create(agreement.householdId);
        final hash = chainHash(
          prev,
          journalCanonical(
            id: meta.id,
            agreementId: agreementId,
            kind: d.kind,
            date: d.date,
            partyId: d.partyId,
            amount: d.amount,
            note: d.note,
            refId: d.refId,
          ),
        );
        await _db
            .into(_db.journalEntries)
            .insert(
              JournalEntriesCompanion.insert(
                id: meta.id,
                householdId: meta.householdId,
                createdAt: meta.createdAt,
                updatedAt: meta.updatedAt,
                agreementId: agreementId,
                seq: seq,
                kind: d.kind.code,
                partyId: Value(d.partyId),
                amountMinor: Value(d.amount?.minorUnits),
                currency: Value(d.amount?.currency),
                entryDate: d.date,
                note: Value(d.note),
                refId: Value(d.refId),
                prevHash: prev,
                hash: hash,
              ),
            );
        return JournalEntry(
          meta: meta,
          agreementId: agreementId,
          seq: seq,
          kind: d.kind,
          partyId: d.partyId,
          amount: d.amount,
          date: d.date,
          note: d.note,
          refId: d.refId,
          prevHash: prev,
          hash: hash,
        );
      });

  @override
  Future<List<JournalEntry>> forAgreement(String agreementId) async => [
    for (final r
        in await (_db.select(_db.journalEntries)
              ..where((t) => t.agreementId.equals(agreementId))
              ..orderBy([(t) => OrderingTerm.asc(t.seq)]))
            .get())
      _fromRow(r),
  ];
}
