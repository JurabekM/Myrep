package uz.mpay.wallet.sdk

import android.content.Context
import android.util.Log
import uz.mpay.core.ApiException
import uz.mpay.core.CardApplet
import uz.mpay.core.CardLuk
import uz.mpay.core.CardProfile
import uz.mpay.core.MpayClient
import uz.mpay.core.ProvisionResult
import uz.mpay.core.Hex
import uz.mpay.core.Revocations
import uz.mpay.core.ServerPinPolicy
import uz.mpay.core.TlsConfig
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
    /** Oflayn ildiz barmoq izi (ADR-0014): berilsa, serverdan bekor qilish ro'yxati olinib tekshiriladi. */
    val rootFingerprint: String? = null,
)

/**
 * Wallet SDK fasadi: PQ Link ulanish, provisioning, OTP, LUK to'ldirish, HCE applet va CDCVM.
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

    /** HCE applet (bitta nusxa — servis va UI bir xil holatni ko'radi). */
    val applet = CardApplet(
        profileProvider = { runCatching { store.load() }.getOrNull() },
        cdcvm = cdcvm,
        onChanged = { p -> store.save(p); emit("Tap: ATC=${p.atc}, LUK ${p.luks.count { it.usesLeft > 0 }} ta yaroqli") },
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
     * Bekor qilish ro'yxati: ildiz pinlangan bo'lsa olinadi va tekshiriladi; faqat kattaroq versiya
     * saqlanadi (orqaga qaytarib bo'lmaydi). Tarmoq yoki imzo xatosida saqlangan ro'yxat ishlatiladi.
     */
    private fun refreshRevocations(c: MpayClient, cfg: WalletConfig, prefs: android.content.SharedPreferences): Set<String> {
        val stored = prefs.getStringSet("revoked", emptySet())!!.toSet()
        val root = cfg.rootFingerprint ?: return stored
        val fresh = runCatching { c.revocationsJson()?.let { Revocations.verify(it, root) } }
            .onFailure { emit("Bekor qilish ro'yxati rad etildi: ${it.message}") }
            .getOrNull() ?: return stored
        if (fresh.version <= prefs.getLong("revoked_version", -1)) return stored
        prefs.edit().putStringSet("revoked", fresh.revoked).putLong("revoked_version", fresh.version).apply()
        emit("Bekor qilish ro'yxati yangilandi: versiya ${fresh.version}, ${fresh.revoked.size} ta")
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

    /**
     * Token muddati yaqinlashgan bo'lsa (`renewAfter` o'tgan) — serverda uzaytiradi va profilni yangilaydi
     * (keyingi tap'larda yangi muddat). Qaytaradi: muddat o'zgardimi.
     */
    fun renewIfDue(nowUnix: Long = System.currentTimeMillis() / 1000): Boolean {
        val p = store.load() ?: return false
        val due = p.renewAfter ?: return false
        if (nowUnix < due) return false
        val r = withReattest { c().renew(p.tokenId) }
        p.renewAfter = r.renewAfter
        val changed = r.expiryYymm != p.expiryYymm
        p.expiryYymm = r.expiryYymm
        store.save(p)
        if (changed) emit("Token muddati yangilandi: ${r.expiryYymm.take(2)}/${r.expiryYymm.drop(2)}")
        return changed
    }

    fun replenish(): Int {
        // Muddati o'tgan tokenga LUK berilmaydi — avval yangilashga urinish (xato LUK to'ldirishni to'xtatmaydi).
        runCatching { renewIfDue() }.onFailure { emit("Muddatni yangilab bo'lmadi: ${it.message}") }
        val p = store.load() ?: throw IllegalStateException("token yo'q")
        val batch = withReattest { c().replenishBatch(p.tokenId) }
        val luks: List<CardLuk> = batch.luks
        p.luks.removeAll { it.usesLeft <= 0 || it.expiresAt <= System.currentTimeMillis() / 1000 }
        p.luks.addAll(luks)
        batch.cvmLimitMinor?.let { p.cvmLimitMinor = it }
        store.save(p)
        emit("LUK to'ldirildi: +${luks.size}")
        return luks.size
    }

    private fun save(p: CardProfile) {
        store.save(p)
        emit("Token faol: ${maskPan(p.dpan)}, ${p.luks.size} ta LUK")
    }

    fun profile(): CardProfile? = runCatching { store.load() }.getOrNull()

    fun reset() {
        store.clear()
        app.getSharedPreferences("mpay", Context.MODE_PRIVATE).edit().clear().apply()
        AndroidDeviceKey.delete()
        client = null
    }
}
