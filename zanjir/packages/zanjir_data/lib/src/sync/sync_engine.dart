import 'package:drift/drift.dart';

import '../db/database.dart';
import '../repo/settings_repository.dart';
import 'transport.dart';
import 'wire.dart';

/// Sinxronlash natijasi.
class SyncReport {
  const SyncReport({required this.pushed, required this.duplicates, required this.stale, required this.pulled});
  final int pushed;
  final int duplicates;
  final int stale;
  final int pulled;

  @override
  String toString() => 'SyncReport(pushed: $pushed, duplicates: $duplicates, stale: $stale, pulled: $pulled)';
}

/// Offline-first sinxronlash (ADR-0012): avval navbatdagi o'zgarishlar push qilinadi, keyin serverdan pull.
///
/// - Navbat (`sync_outbox`) SQLite triggerlari bilan to'ladi; har bir yozuv `op_id` bilan — qayta yuborish xavfsiz
///   (server takrorni o'tkazib yuboradi), javob yo'qolsa ham hech narsa ikki marta yozilmaydi.
/// - Paket tartibi: audit hodisalari (seq bo'yicha) birinchi, keyin jadvallar ota-bola tartibida; protokol o'z hujjati
///   bilan bir paketda. Paket rad etilsa — navbat saqlanadi, pull bajariladi, xato ([SyncRejected]) yuqoriga uzatiladi.
/// - Pull: `server_rev` kursori; metadata — last-writer-wins (`updated_at`, keyin `rev`), append-only — faqat qo'shiladi.
///   Serverdan kelgan o'zgarish navbatga tushmaydi (`sync.applying` belgisi).
class SyncEngine {
  SyncEngine(this.db, this.transport, {this.maxOps = 500});
  final ZanjirDatabase db;
  final SyncTransport transport;
  final int maxOps;

  static const cursorKey = 'sync.cursor';
  static const applyingKey = 'sync.applying';
  static const lastSyncKey = 'sync.last_at';

  late final _prefs = LocalPrefRepository(db);

  Future<int> pendingCount() async =>
      (await db.customSelect('SELECT count(*) AS n FROM sync_outbox').getSingle()).read<int>('n');

  /// Push, keyin pull. Paket rad etilsa ([SyncRejected]) — pull baribir bajariladi, so'ng xato uzatiladi: bitta qotgan
  /// yozuv qurilmani boshqalarning o'zgarishlaridan uzib qo'ymaydi (ADR-0014). Tarmoq xatosi — darhol uzatiladi.
  Future<SyncReport> run({DateTime? now}) async {
    var pushed = 0, duplicates = 0, stale = 0;
    SyncRejected? rejected;
    try {
      (pushed, duplicates, stale) = await _push();
    } on ServerException catch (e) {
      if (e.code != 'push_rejected') rethrow;
      rejected = await _describe(e);
    }
    final pulled = await pull();
    if (rejected != null) throw rejected;
    await _prefs.set(lastSyncKey, (now ?? DateTime.now()).toUtc().toIso8601String());
    return SyncReport(pushed: pushed, duplicates: duplicates, stale: stale, pulled: pulled);
  }

  Future<SyncRejected> _describe(ServerException e) async {
    final op = e.opId == null
        ? null
        : await (db.select(db.syncOutbox)..where((o) => o.opId.equals(e.opId!))).getSingleOrNull();
    return SyncRejected(e, table: op?.tableName_, rowId: op?.rowId);
  }

  Future<(int, int, int)> _push() async {
    var pushed = 0, duplicates = 0, stale = 0;
    for (final batch in await _batches()) {
      final statuses = await transport.push([for (final e in batch) e.op]);
      for (final s in statuses.values) {
        switch (s) {
          case 'duplicate':
            duplicates++;
          case 'stale':
            stale++;
          default:
            pushed++;
        }
      }
      await db.batch((b) {
        for (final e in batch) {
          b.deleteWhere(db.syncOutbox, (o) => o.id.equals(e.outboxId) & o.opId.equals(e.opId));
        }
      });
    }
    return (pushed, duplicates, stale);
  }

  /// Serverdagi o'zgarishlarni oladi va qo'llaydi; qo'llangan qatorlar soni.
  ///
  /// Barcha sahifalar bitta tranzaksiyada (FK tekshiruvi oxirida): ota yozuv keyinroq o'zgargan bo'lsa, uning
  /// `server_rev` i bolalaridan katta — sahifalar alohida commit qilinsa, lokal FK buziladi. Xato bo'lsa — hech narsa
  /// qo'llanmaydi, kursor joyida qoladi.
  Future<int> pull() => db.transaction(() async {
    await db.customStatement('PRAGMA defer_foreign_keys = ON');
    await _prefs.set(applyingKey, '1');
    var applied = 0;
    var since = int.tryParse(await _prefs.get(cursorKey) ?? '') ?? 0;
    while (true) {
      final page = await transport.pull(since);
      for (final c in page.changes) {
        if (await _apply(c)) applied++;
      }
      since = page.serverRev;
      if (!page.hasMore) break;
    }
    await _prefs.remove(applyingKey);
    await _prefs.set(cursorKey, '$since');
    return applied;
  });

