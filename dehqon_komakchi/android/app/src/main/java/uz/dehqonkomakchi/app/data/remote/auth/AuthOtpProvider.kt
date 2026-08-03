package uz.dehqonkomakchi.app.data.remote.auth

data class OtpRequestResult(val requestId: String, val demoCodeHint: String? = null)
data class OtpVerifyResult(val success: Boolean, val authToken: String?)

/**
 * Phone-number OTP authentication, provider-agnostic. [DemoAuthOtpProvider] simulates the flow
 * fully offline (fixed demo code) so the app is usable with zero SMS provider account. A real
 * implementation would call the backend's `/v1/auth/otp/request` and `/v1/auth/otp/verify`
 * endpoints, which themselves delegate to an SMS gateway (e.g. Eskiz.uz, Play Mobile) — never
 * embed SMS provider keys in the app; they stay server-side only.
 */
interface AuthOtpProvider {
    suspend fun requestOtp(phoneNumber: String): OtpRequestResult
    suspend fun verifyOtp(requestId: String, code: String): OtpVerifyResult
}
