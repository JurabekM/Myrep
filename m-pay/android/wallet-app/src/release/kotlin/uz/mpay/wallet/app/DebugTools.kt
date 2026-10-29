package uz.mpay.wallet.app

import android.content.Context

/** Release: sinov vositalari yo'q — virtual NFC ko'prigi sinfi ham, uning nomi ham APK'ga kirmaydi. */
object DebugTools {
    const val ENABLED = false

    fun startVirtualNfc(@Suppress("UNUSED_PARAMETER") context: Context): Boolean = false
}
