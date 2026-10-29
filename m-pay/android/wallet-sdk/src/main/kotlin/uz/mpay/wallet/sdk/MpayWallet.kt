package uz.mpay.wallet.sdk

import android.content.Context
import android.util.Log
import uz.mpay.core.ApiException
import uz.mpay.core.CardApplet
import uz.mpay.core.CardChange
import uz.mpay.core.CardLuk
import uz.mpay.core.CardProfile
import uz.mpay.core.MpayClient
import uz.mpay.core.ProvisionResult
import uz.mpay.core.Hex
import uz.mpay.core.RevocationSources
import uz.mpay.core.ServerPinPolicy
import uz.mpay.core.TlsConfig
import uz.mpay.core.TxnPage
import uz.mpay.core.WalletCard
import uz.mpay.core.WalletToken
import uz.mpay.core.maskPan
import uz.mpay.core.pqlink.ServerIdentity
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Server ishonchi (1-faza, P1.5): bank ilovasi build vaqtida beradi.
 * * `pinnedFingerprints` — PQ Link server barmoq izlari (rotation davrida joriy + keyingi);
 * * `tlsCertSha256` — `https://` server TLS sertifikati pini;
 * * `allowTofu` — faqat sandbox: pin yo'q bo'lsa birinchi ulanishda eslab qolish.
 */
class WalletConfig(
    val pinnedFingerprints: List<String> = emptyList(),
    val tlsCertSha256: ByteArray? = null,
    val allowTofu: Boolean = false,
    /** Oflayn ildiz barmoq izi (ADR-0014): berilsa, bekor qilish ro'yxati olinib tekshiriladi. */
    val rootFingerprint: String? = null,
    /**
     * Ilova build'iga joylangan imzolangan ro'yxat (ADR-0029) — yangi o'rnatilgan ilova ham oshkor
     * kalitni darhol rad etadi. Ildiz imzosi baribir tekshiriladi.
     */
    val bundledRevocations: String? = null,
    /**
     * Mustaqil kanal (ADR-0029): PQ Link serveridan alohida statik fayllar (CDN), faqat `https://`.
     * Hujumchi serveri ro'yxatni bermasa ham qurilma uni shu yerdan oladi.
     */
    val revocationUrls: List<String> = emptyList(),
)

/**
 * Wallet SDK fasadi: PQ Link ulanish, provisioning, OTP, LUK to'ldirish, HCE applet va CDCVM; ko'p
 * karta — ro'yxat, asosiy karta, server bilan moslash, kartani o'zi boshqarish, tarix (ADR-0030).
 * Tarmoq chaqiruvlari bloklovchi — UI'da fon oqimidan (`Dispatchers.IO`) chaqiring.
 */
class MpayWallet private constructor(context: Context) {
    private val app = context.applicationContext
    val store = WalletStore(app)
    val cdcvm = CdcvmState(app)

    /** Ulanishdan oldin o'rnatiladi; standart — pin yo'q va TOFU o'chiq (xavfsiz rad). */
    var config: WalletConfig = WalletConfig()
    private var client: MpayClient? = null
    private var pinnedFingerprint: String? = null
    private val listeners = CopyOnWriteArrayList<(String) -> Unit>()

    /**
     * Keyingi bitta tap uchun tanlangan karta (asosiy o'rniga); tap'dan keyin tozalanadi. To'xtatilgan
     * karta tanlanmaydi ([uz.mpay.core.CardBook.tapCard]).
     */
    @Volatile
    var nextTapCard: String? = null

    /** HCE applet (bitta nusxa — servis va UI bir xil holatni ko'radi). */
    val applet = CardApplet(
        profileProvider = { runCatching { store.read { it.tapCard(nextTapCard) } }.getOrNull() },
        cdcvm = cdcvm,
        onChanged = { p ->
            store.update { it.put(p) }
            nextTapCard = null
            emit("Tap: ${maskPan(p.dpan)}, ATC=${p.atc}, LUK ${p.luks.count { it.usesLeft > 0 }} ta yaroqli")
        },
    )

