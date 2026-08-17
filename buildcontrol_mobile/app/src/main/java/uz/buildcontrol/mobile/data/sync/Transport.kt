package uz.buildcontrol.mobile.data.sync

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

val SyncJson = Json {
    ignoreUnknownKeys = true
    encodeDefaults = true
    explicitNulls = true
}

/** One replicated row operation travelling through the shared log. */
data class Change(
    val entity: String,
    val uid: String,
    val op: String,
    val payload: JsonObject,
    val ts: String,
    val device: String,
    val cursor: String = "",
) {
    fun toWire(tenant: String): JsonObject = buildJsonObject {
        put("tenant", JsonPrimitive(tenant))
        put("device", JsonPrimitive(device))
        put("entity", JsonPrimitive(entity))
        put("uid", JsonPrimitive(uid))
        put("op", JsonPrimitive(op))
        put("payload", payload)
        put("ts", JsonPrimitive(ts))
    }

    companion object {
        const val OP_UPSERT = "upsert"
        const val OP_DELETE = "delete"

        fun fromWire(row: JsonObject, cursor: String): Change {
            val rawPayload = row["payload"]
            val payload = when {
                rawPayload is JsonObject -> rawPayload
                rawPayload != null && rawPayload !is kotlinx.serialization.json.JsonNull ->
                    runCatching {
                        SyncJson.parseToJsonElement(rawPayload.jsonPrimitive.content).jsonObject
                    }.getOrElse { JsonObject(emptyMap()) }
                else -> JsonObject(emptyMap())
            }
            return Change(
                entity = row["entity"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                uid = row["uid"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                op = row["op"]?.jsonPrimitive?.contentOrNull ?: OP_UPSERT,
                payload = payload,
                ts = row["ts"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                device = row["device"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                cursor = cursor,
            )
        }
    }
}

class TransportException(message: String, cause: Throwable? = null) : Exception(message, cause)

/** Append-only log a replication backend must provide. */
interface SyncTransport {
    val key: String
    fun describe(): String

    /** Verify connectivity; returns a status line or throws [TransportException]. */
    fun check(): String

    fun push(changes: List<Change>): Int

    /** Changes newer than [after], oldest first. */
    fun pull(after: String, limit: Int = 500): List<Change>
}
