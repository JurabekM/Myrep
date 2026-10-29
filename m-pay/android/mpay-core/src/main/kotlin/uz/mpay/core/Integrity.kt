package uz.mpay.core

import java.security.MessageDigest
import java.util.Base64

/**
 * Ilova yaxlitligi (2-faza P2.6, ADR-0021) — Rust `mpay_integrity::request_hash` bilan bayt-bir xil.
 *
 * `requestHash = base64url(SHA-256("MPAY-PI-V1" ‖ 0x00 ‖ amal ‖ 0x00 ‖ sessiya ID))`, paddingsiz.
 * Play Integrity standart so'roviga `requestHash` sifatida beriladi; PAN kirmaydi (u Google'ga ketadi).
 */
object Integrity {
    const val PURPOSE_PROVISION = "provision"

    fun requestHash(purpose: String, sessionId: ByteArray): String {
        val md = MessageDigest.getInstance("SHA-256")
        md.update("MPAY-PI-V1".toByteArray(Charsets.US_ASCII))
        md.update(0)
        md.update(purpose.toByteArray(Charsets.US_ASCII))
        md.update(0)
        md.update(sessionId)
        return Base64.getUrlEncoder().withoutPadding().encodeToString(md.digest())
    }
}