    companion object {
        private const val TAG = "MpayWallet"
        @Volatile private var instance: MpayWallet? = null

        fun get(context: Context): MpayWallet =
            instance ?: synchronized(this) { instance ?: MpayWallet(context).also { instance = it } }
    }

    fun addListener(l: (String) -> Unit) { listeners.add(l) }
    fun removeListener(l: (String) -> Unit) { listeners.remove(l) }
    internal fun emit(event: String) {
        Log.i(TAG, event) // faqat maskalangan ma'lumot
        listeners.forEach { it(event) }
    }

    private val prefs get() = app.getSharedPreferences("mpay", Context.MODE_PRIVATE)

    /** Joriy kalit aliasi: kalit almashtirishda (ADR-0015) ikki alias navbatma-navbat ishlatiladi. */
    private val alias: String get() = prefs.getString("device_alias", AndroidDeviceKey.DEFAULT_ALIAS)!!

    private var identity: ServerIdentity? = null

    /** Mavjud qurilma kaliti (bo'lmasa — lokal; serverga ulanishda nonce bilan qayta yaratiladi). */
    fun deviceKey(): AndroidDeviceKey = AndroidDeviceKey.getOrCreate("mpay-local".toByteArray(), alias)

    /**
     * P1.7: yangi qurilma kaliti server nonce'i bilan yaratiladi (attestatsiya yangiligi). Server
     * qurilmani tanimasa (`PQLINK_ENROLLMENT`) — kalit bir marta qayta yaratiladi; eski tokenlar yangi
     * qurilmaga o'tmaydi.
     */
    private fun connectEnrolled(c: MpayClient, identity: ServerIdentity) {
        val a = alias
        val key = if (AndroidDeviceKey.exists(a)) deviceKey() else AndroidDeviceKey.getOrCreate(c.enrollNonce(), a)
        try {
            c.connect(identity, key)
        } catch (e: ApiException) {
            if (e.code != "PQLINK_ENROLLMENT") throw e
            emit("Qurilma serverda ro'yxatdan o'tmagan — kalit yangi nonce bilan qayta yaratilmoqda")
            AndroidDeviceKey.delete(a)
            c.connect(identity, AndroidDeviceKey.getOrCreate(c.enrollNonce(), a))
        }
        this.identity = identity
    }

    /**
     * Serverga ulanadi. Server identifikatori [WalletConfig] bo'yicha tekshiriladi ([ServerPinPolicy]):
     * build pinlari bo'lsa — faqat ular; bo'lmasa va sandbox'da ruxsat bo'lsa — TOFU.
     * `https://` uchun TLS sertifikati ham pinlanadi.
     */
    fun connect(serverUrl: String): String {
        val cfg = config
        val tls = if (serverUrl.startsWith("https://")) {
            TlsConfig(cfg.tlsCertSha256 ?: throw IllegalStateException("https uchun TLS pini kerak (WalletConfig.tlsCertSha256)"))
        } else {
            null
        }
        val c = MpayClient(serverUrl, tls = tls)
        val info = c.identityInfo()
        val identity = info.identity
        val fp = info.fingerprint
        val prefs = app.getSharedPreferences("mpay", Context.MODE_PRIVATE)
        val revoked = refreshRevocations(c, cfg, prefs)
        // Build pinlari + kalit almashtirishda o'rganilgan (joriy pin tasdiqlagan) pinlar, bekor qilinganlarsiz.
        val learned = prefs.getStringSet("pins_learned", emptySet())!!.toSet() - revoked
        // TOFU (sandbox): avval saqlangan barmoq izi ham to'plamda — o'rganilgan pin uni siqib chiqarmasin.
        val tofu = if (cfg.allowTofu) listOfNotNull(prefs.getString("server_fp", null)) else emptyList()
        val decision = ServerPinPolicy(cfg.pinnedFingerprints + learned + tofu, cfg.allowTofu, revoked)
            .check(fp, prefs.getString("server_fp", null))
        if (decision.storeTofu) prefs.edit().putString("server_fp", fp).apply()
        val rolled = ServerPinPolicy.rollForward(learned, info, revoked)
        if (rolled != learned) {
            prefs.edit().putStringSet("pins_learned", rolled).apply()
            emit("Server keyingi kaliti tasdiqlandi va pinlandi (${Hex.encode(info.next!!.fingerprint()).take(16)}…)")
        }
        connectEnrolled(c, identity)
        client = c
        pinnedFingerprint = fp
        emit("PQ Link ulandi (server ${fp.take(16)}…)")
        return fp
    }

