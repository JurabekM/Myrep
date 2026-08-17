package uz.buildcontrol.mobile.data.sync

import android.content.ContentValues
import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeParseException

/**
 * Converts rows to and from the wire format used by the desktop application.
 *
 * Timestamps travel as `{"__dt__": "<iso>"}` and dates as `{"__d__": "<iso>"}`,
 * exactly as Python's `registry._encode` emits them. Foreign keys travel as the
 * target row's uid so local integer ids never leave the device.
 */
object SyncCodec {

    class UnresolvedReference(message: String) : Exception(message)

    // -- timestamps --------------------------------------------------------- //
    fun millisToIso(millis: Long): String =
        LocalDateTime.ofInstant(Instant.ofEpochMilli(millis), ZoneId.systemDefault()).toString()

    fun isoToMillis(text: String): Long? = try {
        val cleaned = text.trim().removeSuffix("Z")
        val local = if (cleaned.contains('T')) {
            LocalDateTime.parse(cleaned)
        } else {
            LocalDateTime.parse(cleaned.replace(' ', 'T'))
        }
        local.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
    } catch (_: DateTimeParseException) {
        null
    }

    private fun encodeDateTime(millis: Long): JsonElement =
        JsonObject(mapOf("__dt__" to JsonPrimitive(millisToIso(millis))))

    private fun encodeDate(iso: String): JsonElement =
        JsonObject(mapOf("__d__" to JsonPrimitive(iso)))

    private fun decodeDateTime(element: JsonElement): Long? {
        val obj = element as? JsonObject ?: return null
        val raw = obj["__dt__"]?.jsonPrimitive?.contentOrNull ?: return null
        return isoToMillis(raw)
    }

    private fun decodeDate(element: JsonElement): String? {
        val obj = element as? JsonObject ?: return null
        val raw = obj["__d__"]?.jsonPrimitive?.contentOrNull ?: return null
        // Tolerate a full timestamp where a plain date is expected.
        return raw.substringBefore('T').substringBefore(' ')
    }

    // -- reading ------------------------------------------------------------ //
    /** Serialise the row identified by [uid] into a transport payload. */
    fun serialise(db: SupportSQLiteDatabase, spec: TableSpec, uid: String): JsonObject? {
        val columns = spec.cols.joinToString(", ") { it.name }
        db.query("SELECT id, $columns FROM ${spec.table} WHERE uid = ? LIMIT 1", arrayOf(uid))
            .use { cursor ->
                if (!cursor.moveToFirst()) return null
                val payload = LinkedHashMap<String, JsonElement>()
                for (col in spec.cols) {
                    val index = cursor.getColumnIndexOrThrow(col.name)
                    if (cursor.isNull(index)) {
                        payload[col.name] = JsonNull
                        continue
                    }
                    payload[col.name] = when {
                        col.fk != null -> {
                            val target = SPEC_BY_TABLE[col.fk]
                            val localId = cursor.getLong(index)
                            val refUid = target?.let { uidOf(db, it.table, localId) }
                            if (refUid == null) JsonNull else JsonPrimitive(refUid)
                        }
                        col.kind == ColKind.BOOL -> JsonPrimitive(cursor.getInt(index) != 0)
                        col.kind == ColKind.INT -> JsonPrimitive(cursor.getLong(index))
                        col.kind == ColKind.REAL -> JsonPrimitive(cursor.getDouble(index))
                        col.kind == ColKind.DATETIME -> encodeDateTime(cursor.getLong(index))
                        col.kind == ColKind.DATE -> encodeDate(cursor.getString(index))
                        else -> JsonPrimitive(cursor.getString(index))
                    }
                }
                return JsonObject(payload)
            }
    }

    private fun uidOf(db: SupportSQLiteDatabase, table: String, id: Long): String? =
        db.query("SELECT uid FROM $table WHERE id = ? LIMIT 1", arrayOf<Any>(id)).use {
            if (it.moveToFirst()) it.getString(0) else null
        }

    private fun localIdOf(db: SupportSQLiteDatabase, table: String, uid: String): Long? =
        db.query("SELECT id FROM $table WHERE uid = ? LIMIT 1", arrayOf<Any>(uid)).use {
            if (it.moveToFirst()) it.getLong(0) else null
        }

    /** Local uid registered for a foreign one, or `null`. */
    fun aliasOf(db: SupportSQLiteDatabase, entity: String, foreignUid: String): String? =
        db.query(
            "SELECT local_uid FROM sync_uid_alias WHERE entity = ? AND foreign_uid = ? LIMIT 1",
            arrayOf<Any>(entity, foreignUid),
        ).use { if (it.moveToFirst()) it.getString(0) else null }

