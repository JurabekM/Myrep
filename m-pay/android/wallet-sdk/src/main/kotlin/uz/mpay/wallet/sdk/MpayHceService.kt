package uz.mpay.wallet.sdk

import android.nfc.cardemulation.HostApduService
import android.os.Bundle

/**
 * HCE servisi: terminal APDU'larini [MpayWallet.applet] ga uzatadi (`emv-profile.md` §2).
 * Ekran yoniq bo'lishi va CDCVM oynasi applet ichida ([CdcvmState]) tekshiriladi.
 */
class MpayHceService : HostApduService() {
    override fun processCommandApdu(commandApdu: ByteArray, extras: Bundle?): ByteArray =
        MpayWallet.get(this).applet.process(commandApdu)

    override fun onDeactivated(reason: Int) {
        MpayWallet.get(this).applet.reset()
    }
}
