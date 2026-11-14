package uz.rostor.rostor2.call

import org.json.JSONObject
import java.net.URLDecoder

/**
 * Qo'ng'iroq Qalqoni qoidalari (F2). Sof JVM kodi: Android'ga bog'liq emas, unit testda ishlaydi.
 * Raqam normallashtirish Dart tomonidagi `lib/core/phone.dart` bilan bir xil bo'lishi shart —
 * ikkalasi ham `app/test/fixtures/phone_kat.json` vektorlari bilan tekshiriladi.
 */
object PhoneNumbers {
    /**
     * Kanonik ko'rinish:
     *  - O'zbekiston va xorijiy raqamlar: "+<mamlakat kodi><raqam>" (E.164);
     *  - qisqa va ichki raqamlar (1102, 0611, 0 800 ...): faqat raqamlar, "+" siz.
     * Raqam bo'lmasa — null.
     */
    fun normalize(raw: String?): String? {
        if (raw == null) return null
        var s = raw.trim()
        if (s.startsWith("tel:", ignoreCase = true)) s = s.substring(4)
        // tel: URI'da "+" ko'pincha %2B bo'lib keladi; URLDecoder esa ochiq "+" ni probelga aylantiradi.
        if ('%' in s) s = try { URLDecoder.decode(s.replace("+", "%2B"), "UTF-8") } catch (e: Exception) { s }
        val plus = s.trimStart().startsWith("+")
        val d = s.filter { it in '0'..'9' }
        if (d.isEmpty()) return null
        return when {
            plus -> "+$d"
            d.startsWith("00") && d.length >= 9 -> "+" + d.substring(2)
            d.length == 12 && d.startsWith("998") -> "+$d"
            d.length == 9 && d[0] != '0' -> "+998$d"
            else -> d
        }
    }

    fun isShort(n: String) = !n.startsWith("+")
    fun isUz(n: String) = n.startsWith("+998")

    /** "+998712310880" -> "+998 71 231 08 80"; boshqalar o'zgarishsiz. */
    fun display(n: String): String {
        if (isUz(n) && n.length == 13) {
            val x = n.substring(4)
            return "+998 ${x.substring(0, 2)} ${x.substring(2, 5)} ${x.substring(5, 7)} ${x.substring(7)}"
        }
        return n
    }

    private val countries = listOf(
        "+992" to "Tojikiston", "+993" to "Turkmaniston", "+996" to "Qirg'iziston", "+994" to "Ozarbayjon",
        "+380" to "Ukraina", "+971" to "BAA", "+90" to "Turkiya", "+44" to "Buyuk Britaniya",
        "+86" to "Xitoy", "+82" to "Janubiy Koreya", "+49" to "Germaniya", "+77" to "Qozog'iston",
        "+7" to "Rossiya", "+1" to "AQSh yoki Kanada",
    )

    fun country(n: String): String? = countries.firstOrNull { n.startsWith(it.first) }?.second
}

data class OfficialPhone(val orgId: String, val orgName: String, val label: String, val number: String)

/** Imzosi tekshirilgan baza payload'idan qurilgan raqamlar indeksi. */
class PhoneIndex(val official: Map<String, List<OfficialPhone>>, val malicious: Set<String>) {
    companion object {
        val EMPTY = PhoneIndex(emptyMap(), emptySet())

        fun fromPayload(payload: String): PhoneIndex {
            val j = JSONObject(payload)
            val official = HashMap<String, MutableList<OfficialPhone>>()
            val orgs = j.optJSONArray("organizations")
            if (orgs != null) for (i in 0 until orgs.length()) {
                val o = orgs.getJSONObject(i)
                val phones = o.optJSONArray("phones") ?: continue
                for (k in 0 until phones.length()) {
                    val p = phones.getJSONObject(k)
                    val n = PhoneNumbers.normalize(p.optString("number")) ?: continue
                    official.getOrPut(n) { mutableListOf() } += OfficialPhone(
                        o.getString("id"), o.optString("name", o.getString("id")), p.optString("label"), p.optString("number"),
                    )
                }
            }
            val mal = HashSet<String>()
            val mp = j.optJSONObject("malicious")?.optJSONArray("phones")
            if (mp != null) for (i in 0 until mp.length()) {
                val v = mp.get(i)
                val raw = if (v is JSONObject) v.optString("number") else v.toString()
                PhoneNumbers.normalize(raw)?.let { mal += it }
            }
            return PhoneIndex(official, mal)
        }
    }
}

/** Foydalanuvchi sozlamalari (SharedPreferences "rostor2" dan o'qiladi). */
data class CallPolicy(
    val blockFlagged: Boolean = true,
    val silenceInternational: Boolean = false,
    val notifyOfficial: Boolean = true,
    val userBlocked: Set<String> = emptySet(),
)

data class CallFinding(val code: String, val severity: String, val title: String, val explain: String, val evidence: String? = null) {
    fun toMap() = mapOf("code" to code, "severity" to severity, "title" to title, "explain" to explain, "evidence" to evidence)
}

data class CallVerdict(
    val normalized: String?,
    val findings: List<CallFinding>,
    val block: Boolean,
    val silence: Boolean,
    val official: List<OfficialPhone>,
) {
    val severity: String get() = findings.maxByOrNull { RANK.indexOf(it.severity) }?.severity ?: "ok"
    val top: CallFinding? get() = findings.maxByOrNull { RANK.indexOf(it.severity) }

    fun toMap(): Map<String, Any?> = mapOf(
        "normalized" to normalized,
        "display" to normalized?.let { PhoneNumbers.display(it) },
        "severity" to severity,
        "block" to block,
        "silence" to silence,
        "findings" to findings.map { it.toMap() },
        "official" to official.map { mapOf("orgId" to it.orgId, "orgName" to it.orgName, "label" to it.label, "number" to it.number) },
    )

    companion object {
        val RANK = listOf("ok", "info", "low", "medium", "high", "critical")
    }
}

