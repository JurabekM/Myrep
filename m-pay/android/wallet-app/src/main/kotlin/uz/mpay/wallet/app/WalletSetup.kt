package uz.mpay.wallet.app

import android.content.Context
import uz.mpay.core.Hex
import uz.mpay.core.ServerPinPolicy
import uz.mpay.wallet.sdk.IntegrityTokenProvider
import uz.mpay.wallet.sdk.MpayWallet
import uz.mpay.wallet.sdk.WalletConfig

/**
 * SDK sozlamasi (Activity va fon xizmati uchun bir xil): server ishonchi build vaqtida (P1.5, ADR-0029),
 * sandbox'da yaxlitlik tokeni server mock'idan. Ulanish dangasa — birinchi tarmoq chaqiruvida.
 */
object WalletSetup {
    @Volatile private var configured = false
    private val lock = Any()

    fun wallet(context: Context): MpayWallet {
        val w = MpayWallet.get(context)
        if (!configured) synchronized(lock) {
            if (!configured) {
                val pins = ServerPinPolicy.parseList(BuildConfig.SERVER_FINGERPRINTS)
                w.config = WalletConfig(
                    pinnedFingerprints = pins,
                    tlsCertSha256 = BuildConfig.TLS_PIN.takeIf { it.isNotEmpty() }?.let(Hex::decode),
                    // TOFU faqat sandbox build'ida va pin berilmaganda.
                    allowTofu = BuildConfig.SANDBOX && pins.isEmpty(),
                    rootFingerprint = BuildConfig.ROOT_FINGERPRINT.takeIf { it.isNotEmpty() },
                    bundledRevocations = runCatching {
                        context.assets.open("mpay-revocations.json").bufferedReader().use { it.readText() }
                    }.getOrNull(),
                    revocationUrls = BuildConfig.REVOCATION_URLS.split(',').map { it.trim() }.filter { it.isNotEmpty() },
                )
                // TODO(spec): production'da Play Integrity (MB-4); sandbox'da — server mock'i o'z PQ Link sessiyasi orqali.
                w.integrityProvider = if (BuildConfig.SANDBOX) IntegrityTokenProvider { w.sandboxDeviceIntegrityToken() } else null
                configured = true
            }
        }
        return w
    }

    /** Ulangan bo'lmasa — ulanadi (bloklovchi, fon oqimida). */
    @Synchronized
    fun connected(context: Context): MpayWallet {
        val w = wallet(context)
        if (!w.isConnected) w.connect(BuildConfig.SERVER)
        return w
    }

    /**
     * Tarmoq chaqiruvi: sessiya eskirgan bo'lsa (`PQLINK_SESSION`) bir marta qayta ulanib takrorlaydi.
     * Sinxron: UI va fon sinxronlashi bitta PQ Link sessiyasini baham ko'radi (yozuvlar ketma-ketligi buzilmasin).
     */
    @Synchronized
    fun <T> call(context: Context, block: (MpayWallet) -> T): T {
        val w = connected(context)
        return try {
            block(w)
        } catch (e: uz.mpay.core.ApiException) {
            if (e.code != "PQLINK_SESSION" && e.code != "NOT_CONNECTED") throw e
            w.connect(BuildConfig.SERVER)
            block(w)
        }
    }
}
