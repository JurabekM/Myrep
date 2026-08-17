package com.aetherq.messenger.data

import com.aetherq.messenger.crypto.AetherCrypto
import com.aetherq.messenger.crypto.toHex
import uniffi.aether_ffi.CompressRecipientHandle
import uniffi.aether_ffi.CompressSenderHandle
import java.util.concurrent.ConcurrentHashMap

/**
 * Bitta kontakt bilan bo'lgan ratchet-seansi — AUTH-AKEM handshake'dan olingan
 * `shared_secret`dan hosil qilingan `session_id`/`base_seed` asosida.
 *
 * PoC chegarasi: bu holat faqat jarayon-ichida (in-memory) saqlanadi — ilova qayta
 * ishga tushganda har bir kontakt uchun handshake avtomatik qayta bajariladi
 * (`README.md`dagi "Ma'lum cheklovlar" bo'limiga qarang).
 */
class ContactSession(
    val sessionId: ByteArray,
    val sender: CompressSenderHandle,
    val recipient: CompressRecipientHandle,
)

/** Har bir kontakt uchun `ContactSession`ni yaratadi va saqlaydi. */
class SessionManager {
    private val sessions = ConcurrentHashMap<String, ContactSession>()

    // MQTT'da barcha kontaktlar bitta inbox topic'iga yozadi (aetherq/msgr/<ownUserId>) —
    // kelgan ratchet-message qaysi kontaktga tegishli ekanligini frame ichidagi
    // session_id orqali aniqlash uchun teskari indeks.
    private val sessionIdIndex = ConcurrentHashMap<String, String>()

    fun sessionFor(contactUserId: String): ContactSession? = sessions[contactUserId]

    fun hasSession(contactUserId: String): Boolean = sessions.containsKey(contactUserId)

    fun contactForSessionId(sessionId: ByteArray): String? = sessionIdIndex[sessionId.toHex()]

    /** AUTH-AKEM handshake natijasidan ratchet-seansini o'rnatadi — ikkala tomon ham
     * o'zining lokal `shared_secret`i bilan mustaqil chaqiradi va bir xil natijaga keladi. */
    fun establishSession(contactUserId: String, sharedSecret: ByteArray): ContactSession {
        val baseSeed = AetherCrypto.deriveRatchetSeed(sharedSecret)
        val sessionId = AetherCrypto.deriveSessionId(sharedSecret)
        val session = ContactSession(
            sessionId = sessionId,
            sender = AetherCrypto.newCompressSender(sessionId, baseSeed),
            recipient = AetherCrypto.newCompressRecipient(sessionId, baseSeed),
        )
        sessions[contactUserId] = session
        sessionIdIndex[sessionId.toHex()] = contactUserId
        return session
    }

    fun clear(contactUserId: String) {
        sessions.remove(contactUserId)?.let { sessionIdIndex.remove(it.sessionId.toHex()) }
    }
}
