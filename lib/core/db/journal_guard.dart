import 'package:drift/drift.dart';

/// Jurnal (`journal_entries`) append-only himoyasi (SPEC 2F.6): `UPDATE` va
/// `DELETE` DB darajasida `RAISE(ABORT)`. Yagona istisno — zaxiradan to'liq
/// tiklash ([withJournalUnlocked]), u ham bitta tranzaksiya ichida.
///
/// `journal_guard` — drift jadvali emas (zaxira nusxaga kirmaydi).
const journalAppendOnlyError = 'journal_append_only';

Future<void> ensureJournalGuard(DatabaseConnectionUser db) async {
  await db.customStatement(
    'CREATE TABLE IF NOT EXISTS journal_guard (allow INTEGER NOT NULL)',
  );
  await db.customStatement(
    'INSERT INTO journal_guard (allow) '
    'SELECT 0 WHERE NOT EXISTS (SELECT 1 FROM journal_guard)',
  );
  for (final op in ['UPDATE', 'DELETE']) {
    await db.customStatement(
      'CREATE TRIGGER IF NOT EXISTS journal_entries_no_${op.toLowerCase()} '
      'BEFORE $op ON journal_entries '
      'WHEN (SELECT allow FROM journal_guard LIMIT 1) = 0 '
      "BEGIN SELECT RAISE(ABORT, '$journalAppendOnlyError'); END",
    );
  }
}

/// [action] davomida jurnalni o'zgartirishga ruxsat (faqat zaxiradan
/// tiklash uchun). Chaqiruvchi tranzaksiya ichida bo'lishi kerak — xato
/// bo'lsa ruxsat ham orqaga qaytadi.
Future<T> withJournalUnlocked<T>(
  DatabaseConnectionUser db,
  Future<T> Function() action,
) async {
  await db.customStatement('UPDATE journal_guard SET allow = 1');
  try {
    return await action();
  } finally {
    await db.customStatement('UPDATE journal_guard SET allow = 0');
  }
}
