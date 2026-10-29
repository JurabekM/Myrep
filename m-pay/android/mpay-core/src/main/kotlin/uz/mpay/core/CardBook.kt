package uz.mpay.core

import org.json.JSONArray
import org.json.JSONObject

/**
 * Hamyondagi karta — UI ko'rinishi (sirlarsiz). `onDevice = false` — server bu qurilmada tokenni biladi,
 * lekin profil (DPAN, LUK'lar) qurilmada yo'q (masalan, ilova qayta o'rnatilgan): to'lab bo'lmaydi,
 * faqat o'chirish mumkin.
 */
data class WalletCard(
    val tokenId: String,
    val dpanMasked: String,
    val fpanMasked: String?,
    val expiryYymm: String,
    /** `ACTIVE`, `SUSPENDED`, `PENDING_IDV`; server bilan hali moslanmagan bo'lsa — `ACTIVE`. */
    val state: String,
    val suspendedBy: String?,
    val luksLeft: Int,
    val isDefault: Boolean,
    val onDevice: Boolean,
) {
    val payable: Boolean get() = onDevice && state == "ACTIVE"
}

/** Server bilan moslashda aniqlangan o'zgarish (bildirishnoma uchun). */
sealed class CardChange {
    abstract val tokenId: String

    /** Holat o'zgardi (masalan, bank kartani to'xtatdi yoki qayta yoqdi). */
    data class State(override val tokenId: String, val from: String, val to: String, val by: String?) : CardChange()

    /** Serverda karta yo'q (bank o'chirgan) — qurilmadan ham o'chirildi. */
    data class Removed(override val tokenId: String, val dpanMasked: String) : CardChange()
}

/**
 * Ko'p kartali hamyon modeli (ADR-0030): profillar (DPAN, LUK'lar — sir), serverdagi holat va asosiy
 * karta. Platformadan mustaqil — saqlash (shifrlash) [toJson]/[fromJson] orqali ilovada.
 * Thread-safe emas: chaqiruvchi sinxronlaydi.
 */
class CardBook {
    private val cards = LinkedHashMap<String, CardProfile>()
    private val server = LinkedHashMap<String, WalletToken>()

    /** Asosiy karta — tap'da standart (foydalanuvchi tanlaydi). */
    var defaultId: String? = null
        private set

    val size: Int get() = cards.size

    fun profiles(): List<CardProfile> = cards.values.toList()

    fun profile(tokenId: String): CardProfile? = cards[tokenId]

    fun server(tokenId: String): WalletToken? = server[tokenId]

    /** Qo'shadi yoki yangilaydi; birinchi karta avtomatik asosiy bo'ladi. */
    fun put(p: CardProfile) {
        cards[p.tokenId] = p
        if (defaultId == null) defaultId = p.tokenId
    }

    /** Profil va server ma'lumotini o'chiradi; asosiy bo'lsa — keyingisi asosiy. */
    fun remove(tokenId: String): CardProfile? {
        server.remove(tokenId)
        val p = cards.remove(tokenId)
        if (defaultId == tokenId) defaultId = cards.keys.firstOrNull()
        return p
    }

    fun setDefault(tokenId: String) {
        require(tokenId in cards) { "karta qurilmada yo'q" }
        defaultId = tokenId
    }

    private fun state(tokenId: String): String = server[tokenId]?.state ?: "ACTIVE"

    /** To'lov qilsa bo'ladimi: qurilmada bor va server bo'yicha faol (moslanmagan bo'lsa — faol deb). */
    fun payable(tokenId: String): Boolean = tokenId in cards && state(tokenId) == "ACTIVE"

    /**
     * Tap uchun karta: `override` (foydalanuvchi shu to'lovga boshqasini tanlagan) yoki asosiy.
     * To'xtatilgan karta tanlanmaydi — terminal karta yo'q deb ko'radi.
     */
    fun tapCard(override: String? = null): CardProfile? {
        val id = override?.takeIf { payable(it) } ?: defaultId?.takeIf { payable(it) } ?: return null
        return cards[id]
    }

    /** UI ro'yxati: qurilmadagilar (qo'shilgan tartibda), so'ng faqat serverdagilar. */
    fun view(nowUnix: Long = System.currentTimeMillis() / 1000): List<WalletCard> {
        val local = cards.values.map { p ->
            val s = server[p.tokenId]
            WalletCard(
                tokenId = p.tokenId,
                dpanMasked = maskPan(p.dpan),
                fpanMasked = s?.fpanMasked,
                expiryYymm = p.expiryYymm,
                state = s?.state ?: "ACTIVE",
                suspendedBy = s?.suspendedBy,
                luksLeft = p.luks.count { it.usesLeft > 0 && it.expiresAt > nowUnix },
                isDefault = p.tokenId == defaultId,
                onDevice = true,
            )
        }
        val remote = server.values.filter { it.tokenId !in cards }.map { s ->
            WalletCard(s.tokenId, s.dpanMasked, s.fpanMasked, s.dpanExpiry, s.state, s.suspendedBy, 0, false, false)
        }
        return local + remote
    }

