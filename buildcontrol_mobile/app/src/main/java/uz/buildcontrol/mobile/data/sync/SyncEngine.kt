package uz.buildcontrol.mobile.data.sync

import android.util.Log
import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.OutboxRow
import uz.buildcontrol.mobile.data.db.SyncStateRow
import uz.buildcontrol.mobile.data.db.newUid

/**
 * Offline-first replication, protocol-compatible with the desktop application.
 *
 * Local edits queue in `sync_outbox`; [synchronize] pushes them to the shared
 * append-only log and applies everything newer than this device's cursor.
 * Conflicts resolve last-write-wins on `sync_ts`; rows two devices created
 * independently merge on the entity's natural key.
 */
class SyncEngine(private val db: BcDatabase) {

    data class Report(
        var pushed: Int = 0,
        var pulled: Int = 0,
        var applied: Int = 0,
        var skippedOlder: Int = 0,
        var skippedOwn: Int = 0,
        var failed: Int = 0,
        val errors: MutableList<String> = mutableListOf(),
    ) {
        val ok: Boolean get() = errors.isEmpty()
        fun summary(): String = "↑$pushed ↓$pulled ✓$applied ↺$skippedOlder ✕$failed"
    }

    private val syncDao = db.syncDao()

    suspend fun state(): SyncStateRow = withContext(Dispatchers.IO) { ensureState() }

    private suspend fun ensureState(): SyncStateRow {
        val existing = syncDao.state()
        if (existing != null) return existing
        val fresh = SyncStateRow(id = 1, deviceId = newUid().take(16))
        syncDao.upsertState(fresh)
        return fresh
    }

    suspend fun setDeviceName(name: String) = withContext(Dispatchers.IO) {
        syncDao.upsertState(ensureState().copy(deviceName = name.take(96)))
    }

    suspend fun resetCursor() = withContext(Dispatchers.IO) {
        syncDao.upsertState(ensureState().copy(cursor = ""))
    }

    /** Queue every local row so a fresh server receives this device's data. */
    suspend fun queueFullUpload(): Int = withContext(Dispatchers.IO) {
        var queued = 0
        db.withTransaction {
            syncDao.clearAllOutbox()
            val raw = db.openHelper.writableDatabase
            for (spec in SYNC_TABLES) {
                raw.query("SELECT uid FROM ${spec.table}").use { cursor ->
                    while (cursor.moveToNext()) {
                        val uid = cursor.getString(0) ?: continue
                        val payload = SyncCodec.serialise(raw, spec, uid) ?: continue
                        syncDao.addOutbox(
                            OutboxRow(
                                entity = spec.entity,
                                uid = uid,
                                op = Change.OP_UPSERT,
                                payload = SyncJson.encodeToString(JsonObject.serializer(), payload),
                            )
                        )
                        queued++
                    }
                }
            }
        }
        queued
    }

    // -- main round ---------------------------------------------------------- //
    suspend fun synchronize(transport: SyncTransport): Report = withContext(Dispatchers.IO) {
        val report = Report()
        try {
            push(transport, report)
            pull(transport, report)
        } catch (exc: TransportException) {
            report.errors.add(exc.message ?: "transport error")
        } catch (exc: Exception) {
            report.errors.add(exc.message ?: exc.javaClass.simpleName)
            Log.e(TAG, "sync round failed", exc)
        }
        syncDao.upsertState(ensureState().copy(lastError = report.errors.take(2).joinToString("; ")))
        db.invalidationTracker.refreshVersionsAsync()
        report
    }

    private suspend fun push(transport: SyncTransport, report: Report) {
        while (true) {
            val rows = syncDao.outboxBatch(PUSH_CHUNK)
            if (rows.isEmpty()) return
            val device = ensureState().deviceId
            val changes = rows.map { row ->
                Change(
                    entity = row.entity,
                    uid = row.uid,
                    op = row.op,
                    payload = if (row.payload.isBlank()) emptyPayload()
                    else SyncCodec.jsonToObject(row.payload),
                    ts = SyncCodec.millisToIso(row.ts),
                    device = device,
                )
            }
            val sent = transport.push(changes)
            syncDao.clearOutbox(rows.map { it.id })
            val state = ensureState()
            syncDao.upsertState(
                state.copy(pushedTotal = state.pushedTotal + sent, lastPushAt = System.currentTimeMillis())
            )
            report.pushed += sent
            if (rows.size < PUSH_CHUNK) return
        }
    }

