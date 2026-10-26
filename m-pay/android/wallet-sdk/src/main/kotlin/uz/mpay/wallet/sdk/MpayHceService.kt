package uz.mpay.wallet.sdk

import android.content.Context
import android.nfc.cardemulation.HostApduService
import android.os.Bundle

/**
 * HCE APDU ishlovchisi. NFC servisi ([MpayHceService]) va sandbox sinov ko'prigi (wallet-demo debug
 * build'idagi virtual NFC) **bir xil** yo'ldan o'tadi: [MpayWallet.applet] (CDCVM, LUK, ATC).
 */
object HceDispatcher {
    fun process(context: Context, commandApdu: ByteArray): ByteArray =
        MpayWallet.get(context).applet.process(commandApdu)

    /** Maydon yo'qoldi (telefon uzoqlashdi) — applet holati tozalanadi. */
    fun deactivated(context: Context) {
        MpayWallet.get(context).applet.reset()
    }
}

/**
 * HCE servisi: terminal APDU'larini [HceDispatcher] ga uzatadi (`emv-profile.md` §2).
 * Ekran yoniq bo'lishi va CDCVM oynasi applet ichida ([CdcvmState]) tekshiriladi.
 */
class MpayHceService : HostApduService() {
    override fun processCommandApdu(commandApdu: ByteArray, extras: Bundle?): ByteArray =
        HceDispatcher.process(this, commandApdu)

    override fun onDeactivated(reason: Int) {
        HceDispatcher.deactivated(this)
    }
}