    /**
     * Bekor qilish ro'yxati (ADR-0014, ADR-0029): ildiz pinlangan bo'lsa build nusxasi, mustaqil kanallar
     * va server — har biri ildiz imzosi bilan tekshiriladi, eng katta versiya olinadi. Faqat qurilmada
     * saqlangandan kattasi saqlanadi (orqaga qaytarib bo'lmaydi). Hech biri yetmasa — saqlangani.
     * Ro'yxat server identifikatori tekshirilishidan **oldin** yangilanadi.
     */
    private fun refreshRevocations(c: MpayClient, cfg: WalletConfig, prefs: android.content.SharedPreferences): Set<String> {
        val stored = prefs.getStringSet("revoked", emptySet())!!.toSet()
        val root = cfg.rootFingerprint ?: run {
            check(cfg.bundledRevocations == null && cfg.revocationUrls.isEmpty()) {
                "bekor qilish ro'yxati manbalari uchun WalletConfig.rootFingerprint kerak"
            }
            return stored
        }
        val candidates = buildList {
            add(RevocationSources.Candidate("ilova", cfg.bundledRevocations))
            cfg.revocationUrls.forEach { add(RevocationSources.Candidate(it, RevocationSources.fetch(it))) }
            add(RevocationSources.Candidate("server", runCatching { c.revocationsJson() }.getOrNull()))
        }
        val sel = RevocationSources.select(root, candidates)
        sel.rejected.forEach { emit("Bekor qilish ro'yxati rad etildi ($it)") }
        val fresh = sel.best ?: return stored
        if (fresh.version <= prefs.getLong("revoked_version", -1)) return stored
        prefs.edit().putStringSet("revoked", fresh.revoked).putLong("revoked_version", fresh.version).apply()
        emit("Bekor qilish ro'yxati yangilandi: versiya ${fresh.version} (${sel.bestSource}), ${fresh.revoked.size} ta")
        return fresh.revoked
    }

    private fun c(): MpayClient = client ?: throw IllegalStateException("avval serverga ulaning")

    /**
     * Davriy qayta attestatsiya (ADR-0015): server `REATTEST_REQUIRED` desa — yangi alias ostida nonce
     * bilan kalit yaratiladi, `rekey` (tokenlar ko'chadi), eski kalit o'chiriladi, qayta ulanib so'rov
     * bir marta takrorlanadi.
     */
    private fun <T> withReattest(block: () -> T): T = try {
        block()
    } catch (e: ApiException) {
        if (e.code != "REATTEST_REQUIRED") throw e
        rekeyDevice()
        block()
    }

    private fun rekeyDevice() {
        val c = c()
        val old = alias
        val next = if (old == AndroidDeviceKey.DEFAULT_ALIAS) "${AndroidDeviceKey.DEFAULT_ALIAS}-b" else AndroidDeviceKey.DEFAULT_ALIAS
        AndroidDeviceKey.delete(next) // avvalgi tugallanmagan urinish qoldig'i
        val key = AndroidDeviceKey.getOrCreate(c.enrollNonce(), next)
        val id = c.rekey(key)
        prefs.edit().putString("device_alias", next).apply()
        AndroidDeviceKey.delete(old)
        c.connect(identity ?: throw IllegalStateException("server identifikatori yo'q"), key)
        emit("Qurilma attestatsiyasi yangilandi: yangi kalit ${id.take(16)}…")
    }

