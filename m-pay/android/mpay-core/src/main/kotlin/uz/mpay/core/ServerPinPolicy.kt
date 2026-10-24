package uz.mpay.core

/**
 * PQ Link server identifikatorini pinlash siyosati (1-faza, P1.5).
 *
 * * `pinned` — build vaqtida ilovaga joylangan barmoq izlari (hex). Bir nechta bo'lishi mumkin:
 *   kalit almashtirish (P1.6) davrida joriy va keyingi identifikator birga pinlanadi.
 * * `allowTofu` — pin berilmagan sandbox build'ida birinchi ulanishda barmoq izini eslab qolish
 *   (Trust On First Use). Production build'da `false`.
 */
class ServerPinPolicy(pinned: Collection<String>, val allowTofu: Boolean) {
    val pinned: Set<String> = pinned.map { it.trim().lowercase() }.filter { it.isNotEmpty() }.toSet()

    init {
        require(this.pinned.all { it.length == 64 && it.all { ch -> ch in '0'..'9' || ch in 'a'..'f' } }) {
            "barmoq izi 64 hex belgi bo'lishi kerak"
        }
    }

    /** Qaror: qabul (va TOFU uchun yangi barmoq izini saqlash kerakmi). */
    data class Accept(val storeTofu: Boolean)

    /**
     * `fingerprint` — serverdan olingan va identifikatorga mosligi tekshirilgan barmoq izi;
     * `tofuStored` — avval TOFU bilan saqlangani (bo'lsa).
     */
    fun check(fingerprint: String, tofuStored: String?): Accept {
        val fp = fingerprint.lowercase()
        if (pinned.isNotEmpty()) {
            if (fp !in pinned) throw PinException("server barmoq izi pinlanmagan: ${fp.take(16)}…")
            return Accept(storeTofu = false)
        }
        if (!allowTofu) throw PinException("server barmoq izi pinlanmagan va TOFU o'chiq")
        if (tofuStored != null && !tofuStored.equals(fp, ignoreCase = true)) {
            throw PinException("server barmoq izi o'zgargan — pinlangan: ${tofuStored.take(16)}…")
        }
        return Accept(storeTofu = tofuStored == null)
    }

    companion object {
        /** `BuildConfig` qatori: vergul bilan ajratilgan hex barmoq izlari. */
        fun parseList(s: String): List<String> = s.split(',', ';', ' ').map { it.trim() }.filter { it.isNotEmpty() }
    }
}

class PinException(message: String) : SecurityException(message)
