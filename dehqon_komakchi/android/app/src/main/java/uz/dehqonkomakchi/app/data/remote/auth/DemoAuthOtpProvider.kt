package uz.dehqonkomakchi.app.data.remote.auth

import kotlinx.coroutines.delay
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/** Demo-mode OTP: always "sends" code 123456 and accepts it. Clearly labeled, no real SMS sent. */
@Singleton
class DemoAuthOtpProvider @Inject constructor() : AuthOtpProvider {

    private val pendingRequests = mutableMapOf<String, String>()

    override suspend fun requestOtp(phoneNumber: String): OtpRequestResult {
        delay(400)
        val requestId = UUID.randomUUID().toString()
        pendingRequests[requestId] = DEMO_CODE
        return OtpRequestResult(requestId = requestId, demoCodeHint = "Demo rejim: kod $DEMO_CODE")
    }

    override suspend fun verifyOtp(requestId: String, code: String): OtpVerifyResult {
        delay(300)
        val expected = pendingRequests[requestId]
        return if (expected != null && expected == code) {
            OtpVerifyResult(success = true, authToken = "demo-token-${UUID.randomUUID()}")
        } else {
            OtpVerifyResult(success = false, authToken = null)
        }
    }

    companion object {
        const val DEMO_CODE = "123456"
    }
}