object PhoneRules {
    /** Connection.VERIFICATION_STATUS_* bilan bir xil qiymatlar (API 30+, STIR/SHAKEN). */
    const val VERIFY_NONE = 0
    const val VERIFY_PASSED = 1
    const val VERIFY_FAILED = 2

    private const val NEVER_ASK =
        "xodimi hech qachon SMS kod, karta amal qilish muddati yoki CVV ni so'ramaydi va pulni \"xavfsiz hisobga\" o'tkazishni talab qilmaydi."

    fun evaluate(raw: String?, hidden: Boolean, verification: Int, idx: PhoneIndex, policy: CallPolicy): CallVerdict {
        val n = if (hidden) null else PhoneNumbers.normalize(raw)
        val out = mutableListOf<CallFinding>()
        if (n == null) {
            out += CallFinding(
                "call.hidden", "low", "Yashirin raqam",
                "Qo'ng'iroq qiluvchi raqamini yashirgan. O'zini bank, IIV yoki operator xodimi deb tanishtirsa, " +
                    "go'shakni qo'ying va tashkilotning rasmiy raqamiga o'zingiz qo'ng'iroq qiling.",
            )
            return CallVerdict(null, out, block = false, silence = false, official = emptyList())
        }
        val shown = PhoneNumbers.display(n)
        val official = idx.official[n].orEmpty()
        val orgNames = official.map { it.orgName }.distinct().joinToString(", ")
        var block = false
        var silence = false

        if (n in policy.userBlocked) {
            out += CallFinding("call.user_blocked", "high", "Siz bloklagan raqam", "Bu raqamni ROSTOR-2 da o'zingiz bloklagansiz.", shown)
            block = policy.blockFlagged
        }
        if (n in idx.malicious) {
            out += CallFinding(
                "call.malicious", "critical", "Firibgar raqam",
                "Bu raqam ROSTOR-2 bazasida firibgarlik raqami sifatida qayd etilgan. Javob bermang, " +
                    "javob bergan bo'lsangiz hech qanday kod yoki karta ma'lumotini aytmang.",
                shown,
            )
            block = policy.blockFlagged
        }
        if (verification == VERIFY_FAILED) {
            out += if (official.isNotEmpty()) CallFinding(
                "call.official_spoofed", "critical", "$orgNames raqami soxtalashtirilgan bo'lishi mumkin",
                "Raqam $orgNames ga tegishli, lekin operator bu qo'ng'iroq haqiqatan shu raqamdan kelayotganini tasdiqlamadi. " +
                    "Firibgarlar rasmiy raqamni ko'rsatib qo'ng'iroq qiladi. Go'shakni qo'ying va rasmiy raqamga o'zingiz qo'ng'iroq qiling.",
                shown,
            ) else CallFinding(
                "call.verification_failed", "high", "Raqam tasdiqlanmadi",
                "Operator bu qo'ng'iroq ko'rsatilgan raqamdan kelayotganini tasdiqlamadi — raqam soxtalashtirilgan bo'lishi mumkin.",
                shown,
            )
        }
        if (official.isNotEmpty() && verification != VERIFY_FAILED) {
            val labels = official.mapNotNull { it.label.ifBlank { null } }.distinct().joinToString(", ")
            out += CallFinding(
                "call.official", "info", "$orgNames rasmiy raqami",
                "Raqam $orgNames ning rasmiy saytida ko'rsatilgan" + (if (labels.isNotEmpty()) " ($labels)" else "") + ". " +
                    (if (verification == VERIFY_PASSED) "Operator raqamni tasdiqladi. " else "Lekin raqamni soxtalashtirish mumkin: ") +
                    "$orgNames $NEVER_ASK",
                shown,
            )
        }
        if (!PhoneNumbers.isShort(n) && !PhoneNumbers.isUz(n)) {
            val c = PhoneNumbers.country(n)
            out += CallFinding(
                "call.international", "medium", "Xorijiy raqam" + (c?.let { " ($it)" } ?: ""),
                "Qo'ng'iroq O'zbekistondan tashqaridagi raqamdan. O'zini O'zbekistondagi bank, to'lov tizimi, IIV yoki " +
                    "operator xodimi deb tanishtirsa — bu firibgarlik belgisi: ular mahalliy rasmiy raqamlardan foydalanadi.",
                shown,
            )
            silence = policy.silenceInternational
        }
        if (out.isEmpty()) {
            out += CallFinding(
                "call.no_signal", "ok", "Raqam bazada yo'q",
                "Raqam na rasmiy, na firibgar raqamlar ro'yxatida. Bu kafolat emas: kim bo'lishidan qat'i nazar, " +
                    "telefonda SMS kod, karta muddati yoki CVV ni aytmang.",
                shown,
            )
        }
        return CallVerdict(n, out, block, silence && !block, official)
    }

    /** Ogohlantirish ko'rsatilsinmi: oddiy noma'lum raqamlar uchun bezovta qilmaymiz. */
    fun shouldNotify(v: CallVerdict, policy: CallPolicy): Boolean = when (v.severity) {
        "ok" -> false
        "info" -> policy.notifyOfficial && v.official.isNotEmpty()
        else -> true
    }
}