    private suspend fun pull(transport: SyncTransport, report: Report) {
        repeat(MAX_BATCHES) {
            val cursor = ensureState().cursor
            val batch = transport.pull(cursor, PULL_LIMIT)
            if (batch.isEmpty()) return
            report.pulled += batch.size
            applyBatch(batch, report)
            if (batch.size < PULL_LIMIT) return
        }
    }

    private suspend fun applyBatch(batch: List<Change>, report: Report) {
        db.withTransaction {
            val raw = db.openHelper.writableDatabase
            val own = ensureState().deviceId
            var cursor = ensureState().cursor
            val deferred = mutableListOf<Change>()

            for (change in batch.sortedBy { it.cursor.toLongOrNull() ?: 0L }) {
                if (change.device.isNotEmpty() && change.device == own) {
                    report.skippedOwn++
                    if (change.cursor.isNotEmpty()) cursor = change.cursor
                    continue
                }
                if (applyOne(raw, change, report) == Outcome.DEFER) deferred.add(change)
                if (change.cursor.isNotEmpty()) cursor = change.cursor
            }

            var pending = deferred
            repeat(3) {
                if (pending.isEmpty()) return@repeat
                val retry = pending.sortedWith(
                    compareBy({ ENTITY_ORDER[it.entity] ?: 99 }, { it.cursor.toLongOrNull() ?: 0L })
                )
                val next = mutableListOf<Change>()
                for (change in retry) {
                    if (applyOne(raw, change, report) == Outcome.DEFER) next.add(change)
                }
                pending = next
            }
            for (change in pending) {
                report.failed++
                report.errors.add("${change.entity}/${change.uid}: bog'liq yozuv topilmadi")
            }

            val state = ensureState()
            syncDao.upsertState(
                state.copy(
                    cursor = cursor,
                    lastPullAt = System.currentTimeMillis(),
                    pulledTotal = state.pulledTotal + batch.size,
                )
            )
        }
    }

    private enum class Outcome { OK, SKIP, DEFER, FAIL }

    private fun applyOne(
        raw: androidx.sqlite.db.SupportSQLiteDatabase,
        change: Change,
        report: Report,
    ): Outcome {
        val spec = SPEC_BY_ENTITY[change.entity] ?: return Outcome.SKIP
        return try {
            if (change.op == Change.OP_DELETE) {
                val removed = raw.delete(spec.table, "uid = ?", arrayOf<Any>(change.uid))
                if (removed > 0) report.applied++
                return Outcome.OK
            }
            val values = SyncCodec.toContentValues(raw, spec, change.payload)
            val incomingTs = SyncCodec.payloadSyncTs(change.payload)
            val rowId = SyncCodec.findRowId(raw, spec, change.uid, values)

            if (rowId == null) {
                values.put("uid", change.uid)
                raw.insert(spec.table, android.database.sqlite.SQLiteDatabase.CONFLICT_ABORT, values)
                report.applied++
                return Outcome.OK
            }

            // Merged on a natural key: keep our uid and remember theirs so the
            // other device's foreign keys keep resolving here.
            val localUid = SyncCodec.uidOfRow(raw, spec, rowId)
            if (localUid != null && localUid != change.uid) {
                SyncCodec.recordAlias(raw, spec.entity, change.uid, localUid)
            }

            val localTs = SyncCodec.localSyncTs(raw, spec, localUid ?: change.uid)
            if (localTs != null && incomingTs <= localTs) {
                report.skippedOlder++
                return Outcome.SKIP
            }
            values.remove("uid")
            raw.update(
                spec.table,
                android.database.sqlite.SQLiteDatabase.CONFLICT_ABORT,
                values,
                "id = ?",
                arrayOf<Any>(rowId),
            )
            report.applied++
            Outcome.OK
        } catch (_: SyncCodec.UnresolvedReference) {
            Outcome.DEFER
        } catch (exc: Exception) {
            report.failed++
            report.errors.add("${change.entity}/${change.uid}: ${exc.message?.take(120)}")
            Outcome.FAIL
        }
    }

    companion object {
        private const val TAG = "SyncEngine"
        private const val PUSH_CHUNK = 200
        private const val PULL_LIMIT = 500
        private const val MAX_BATCHES = 40
    }
}
