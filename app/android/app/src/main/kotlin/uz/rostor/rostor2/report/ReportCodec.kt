package uz.rostor.rostor2.report

import org.json.JSONArray
import org.json.JSONObject
import uz.rostor.rostor2.call.PhoneNumbers
import uz.rostor.rostor2.crypto.Hybrid
import uz.rostor.rostor2.crypto.toHex
import java.net.URI
import java.text.SimpleDateFormat
import java.util.Base64
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * F3: imzolangan firibgarlik hisoboti. Sof JVM kodi (unit testda ishlaydi).
 *
 *   { "format": "ROSTOR-2/fraud-report/v1", "content": b64, "sig": b64,
 *     "ed25519_pk": b64, "mldsa65_pk": b64, "device_id": hex32, "readable": matn }
 *
 * Imzolanadi: "ROSTOR-2/fraud-report" || content baytlari. content baytlari faylga o'zgarishsiz
 * joylanadi, shuning uchun tekshiruvchi JSON'ni qayta kanonlashtirmaydi (DbBundle bilan bir xil naqsh).
 * `readable` — odam uchun nusxa, imzolanmaydi; haqiqiy matn faqat `content` da.
 * `target_value_hash` ROSTOR-1 `fraud_report.target_hash` bilan bir xil: sha3("ROSTOR-1/report-target" || type || value).
 */
object ReportCodec {
    const val FORMAT = "ROSTOR-2/fraud-report/v1"
    val DOMAIN = "ROSTOR-2/fraud-report".toByteArray(Charsets.US_ASCII)
    private val TARGET_DOMAIN = "ROSTOR-1/report-target".toByteArray(Charsets.US_ASCII)

    val CATEGORIES = linkedMapOf(
        "T1" to "Messenjerda kelgan zararli APK",
        "T2" to "\"Bank xavfsizlik xizmati\" qo'ng'irog'i",
        "T3" to "Davlat idorasi nomidan qo'rqitish",
        "T4" to "SIM-kartani almashtirish",
        "T5" to "OLX va bozordagi soxta xaridor",
        "T6" to "Oson daromad va investitsiya",
        "T7" to "Telegram akkauntini egallash",
        "other" to "Boshqa firibgarlik",
    )
    val TARGET_TYPES = linkedMapOf(
        "phone" to "Telefon raqami",
        "link" to "Havola yoki sayt",
        "apk" to "APK fayl (SHA-256)",
        "card" to "Firibgarning kartasi",
        "telegram" to "Telegram akkaunt",
        "other" to "Boshqa",
    )
    const val MAX_TEXT = 4000
    const val MAX_EVIDENCE = 5

    class InvalidInput(msg: String) : Exception(msg)

    fun deviceId(edPk: ByteArray, mlPk: ByteArray): String = Hybrid.sha3_256(edPk, mlPk).toHex().substring(0, 32)

    fun targetHash(type: String, normalized: String): String =
        Hybrid.sha3_256(TARGET_DOMAIN, type.toByteArray(Charsets.UTF_8), normalized.toByteArray(Charsets.UTF_8)).toHex()

    /** Imzolanadigan qiymat kanonik ko'rinishda bo'lishi shart — aks holda bir xil firibgar turli xesh oladi. */
    fun normalizeTarget(type: String, raw: String): String {
        val v = raw.trim()
        if (v.isEmpty()) throw InvalidInput("Firibgar ma'lumotini kiriting")
        return when (type) {
            "phone" -> PhoneNumbers.normalize(v) ?: throw InvalidInput("Telefon raqami noto'g'ri")
            "link" -> {
                val withScheme = if ("://" in v) v else "http://$v"
                val host = try { URI(withScheme.replace(" ", "")).host } catch (e: Exception) { null }
                host?.lowercase()?.trimEnd('.')?.removePrefix("www.")?.takeIf { '.' in it }
                    ?: throw InvalidInput("Havola yoki domen noto'g'ri")
            }
            "apk" -> v.lowercase().takeIf { Regex("[0-9a-f]{64}").matches(it) }
                ?: throw InvalidInput("APK SHA-256 izi 64 ta hex belgidan iborat bo'lishi kerak")
            "card" -> v.filter { it.isDigit() }.takeIf { it.length in 16..19 }
                ?: throw InvalidInput("Karta raqami 16–19 raqamdan iborat bo'lishi kerak")
            "telegram" -> v.removePrefix("https://").removePrefix("t.me/").removePrefix("@").lowercase()
                .takeIf { Regex("[a-z0-9_]{4,32}").matches(it) } ?: throw InvalidInput("Telegram nomi noto'g'ri (@nom)")
            "other" -> v.take(200)
            else -> throw InvalidInput("Noma'lum tur: $type")
        }
    }

