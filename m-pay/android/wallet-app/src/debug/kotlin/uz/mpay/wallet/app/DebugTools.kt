package uz.mpay.wallet.app

import android.content.Context
import android.content.Intent

/** Faqat debug build: emulyator sinovi vositalari (release'da no-op nusxa — `src/release`). */
object DebugTools {
    const val ENABLED = true

    /** Virtual NFC ko'prigi ([VirtualNfcService]). */
    fun startVirtualNfc(context: Context): Boolean =
        runCatching { context.startForegroundService(Intent(context, VirtualNfcService::class.java)) }.isSuccess
}
