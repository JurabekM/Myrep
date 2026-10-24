package uz.barakadaftari.app.native

import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.DEVICE_CREDENTIAL
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

/** BiometricPrompt o'rami: BIOMETRIC_STRONG yoki qurilma krediensiali. */
class BiometricAuthenticator(private val activityProvider: () -> FragmentActivity?) {

    /**
     * API 30+ da biometriya yoki qurilma krediensiali birga ruxsat etiladi.
     * API 26–29 da bu kombinatsiya qo'llanmaydi — faqat BIOMETRIC_STRONG.
     */
    private val authenticators: Int =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) BIOMETRIC_STRONG or DEVICE_CREDENTIAL
        else BIOMETRIC_STRONG

    fun availability(): BiometricAvailability {
        val activity = activityProvider() ?: return BiometricAvailability.UNAVAILABLE
        return when (BiometricManager.from(activity).canAuthenticate(authenticators)) {
            BiometricManager.BIOMETRIC_SUCCESS -> BiometricAvailability.AVAILABLE
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> BiometricAvailability.NONE_ENROLLED
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> BiometricAvailability.NO_HARDWARE
            else -> BiometricAvailability.UNAVAILABLE
        }
    }

    fun authenticate(
        title: String,
        subtitle: String,
        cancelLabel: String,
        callback: (Result<BiometricOutcome>) -> Unit,
    ) {
        val activity = activityProvider()
        if (activity == null || availability() != BiometricAvailability.AVAILABLE) {
            callback(Result.success(BiometricOutcome.UNAVAILABLE))
            return
        }
        var done = false
        fun finish(outcome: BiometricOutcome) {
            if (done) return
            done = true
            callback(Result.success(outcome))
        }

        val prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) =
                    finish(BiometricOutcome.SUCCESS)

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) =
                    finish(mapError(errorCode))

                // Bitta muvaffaqiyatsiz urinish — prompt ochiq qoladi, natija hali yo'q.
                override fun onAuthenticationFailed() = Unit
            },
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setAllowedAuthenticators(authenticators)
            .apply { if (authenticators and DEVICE_CREDENTIAL == 0) setNegativeButtonText(cancelLabel) }
            .build()
        activity.runOnUiThread { prompt.authenticate(info) }
    }

    companion object {
        fun mapError(code: Int): BiometricOutcome = when (code) {
            BiometricPrompt.ERROR_USER_CANCELED,
            BiometricPrompt.ERROR_NEGATIVE_BUTTON,
            BiometricPrompt.ERROR_CANCELED,
            -> BiometricOutcome.CANCELLED
            BiometricPrompt.ERROR_LOCKOUT,
            BiometricPrompt.ERROR_LOCKOUT_PERMANENT,
            -> BiometricOutcome.LOCKED_OUT
            BiometricPrompt.ERROR_HW_NOT_PRESENT,
            BiometricPrompt.ERROR_HW_UNAVAILABLE,
            BiometricPrompt.ERROR_NO_BIOMETRICS,
            BiometricPrompt.ERROR_NO_DEVICE_CREDENTIAL,
            -> BiometricOutcome.UNAVAILABLE
            else -> BiometricOutcome.FAILED
        }
    }
}
