package uz.mpay.core

import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI

/**
 * Bekor qilish ro'yxati bir nechta mustaqil manbadan (ADR-0029):
 * * ilova build'iga joylangan nusxa — yangi o'rnatilgan ilova ham oshkor kalitni darhol rad etadi;
 * * mustaqil kanal (CDN — statik fayl, PQ Link serveridan alohida) — hujumchi serveri ro'yxatni
 *   bermasa ham qurilma uni boshqa yo'l bilan oladi;
 * * PQ Link serverining o'zi (`GET /v1/pqlink/revocations`).
 *
 * Manbaga ishonilmaydi: har nusxa oflayn ildiz imzosi bilan tekshiriladi ([Revocations.verify]). Eng
 * katta versiya yutadi; qurilmada saqlangandan kichigi e'tiborsiz (orqaga qaytarib bo'lmaydi). Kanal
 * eski (lekin haqiqiy) ro'yxatni berishi mumkin — u shunchaki yutqazadi.
 */
object RevocationSources {
    /** Manba nomi (log uchun) va JSON (`null` — yo'q yoki yetib bo'lmadi). */
    class Candidate(val source: String, val json: String?)

    /** Eng katta versiyali haqiqiy ro'yxat (yo'q — `null`) va rad etilgan manbalar sababi bilan. */
    class Selection(val best: Revocations?, val bestSource: String?, val rejected: List<String>)

    fun select(pinnedRootFingerprint: String, candidates: List<Candidate>): Selection {
        var best: Revocations? = null
        var bestSource: String? = null
        val rejected = mutableListOf<String>()
        for (c in candidates) {
            val json = c.json ?: continue
            val r = try {
                Revocations.verify(json, pinnedRootFingerprint)
            } catch (e: Exception) {
                rejected += "${c.source}: ${e.message}"
                continue
            }
            if (best == null || r.version > best.version) {
                best = r
                bestSource = c.source
            }
        }
        return Selection(best, bestSource, rejected)
    }

    /**
     * Ro'yxatni mustaqil kanaldan oladi. Faqat `https://` (loopback `http://` — sinov uchun), yo'naltirishsiz,
     * [maxBytes] gacha, qisqa timeout. TLS — tizim ildizlari: fayl imzolangan, kanal faqat yetkazadi.
     * Har qanday xato — `null` (ulanish to'xtamaydi, boshqa manbalar va saqlangan ro'yxat ishlatiladi).
     */
    fun fetch(url: String, timeoutMs: Int = 3000, maxBytes: Int = 64 * 1024): String? = runCatching {
        val u = URI(url)
        val loopback = u.scheme == "http" && u.host in setOf("127.0.0.1", "localhost", "[::1]")
        require(u.scheme == "https" || loopback) { "faqat https://" }
        val c = u.toURL().openConnection() as HttpURLConnection
        try {
            c.connectTimeout = timeoutMs
            c.readTimeout = timeoutMs
            c.instanceFollowRedirects = false
            if (c.responseCode != 200) return@runCatching null
            val out = ByteArrayOutputStream()
            c.inputStream.use { s ->
                val buf = ByteArray(8192)
                while (true) {
                    val n = s.read(buf)
                    if (n < 0) break
                    out.write(buf, 0, n)
                    if (out.size() > maxBytes) return@runCatching null
                }
            }
            out.toString(Charsets.UTF_8.name())
        } finally {
            c.disconnect()
        }
    }.getOrNull()
}