    data class Input(
        val category: String,
        val targetType: String,
        val targetValue: String,
        val claimedOrg: String? = null,
        val incidentAt: Long? = null,
        val amountUzs: Long? = null,
        val description: String = "",
        val evidence: List<Pair<String, String>> = emptyList(),
        /** (kod, sarlavha) — kod tahlil uchun, sarlavha odam o'qishi uchun. */
        val findings: List<Pair<String, String>> = emptyList(),
        val reporterContact: String? = null,
    )

    fun buildContent(inp: Input, reportId: String, createdAt: Long, deviceId: String, appVersion: String, dbVersion: Long): JSONObject {
        if (inp.category !in CATEGORIES) throw InvalidInput("Firibgarlik turini tanlang")
        val target = normalizeTarget(inp.targetType, inp.targetValue)
        val ev = JSONArray()
        for ((kind, value) in inp.evidence.take(MAX_EVIDENCE)) {
            if (value.isBlank()) continue
            ev.put(JSONObject().put("kind", kind).put("value", value.take(MAX_TEXT)))
        }
        fun opt(v: Any?): Any = v ?: JSONObject.NULL
        return JSONObject()
            .put("v", 1)
            .put("report_id", reportId)
            .put("created_at", createdAt)
            .put("category", inp.category)
            .put("target_type", inp.targetType)
            .put("target_value", target)
            .put("target_value_hash", targetHash(inp.targetType, target))
            .put("claimed_org", opt(inp.claimedOrg?.trim()?.ifBlank { null }?.take(100)))
            .put("incident_at", opt(inp.incidentAt))
            .put("amount_uzs", opt(inp.amountUzs?.takeIf { it > 0 }))
            .put("description", inp.description.trim().take(MAX_TEXT))
            .put("evidence", ev)
            .put("findings", JSONArray().apply {
                for ((code, title) in inp.findings.take(30)) put(JSONObject().put("code", code.take(60)).put("title", title.take(200)))
            })
            .put("reporter_contact", opt(inp.reporterContact?.trim()?.ifBlank { null }?.take(200)))
            .put("app", JSONObject().put("version", appVersion).put("db_version", dbVersion))
            .put("device_id", deviceId)
    }

    fun create(inp: Input, edSeed: ByteArray, mlSeed: ByteArray, reportId: String, createdAt: Long,
               appVersion: String, dbVersion: Long): JSONObject {
        val (edPk, mlPk) = Hybrid.publicKeys(edSeed, mlSeed)
        val did = deviceId(edPk, mlPk)
        val content = buildContent(inp, reportId, createdAt, did, appVersion, dbVersion)
        val bytes = content.toString().toByteArray(Charsets.UTF_8)
        val sig = Hybrid.sign(edSeed, mlSeed, DOMAIN + bytes)
        val b64 = Base64.getEncoder()
        return JSONObject()
            .put("format", FORMAT)
            .put("content", b64.encodeToString(bytes))
            .put("sig", b64.encodeToString(sig))
            .put("ed25519_pk", b64.encodeToString(edPk))
            .put("mldsa65_pk", b64.encodeToString(mlPk))
            .put("device_id", did)
            .put("readable", readable(content))
    }

    data class Verified(val ok: Boolean, val error: String? = null, val content: JSONObject? = null)

