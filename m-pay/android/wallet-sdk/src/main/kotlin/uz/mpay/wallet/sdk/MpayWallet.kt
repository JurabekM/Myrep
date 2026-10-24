package uz.mpay.wallet.sdk

import android.content.Context
import android.util.Log
import uz.mpay.core.CardApplet
import uz.mpay.core.CardLuk
import uz.mpay.core.CardProfile
import uz.mpay.core.MpayClient
import uz.mpay.core.ProvisionResult
import uz.mpay.core.maskPan
import uz.mpay.core.pqlink.ServerIdentity
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Wallet SDK fasadi: PQ Link ulanish, provisioning, OTP, LUK to'ldirish, HCE applet va CDCVM.
 * Tarmoq chaqiruvlari bloklovchi — UI'da fon oqimidan (`Dispatchers.IO`) chaqiring.
 */
class MpayWallet private constructor(context: Context) {
    private val app = context.applicationContext
    val store = WalletStore(app)
    val cdcvm = CdcvmState(app)
    var integrity: IntegrityProvider = StubIntegrityProvider
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

    fun deviceKey(): AndroidDeviceKey = AndroidDeviceKey.getOrCreate("mpay-enroll".toByteArray())

    /** Serverga ulanadi (TOFU pinlash: birinchi ulanishda barmoq izi saqlanadi). */
    fun connect(serverUrl: String): String {
        val c = MpayClient(serverUrl)
        val (identity, fp) = c.identity()
        val prefs = app.getSharedPreferences("mpay", Context.MODE_PRIVATE)
        val pinned = prefs.getString("server_fp", null)
        if (pinned != null && !pinned.equals(fp, ignoreCase = true)) {
            throw IllegalStateException("server barmoq izi o'zgargan — pinlangan: ${pinned.take(16)}…")
        }
        prefs.edit().putString("server_fp", fp).apply()
        c.connect(identity, deviceKey())
        client = c
        pinnedFingerprint = fp
        emit("PQ Link ulandi (server ${fp.take(16)}…)")
        return fp
    }

    private fun c(): MpayClient = client ?: throw IllegalStateException("avval serverga ulaning")

    fun provision(pan: String, expiryYymm: String): ProvisionResult {
        val r = c().provision(pan, expiryYymm)
        if (r is ProvisionResult.Active) save(r.profile)
        return r
    }

    fun verifyOtp(tokenId: String, challengeId: String, otp: String): CardProfile =
        c().verifyOtp(tokenId, challengeId, otp).also { save(it) }

    fun sandboxOtp(challengeId: String, operatorKey: String): String = c().sandboxOtp(challengeId, operatorKey)

    fun replenish(): Int {
        val p = store.load() ?: throw IllegalStateException("token yo'q")
        val luks: List<CardLuk> = c().replenish(p.tokenId)
        p.luks.removeAll { it.usesLeft <= 0 || it.expiresAt <= System.currentTimeMillis() / 1000 }
        p.luks.addAll(luks)
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
