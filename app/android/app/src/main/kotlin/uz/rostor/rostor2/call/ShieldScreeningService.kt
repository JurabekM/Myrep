package uz.rostor.rostor2.call

import android.os.Build
import android.telecom.Call
import android.telecom.CallScreeningService
import android.telecom.TelecomManager
import java.util.concurrent.Executors

/**
 * Tizim har kiruvchi qo'ng'iroqda chaqiradigan xizmat (faqat ROSTOR-2 "qo'ng'iroqlarni saralash"
 * roliga ega bo'lsa, Android 10+). Fon xizmati emas (Q4): tizim uni qo'ng'iroq vaqtida o'zi bog'laydi.
 * Javob 5 soniya ichida berilishi shart, shuning uchun xato bo'lsa ham qo'ng'iroq o'tkazib yuboriladi.
 */
class ShieldScreeningService : CallScreeningService() {
    private val io = Executors.newSingleThreadExecutor()

    override fun onScreenCall(details: Call.Details) {
        io.execute {
            var responded = false
            try {
                if (Build.VERSION.SDK_INT >= 29 && details.callDirection != Call.Details.DIRECTION_INCOMING) {
                    respondToCall(details, CallResponse.Builder().build())
                    responded = true
                    return@execute
                }
                val hidden = details.handle == null || details.handlePresentation != TelecomManager.PRESENTATION_ALLOWED
                val verification = if (Build.VERSION.SDK_INT >= 30) details.callerNumberVerificationStatus else PhoneRules.VERIFY_NONE
                val v = CallShield.screen(this, details.handle?.schemeSpecificPart, hidden, verification)
                val resp = CallResponse.Builder()
                if (v.block) {
                    resp.setDisallowCall(true).setRejectCall(true).setSkipCallLog(false).setSkipNotification(false)
                } else if (v.silence && Build.VERSION.SDK_INT >= 29) {
                    resp.setSilenceCall(true)
                }
                respondToCall(details, resp.build())
                responded = true
                CallShield.after(this, v)
            } catch (e: Throwable) {
                if (!responded) try { respondToCall(details, CallResponse.Builder().build()) } catch (_: Throwable) {}
            }
        }
    }

    override fun onDestroy() {
        io.shutdown()
        super.onDestroy()
    }
}