    fun provision(pan: String, expiryYymm: String): ProvisionResult = withReattest { provisionOnce(pan, expiryYymm) }

    /** Provisioning'ga yaxlitlik tokeni (P2.6); `null` — yuborilmaydi. */
    @Volatile
    var integrityProvider: IntegrityTokenProvider? = null

    private fun provisionOnce(pan: String, expiryYymm: String): ProvisionResult {
        val c = c()
        // Qayta attestatsiyadan keyin sessiya yangi — hash ham har urinishda qayta hisoblanadi.
        val token = integrityProvider?.token(c.integrityRequestHash())
        val r = c.provision(pan, expiryYymm, token)
        if (r is ProvisionResult.Active) save(r.profile)
        return r
    }

    fun verifyOtp(tokenId: String, challengeId: String, otp: String): CardProfile =
        withReattest { c().verifyOtp(tokenId, challengeId, otp) }.also { save(it) }

    /** OTP SMS'ni karta egasining telefoniga qayta yuboradi; qaytaradi: maskalangan telefon. */
    fun resendOtp(tokenId: String, challengeId: String): String = withReattest { c().resendOtp(tokenId, challengeId) }

    fun sandboxOtp(challengeId: String, operatorKey: String): String = c().sandboxOtp(challengeId, operatorKey)

    /** Sandbox: mock token o'z PQ Link sessiyasi orqali (operator kaliti va mTLS'siz). */
    fun sandboxDeviceIntegrityToken(preset: String? = null): String? = c().sandboxDeviceIntegrityToken(preset)

    /** Sandbox: Play Integrity o'rnida server mock tokeni operator kaliti bilan (`preset` — sinov stsenariysi). */
    fun sandboxIntegrityToken(requestHash: String, operatorKey: String, preset: String? = null): String? =
        c().sandboxIntegrityToken(requestHash, operatorKey, preset)

    private fun card(tokenId: String?): CardProfile? =
        store.read { b -> (tokenId ?: b.defaultId)?.let { b.profile(it) } }

    /**
     * Token muddati yaqinlashgan bo'lsa (`renewAfter` o'tgan) — serverda uzaytiradi va profilni yangilaydi
     * (keyingi tap'larda yangi muddat). `tokenId == null` — asosiy karta. Qaytaradi: muddat o'zgardimi.
     */
    fun renewIfDue(tokenId: String? = null, nowUnix: Long = System.currentTimeMillis() / 1000): Boolean {
        val p = card(tokenId) ?: return false
        val due = p.renewAfter ?: return false
        if (nowUnix < due) return false
        val r = withReattest { c().renew(p.tokenId) }
        val changed = store.update { b ->
            val cur = b.profile(p.tokenId) ?: return@update false
            cur.renewAfter = r.renewAfter
            val ch = r.expiryYymm != cur.expiryYymm
            cur.expiryYymm = r.expiryYymm
            ch
        }
        if (changed) emit("Token muddati yangilandi: ${maskPan(p.dpan)}, ${r.expiryYymm.take(2)}/${r.expiryYymm.drop(2)}")
        return changed
    }

    /** LUK to'ldirish (`tokenId == null` — asosiy karta). Qaytaradi: yangi LUK'lar soni. */
    fun replenish(tokenId: String? = null): Int {
        val id = card(tokenId)?.tokenId ?: throw IllegalStateException("token yo'q")
        // Muddati o'tgan tokenga LUK berilmaydi — avval yangilashga urinish (xato LUK to'ldirishni to'xtatmaydi).
        runCatching { renewIfDue(id) }.onFailure { emit("Muddatni yangilab bo'lmadi: ${it.message}") }
        val batch = withReattest { c().replenishBatch(id) }
        val luks: List<CardLuk> = batch.luks
        val now = System.currentTimeMillis() / 1000
        store.update { b ->
            val p = b.profile(id) ?: return@update
            p.luks.removeAll { it.usesLeft <= 0 || it.expiresAt <= now }
            p.luks.addAll(luks)
            batch.cvmLimitMinor?.let { p.cvmLimitMinor = it }
        }
        emit("LUK to'ldirildi: +${luks.size}")
        return luks.size
    }