    /** Remember that [foreignUid] denotes the same row as [localUid] here. */
    fun recordAlias(
        db: SupportSQLiteDatabase,
        entity: String,
        foreignUid: String,
        localUid: String,
    ) {
        val values = ContentValues().apply {
            put("entity", entity)
            put("foreign_uid", foreignUid)
            put("local_uid", localUid)
            put("created_at", System.currentTimeMillis())
        }
        db.insert(
            "sync_uid_alias",
            android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE,
            values,
        )
    }

    // -- writing ------------------------------------------------------------ //
    /**
     * Convert a payload into column values for this device.
     *
     * @throws UnresolvedReference when a referenced row has not arrived yet.
     */
    fun toContentValues(
        db: SupportSQLiteDatabase,
        spec: TableSpec,
        payload: JsonObject,
    ): ContentValues {
        val values = ContentValues()
        for ((name, element) in payload) {
            val col = spec.byName[name] ?: continue
            if (element is JsonNull) {
                values.putNull(name)
                continue
            }
            if (col.fk != null) {
                val refUid = element.jsonPrimitive.contentOrNull
                if (refUid.isNullOrEmpty()) {
                    values.putNull(name)
                } else {
                    val target = SPEC_BY_TABLE[col.fk]
                        ?: throw UnresolvedReference("unknown table ${col.fk}")
                    val localId = localIdOf(db, target.table, refUid)
                        ?: aliasOf(db, target.entity, refUid)
                            ?.let { localIdOf(db, target.table, it) }
                        ?: throw UnresolvedReference("${target.table}.uid=$refUid ($name)")
                    values.put(name, localId)
                }
                continue
            }
            when (col.kind) {
                ColKind.BOOL -> values.put(name, if (element.jsonPrimitive.booleanish()) 1 else 0)
                ColKind.INT -> values.put(name, element.jsonPrimitive.longOrNull ?: 0L)
                ColKind.REAL -> values.put(name, element.jsonPrimitive.doubleOrNull ?: 0.0)
                ColKind.DATETIME -> decodeDateTime(element)?.let { values.put(name, it) }
                    ?: values.putNull(name)
                ColKind.DATE -> decodeDate(element)?.let { values.put(name, it) }
                    ?: values.putNull(name)
                ColKind.TEXT -> values.put(name, element.jsonPrimitive.contentOrNull)
            }
        }
        return values
    }

    private fun JsonPrimitive.booleanish(): Boolean =
        booleanOrNullCompat() ?: ((longOrNull ?: 0L) != 0L)

    private fun JsonPrimitive.booleanOrNullCompat(): Boolean? = booleanOrNull

    /** Timestamp a payload carries, used for last-write-wins. */
    fun payloadSyncTs(payload: JsonObject): Long =
        payload["sync_ts"]?.let { decodeDateTime(it) } ?: 0L

    /** The uid stored on the row with this local id. */
    fun uidOfRow(db: SupportSQLiteDatabase, spec: TableSpec, rowId: Long): String? =
        db.query("SELECT uid FROM ${spec.table} WHERE id = ? LIMIT 1", arrayOf<Any>(rowId))
            .use { if (it.moveToFirst()) it.getString(0) else null }

    /** Local `sync_ts` of the row with this uid, or `null` when absent. */
    fun localSyncTs(db: SupportSQLiteDatabase, spec: TableSpec, uid: String): Long? =
        db.query("SELECT sync_ts FROM ${spec.table} WHERE uid = ? LIMIT 1", arrayOf<Any>(uid))
            .use { if (it.moveToFirst()) it.getLong(0) else null }

    /** Find an existing row by uid, then by the entity's natural key. */
    fun findRowId(
        db: SupportSQLiteDatabase,
        spec: TableSpec,
        uid: String,
        values: ContentValues,
    ): Long? {
        localIdOf(db, spec.table, uid)?.let { return it }
        aliasOf(db, spec.entity, uid)?.let { alias ->
            localIdOf(db, spec.table, alias)?.let { return it }
        }
        if (spec.singleton) {
            return db.query("SELECT id FROM ${spec.table} LIMIT 1").use {
                if (it.moveToFirst()) it.getLong(0) else null
            }
        }
        if (spec.naturalKeys.isEmpty()) return null
        val args = ArrayList<Any>()
        val clauses = ArrayList<String>()
        for (key in spec.naturalKeys) {
            val value = values.get(key) ?: return null
            args.add(value)
            clauses.add("$key = ?")
        }
        val where = clauses.joinToString(" AND ")
        return db.query("SELECT id FROM ${spec.table} WHERE $where LIMIT 1", args.toTypedArray())
            .use { if (it.moveToFirst()) it.getLong(0) else null }
    }

    fun jsonToObject(text: String): JsonObject = SyncJson.parseToJsonElement(text).jsonObject
}
