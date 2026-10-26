package uz.sectorverify.format

import java.security.MessageDigest
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Canonical form (§8.3): object keys sorted recursively, no whitespace, number literals kept verbatim.
 * Re-parsing a pretty-printed document yields the same canonical bytes.
 */
object CanonicalJson {
    fun canonicalize(e: JsonElement): JsonElement = when (e) {
        is JsonObject -> JsonObject(e.entries.sortedBy { it.key }.associateTo(LinkedHashMap()) { it.key to canonicalize(it.value) })
        is JsonArray -> JsonArray(e.map(::canonicalize))
        is JsonPrimitive -> e
    }

    fun bytes(e: JsonElement): ByteArray = canonicalize(e).toString().toByteArray(Charsets.UTF_8)

    fun sha256Hex(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
}
