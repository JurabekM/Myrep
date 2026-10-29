package uz.mpay.wallet.sdk

import android.content.Context
import android.os.PowerManager
import android.os.SystemClock
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import uz.mpay.core.CdcvmGate

/**
 * CDCVM (Consumer Device CVM): `BiometricPrompt` (`BIOMETRIC_STRONG`) dan keyin LUK faqat
 * [windowSeconds] soniya ishlaydi va **ekran yoniq** bo'lishi shart. Tasdiq bir martalik
 * (muvaffaqiyatli GPO'dan keyin tushadi).
 */
class CdcvmState(context: Context, private val windowSeconds: Int = 60) : CdcvmGate {
    private val power = context.applicationContext.getSystemService(Context.POWER_SERVICE) as PowerManager
    @Volatile private var verifiedUntil = 0L

    fun markVerified() {
        verifiedUntil = SystemClock.elapsedRealtime() + windowSeconds * 1000L
    }

    /** Oyna tugashigacha qolgan soniyalar (0 — tasdiq yo'q). */
    fun secondsLeft(): Int = ((verifiedUntil - SystemClock.elapsedRealtime()) / 1000).coerceAtLeast(0).toInt()

    override fun isVerified(): Boolean = power.isInteractive && SystemClock.elapsedRealtime() < verifiedUntil

    override fun consume() {
        verifiedUntil = 0
    }
}

/** BiometricPrompt yordamchisi. */
object BiometricGate {
    fun available(context: Context): Boolean =
        BiometricManager.from(context).canAuthenticate(BIOMETRIC_STRONG) == BiometricManager.BIOMETRIC_SUCCESS

    fun authenticate(activity: FragmentActivity, state: CdcvmState, onResult: (Boolean, String?) -> Unit) {
        val prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    state.markVerified()
                    onResult(true, null)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    onResult(false, errString.toString())
                }
            },
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(activity.getString(R.string.mpay_biometric_title))
            .setSubtitle(activity.getString(R.string.mpay_biometric_subtitle))
            .setNegativeButtonText(activity.getString(R.string.mpay_biometric_cancel))
            .setAllowedAuthenticators(BIOMETRIC_STRONG)
            .build()
        prompt.authenticate(info)
    }
}
