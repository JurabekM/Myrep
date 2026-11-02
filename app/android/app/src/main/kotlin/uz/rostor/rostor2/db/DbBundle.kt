package uz.rostor.rostor2.db

import org.json.JSONObject
import uz.rostor.rostor2.crypto.Hybrid
import uz.rostor.rostor2.crypto.toHex
import java.util.Base64

/**
 * Imzolangan offlayn baza (Q5). Fayl tuzilmasi `tools/rostor_db/build_db.py` da yaratiladi:
 *
 *   { "format": "ROSTOR-2/db-bundle/v1", "manifest": b64, "sig": b64, "payload": b64 }
 *
 * manifest — kanonik JSON: {v, db_version, issued_at, payload_len, payload_sha3_256, key_id}.
 * Imzolanadigan xabar: "ROSTOR-2/db-manifest" || manifest baytlari (ROSTOR-1 domen ajratish naqshi).
 */
object DbBundle {
    const val FORMAT = "ROSTOR-2/db-bundle/v1"
    val DOMAIN = "ROSTOR-2/db-manifest".toByteArray(Charsets.US_ASCII)

    data class Result(
        val ok: Boolean,
        val error: String? = null,
        val dbVersion: Long = 0,
        val issuedAt: Long = 0,
        val keyId: String = "",
        val payloadJson: String? = null,
    )

    fun keyId(edPk: ByteArray, mldsaPk: ByteArray): String = Hybrid.sha3_256(edPk, mldsaPk).toHex().substring(0, 16)

    /** Sof funksiya: Android'ga bog'liq emas, JVM unit testida ham ishlaydi. */
    fun verify(bundleJson: String, edPk: ByteArray, mldsaPk: ByteArray, minVersion: Long): Result {
        val b64 = Base64.getDecoder()
        val obj = try { JSONObject(bundleJson) } catch (e: Exception) { return Result(false, "baza fayli JSON emas") }
        if (obj.optString("format") != FORMAT) return Result(false, "noma'lum baza formati")
        val manifestBytes: ByteArray
        val sig: ByteArray
        val payload: ByteArray
        try {
            manifestBytes = b64.decode(obj.getString("manifest"))
            sig = b64.decode(obj.getString("sig"))
            payload = b64.decode(obj.getString("payload"))
        } catch (e: Exception) {
            return Result(false, "baza maydonlari buzilgan")
        }
        if (!Hybrid.verify(edPk, mldsaPk, sig, DOMAIN + manifestBytes)) {
            return Result(false, "baza imzosi haqiqiy emas")
        }
        // Imzo tekshirilgandan keyingina manifest mazmuniga ishoniladi.
        val m = JSONObject(String(manifestBytes, Charsets.UTF_8))
        if (m.optInt("v") != 1) return Result(false, "manifest versiyasi qo'llab-quvvatlanmaydi")
        val expectedKeyId = keyId(edPk, mldsaPk)
        if (m.optString("key_id") != expectedKeyId) return Result(false, "kalit identifikatori mos emas")
        if (m.optLong("payload_len", -1) != payload.size.toLong()) return Result(false, "baza uzunligi mos emas")
        if (m.optString("payload_sha3_256") != Hybrid.sha3_256(payload).toHex()) {
            return Result(false, "baza xeshi mos emas")
        }
        val version = m.optLong("db_version", -1)
        if (version < 0) return Result(false, "baza versiyasi yo'q")
        if (version < minVersion) {
            return Result(false, "baza versiyasi pasaytirilgan ($version < $minVersion)")
        }
        return Result(
            ok = true,
            dbVersion = version,
            issuedAt = m.optLong("issued_at"),
            keyId = expectedKeyId,
            payloadJson = String(payload, Charsets.UTF_8),
        )
    }
}