    /**
     * Server ro'yxati bilan moslash ([MpayClient.walletTokens]). Serverda yo'q qurilma kartalari
     * o'chiriladi (bank o'chirgan — LUK'lar ham ketadi). Qaytaradi: bildirishnoma uchun o'zgarishlar.
     */
    fun applyServer(tokens: List<WalletToken>): List<CardChange> {
        val changes = mutableListOf<CardChange>()
        val ids = tokens.map { it.tokenId }.toSet()
        for (id in cards.keys.filter { it !in ids }) {
            val p = remove(id)!!
            changes += CardChange.Removed(id, maskPan(p.dpan))
        }
        server.keys.retainAll(ids)
        for (t in tokens) {
            val old = server[t.tokenId]?.state ?: if (t.tokenId in cards) "ACTIVE" else null
            if (old != null && old != t.state) changes += CardChange.State(t.tokenId, old, t.state, t.suspendedBy)
            server[t.tokenId] = t
        }
        return changes
    }

    /** Bitta karta server javobi ([MpayClient.walletSetState]). `DELETED` — kartani butunlay o'chiradi. */
    fun applyServer(token: WalletToken) {
        if (token.state == "DELETED") remove(token.tokenId) else server[token.tokenId] = token
    }

    fun clear() {
        cards.clear()
        server.clear()
        defaultId = null
    }

    fun toJson(): String = JSONObject()
        .put("v", 2)
        .put("default", defaultId ?: JSONObject.NULL)
        .put("cards", JSONArray().apply { cards.values.forEach { put(profileJson(it)) } })
        .put("server", JSONArray().apply { server.values.forEach { put(tokenJson(it)) } })
        .toString()

    companion object {
        /** v2 yoki eski bitta kartali format (v1 — `token_id` yuqori darajada): migratsiya. */
        fun fromJson(s: String): CardBook {
            val j = JSONObject(s)
            val b = CardBook()
            if (!j.has("v")) {
                b.put(profileFrom(j))
                return b
            }
            require(j.getInt("v") == 2) { "noma'lum hamyon formati" }
            j.getJSONArray("cards").let { a -> repeat(a.length()) { b.put(profileFrom(a.getJSONObject(it))) } }
            j.optJSONArray("server")?.let { a -> repeat(a.length()) { i -> tokenFrom(a.getJSONObject(i)).let { b.server[it.tokenId] = it } } }
            if (!j.isNull("default")) j.getString("default").takeIf { it in b.cards }?.let { b.defaultId = it }
            return b
        }

        private fun profileJson(p: CardProfile) = JSONObject()
            .put("token_id", p.tokenId).put("dpan", p.dpan).put("expiry", p.expiryYymm).put("psn", p.psn).put("atc", p.atc)
            .put("cvm", p.cvmLimitMinor)
            .put("renew_after", p.renewAfter ?: JSONObject.NULL)
            .put("luks", JSONArray().apply {
                p.luks.forEach { put(JSONObject().put("seq", it.seq).put("key", Hex.encode(it.key)).put("exp", it.expiresAt).put("uses", it.usesLeft)) }
            })

        private fun profileFrom(j: JSONObject): CardProfile {
            val a = j.getJSONArray("luks")
            return CardProfile(
                j.getString("token_id"), j.getString("dpan"), j.getString("expiry"), j.getInt("psn"),
                MutableList(a.length()) { i ->
                    val l = a.getJSONObject(i)
                    CardLuk(l.getLong("seq"), Hex.decode(l.getString("key")), l.getLong("exp"), l.getInt("uses"))
                },
                j.getInt("atc"),
                j.optLong("cvm", DEFAULT_CVM_LIMIT_MINOR),
                if (j.isNull("renew_after")) null else j.getLong("renew_after"),
            )
        }

        private fun tokenJson(t: WalletToken) = JSONObject()
            .put("token_id", t.tokenId).put("state", t.state).put("dpan_masked", t.dpanMasked)
            .put("fpan_masked", t.fpanMasked).put("dpan_expiry", t.dpanExpiry)
            .put("created_at", t.createdAt).put("updated_at", t.updatedAt)
            .put("suspended_by", t.suspendedBy ?: JSONObject.NULL)

        private fun tokenFrom(j: JSONObject) = WalletToken(
            j.getString("token_id"), j.getString("state"), j.getString("dpan_masked"), j.getString("fpan_masked"),
            j.getString("dpan_expiry"), j.getLong("created_at"), j.getLong("updated_at"),
            if (j.isNull("suspended_by")) null else j.getString("suspended_by"),
        )
    }
}