    /**
     * Davriy xizmat (fon sinxronlash): to'lash mumkin bo'lgan har kartada yaroqli LUK `minLuks` dan kam
     * bo'lsa to'ldiradi. Bitta kartadagi xato boshqalarini to'xtatmaydi. Qaytaradi: to'ldirilgan kartalar.
     */
    fun replenishLow(minLuks: Int = 2): List<String> = cards().filter { it.payable && it.luksLeft < minLuks }.mapNotNull { w ->
        runCatching { replenish(w.tokenId) }.onFailure { emit("LUK to'ldirilmadi (${w.dpanMasked}): ${it.message}") }
            .getOrNull()?.let { w.tokenId }
    }

    private fun save(p: CardProfile) {
        store.update { it.put(p) }
        emit("Token faol: ${maskPan(p.dpan)}, ${p.luks.size} ta LUK")
    }

    /** Asosiy karta profili (eski bitta kartali API bilan moslik). */
    fun profile(): CardProfile? = runCatching { card(null) }.getOrNull()

    // ------------------------------------------------------------ ko'p karta (ADR-0030)

    /** Hamyondagi kartalar (sirlarsiz): qurilmadagilar, so'ng faqat serverdagilar. */
    fun cards(): List<WalletCard> = store.read { it.view() }

    fun setDefaultCard(tokenId: String) {
        store.update { it.setDefault(tokenId) }
        emit("Asosiy karta: ${cards().first { it.tokenId == tokenId }.dpanMasked}")
    }

    /**
     * Server bilan moslash: holatlar (bank to'xtatgan/yoqqan), bank o'chirgan kartalar qurilmadan ham
     * o'chadi. Qaytaradi: o'zgarishlar (bildirishnoma uchun).
     */
    fun syncCards(): List<CardChange> {
        val tokens = withReattest { c().walletTokens() }
        val changes = store.update { it.applyServer(tokens) }
        changes.forEach { emit("Karta o'zgardi: $it") }
        return changes
    }

    /** Kartani o'zi to'xtatadi (yo'qotdim/shubha) — tap'lar rad etiladi, o'zi qayta yoqa oladi. */
    fun suspendCard(tokenId: String): WalletToken = setState(tokenId, "suspend")

    /** O'zi to'xtatgan kartani yoqadi; bank to'xtatgan bo'lsa — `ApiException(SUSPENDED_BY_BANK)`. */
    fun resumeCard(tokenId: String): WalletToken = setState(tokenId, "resume")

    /**
     * Kartani o'chiradi (serverda va qurilmada; qaytarib bo'lmaydi). Serverda allaqachon yo'q bo'lsa ham
     * qurilmadan o'chadi.
     */
    fun deleteCard(tokenId: String) {
        try {
            setState(tokenId, "delete")
        } catch (e: ApiException) {
            if (e.code != "TOKEN_NOT_FOUND") throw e
        }
        store.update { it.remove(tokenId) }
        if (nextTapCard == tokenId) nextTapCard = null
    }

    private fun setState(tokenId: String, action: String): WalletToken {
        val t = withReattest { c().walletSetState(tokenId, action) }
        store.update { it.applyServer(t) }
        emit("Karta ${t.dpanMasked}: ${t.state}")
        return t
    }

    /** Karta tarixi (yangilari birinchi); `cursor` — oldingi sahifaning `nextCursor` i. */
    fun transactions(tokenId: String, cursor: String? = null, limit: Int = 20): TxnPage =
        withReattest { c().transactions(tokenId, cursor, limit) }

    fun reset() {
        store.clear()
        app.getSharedPreferences("mpay", Context.MODE_PRIVATE).edit().clear().apply()
        AndroidDeviceKey.delete()
        client = null
    }
}