  Future<bool> _apply(PullChange c) async {
    if (!syncTables.contains(c.table)) return false;
    final columns = wireColumns(db, c.table);
    final id = c.row['id']! as String;
    final existing = await db
        .customSelect('SELECT * FROM ${c.table} WHERE id = ?', variables: [Variable<String>(id)])
        .getSingleOrNull();
    if (existing != null) {
      if (appendOnlyTables.contains(c.table)) return false;
      final local = (localDate(existing.data['updated_at']), existing.data['rev'] as int);
      final incoming = (wireDate(c.row['updated_at']), (c.row['rev'] as num?)?.toInt() ?? 0);
      if (!_newer(incoming, local)) return false;
      final names = [
        for (final n in columns.keys)
          if (n != 'id' && c.row.containsKey(n)) n,
      ];
      await db.customStatement('UPDATE ${c.table} SET ${names.map((n) => '"$n" = ?').join(', ')} WHERE id = ?', [
        for (final n in names) wireToVariable(columns[n]!, c.row[n]).value,
        id,
      ]);
      // Server versiyasi yutdi — mahalliy (eskiroq) o'zgarish yuborilmaydi.
      await (db.delete(db.syncOutbox)..where((o) => o.tableName_.equals(c.table) & o.rowId.equals(id))).go();
      return true;
    }
    final names = [
      for (final n in columns.keys)
        if (c.row.containsKey(n)) n,
    ];
    final defaults = localOnlyDefaults[c.table] ?? const <String, Object>{};
    await db.customStatement(
      'INSERT INTO ${c.table} (${[...names, ...defaults.keys].map((n) => '"$n"').join(', ')}) '
      'VALUES (${List.filled(names.length + defaults.length, '?').join(', ')})',
      [for (final n in names) wireToVariable(columns[n]!, c.row[n]).value, ...defaults.values],
    );
    return true;
  }

  static bool _newer((DateTime?, int) a, (DateTime?, int) b) {
    final (at, ar) = a;
    final (bt, br) = b;
    if (at == null) return false;
    if (bt == null) return true;
    final cmp = at.compareTo(bt);
    return cmp > 0 || (cmp == 0 && ar > br);
  }

  /// Navbat → paketlar (≤ [maxOps]).
  Future<List<List<_Entry>>> _batches() async {
    final rows = await (db.select(db.syncOutbox)..orderBy([(o) => OrderingTerm(expression: o.id)])).get();
    final entries = <_Entry>[];
    for (final r in rows) {
      if (apiOnlyTables.contains(r.tableName_)) continue;
      final raw = await db
          .customSelect('SELECT * FROM ${r.tableName_} WHERE id = ?', variables: [Variable<String>(r.rowId)])
          .getSingleOrNull();
      if (raw == null) {
        await (db.delete(db.syncOutbox)..where((o) => o.id.equals(r.id))).go();
        continue;
      }
      entries.add(
        _Entry(r.id, r.opId, {
          'client_op_id': r.opId,
          'table': r.tableName_,
          'row': rowToWire(wireColumns(db, r.tableName_), raw.data),
        }),
      );
    }
    int rank(_Entry e) => e.table == 'audit_event' ? -1 : syncTables.indexOf(e.table);
    entries.sort((a, b) {
      final r = rank(a).compareTo(rank(b));
      return r != 0 ? r : a.outboxId.compareTo(b.outboxId);
    });
    // Protokol hujjati protokol bilan bir paketda bo'lishi shart (server talabi).
    final units = <List<_Entry>>[];
    final docs = {
      for (final e in entries)
        if (e.table == 'protocol_document') e.row['protocol_id']: e,
    };
    for (final e in entries) {
      if (e.table == 'protocol_document' &&
          entries.any((p) => p.table == 'protocol' && p.row['id'] == e.row['protocol_id'])) {
        continue;
      }
      final doc = e.table == 'protocol' ? docs[e.row['id']] : null;
      units.add([e, ?doc]);
    }
    final batches = <List<_Entry>>[];
    var current = <_Entry>[];
    for (final u in units) {
      if (current.isNotEmpty && current.length + u.length > maxOps) {
        batches.add(current);
        current = [];
      }
      current.addAll(u);
    }
    if (current.isNotEmpty) batches.add(current);
    return batches;
  }
}

class _Entry {
  _Entry(this.outboxId, this.opId, this.op);
  final int outboxId;
  final String opId;
  final Map<String, Object?> op;
  String get table => op['table']! as String;
  Map<String, Object?> get row => op['row']! as Map<String, Object?>;
}