    fun verify(fileJson: String): Verified {
        val b64 = Base64.getDecoder()
        val f = try { JSONObject(fileJson) } catch (e: Exception) { return Verified(false, "JSON emas") }
        if (f.optString("format") != FORMAT) return Verified(false, "noma'lum format")
        val bytes: ByteArray; val sig: ByteArray; val edPk: ByteArray; val mlPk: ByteArray
        try {
            bytes = b64.decode(f.getString("content")); sig = b64.decode(f.getString("sig"))
            edPk = b64.decode(f.getString("ed25519_pk")); mlPk = b64.decode(f.getString("mldsa65_pk"))
        } catch (e: Exception) { return Verified(false, "maydonlar buzilgan") }
        if (!Hybrid.verify(edPk, mlPk, sig, DOMAIN + bytes)) return Verified(false, "imzo haqiqiy emas")
        val c = JSONObject(String(bytes, Charsets.UTF_8))
        val did = deviceId(edPk, mlPk)
        if (f.optString("device_id") != did || c.optString("device_id") != did) return Verified(false, "qurilma ID mos emas")
        if (c.optInt("v") != 1) return Verified(false, "hisobot versiyasi qo'llab-quvvatlanmaydi")
        if (c.optString("target_value_hash") != targetHash(c.optString("target_type"), c.optString("target_value"))) {
            return Verified(false, "target xeshi mos emas")
        }
        return Verified(true, content = c)
    }

    private fun fmt(secs: Long): String = SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.ROOT)
        .apply { timeZone = TimeZone.getTimeZone("Asia/Tashkent") }.format(Date(secs * 1000))

    private fun shownTarget(type: String, v: String): String = when (type) {
        "phone" -> PhoneNumbers.display(v)
        "card" -> v.chunked(4).joinToString(" ")
        "telegram" -> "@$v"
        else -> v
    }

    private val EVIDENCE_LABELS = mapOf(
        "sms_text" to "Xabar matni", "url" to "Havola", "call" to "Qo'ng'iroq", "apk" to "APK fayl", "note" to "Izoh",
    )

    /** Militsiya yoki bank xodimi o'qiydigan matn (imzolangan content'dan yasaladi). */
    fun readable(c: JSONObject): String = buildString {
        val type = c.getString("target_type")
        appendLine("ROSTOR-2 FIRIBGARLIK HISOBOTI")
        appendLine("Hisobot raqami: R2-${c.getString("report_id").substring(0, 12).uppercase()}")
        appendLine("Yaratilgan: ${fmt(c.getLong("created_at"))} (Toshkent vaqti)")
        appendLine("Turi: ${CATEGORIES[c.getString("category")] ?: c.getString("category")}")
        appendLine("Firibgar — ${TARGET_TYPES[type] ?: type}: ${shownTarget(type, c.getString("target_value"))}")
        if (!c.isNull("claimed_org")) appendLine("O'zini tanishtirgan tashkilot: ${c.getString("claimed_org")}")
        if (!c.isNull("incident_at")) appendLine("Voqea vaqti: ${fmt(c.getLong("incident_at"))}")
        if (!c.isNull("amount_uzs")) appendLine("Yo'qotilgan summa: ${"%,d".format(Locale.ROOT, c.getLong("amount_uzs")).replace(',', ' ')} so'm")
        val d = c.optString("description")
        if (d.isNotBlank()) { appendLine(); appendLine("Voqea tavsifi:"); appendLine(d) }
        val ev = c.optJSONArray("evidence")
        if (ev != null && ev.length() > 0) {
            appendLine(); appendLine("Dalillar:")
            for (i in 0 until ev.length()) {
                val e = ev.getJSONObject(i)
                appendLine("- ${EVIDENCE_LABELS[e.getString("kind")] ?: e.getString("kind")}: ${e.getString("value")}")
            }
        }
        val fd = c.optJSONArray("findings")
        if (fd != null && fd.length() > 0) {
            appendLine(); appendLine("ROSTOR-2 aniqlagan belgilar:")
            for (i in 0 until fd.length()) {
                val x = fd.optJSONObject(i)
                appendLine("- " + (x?.optString("title")?.ifBlank { null } ?: x?.optString("code") ?: fd.get(i).toString()))
            }
        }
        if (!c.isNull("reporter_contact")) { appendLine(); appendLine("Murojaatchi: ${c.getString("reporter_contact")}") }
        appendLine()
        appendLine("---")
        appendLine("Hisobot telefon ichida yaratilgan va qurilma kaliti bilan imzolangan (Ed25519 + ML-DSA-65).")
        appendLine("Qurilma ID: ${c.getString("device_id")}")
        append("Imzolangan asl nusxa ilova qilingan .json faylda; bu matn uning o'qish uchun nusxasi.")
    }
}
