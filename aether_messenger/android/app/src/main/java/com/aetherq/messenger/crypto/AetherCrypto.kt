package com.aetherq.messenger.crypto

import uniffi.aether_ffi.AkemEncapsulation
import uniffi.aether_ffi.CompressFrameResult
import uniffi.aether_ffi.CompressRecipientHandle
import uniffi.aether_ffi.CompressSenderHandle
import uniffi.aether_ffi.KeyPair
import uniffi.aether_ffi.akemDecapsulate as ffiAkemDecapsulate
import uniffi.aether_ffi.akemEncapsulate as ffiAkemEncapsulate
import uniffi.aether_ffi.deriveBytes as ffiDeriveBytes
import uniffi.aether_ffi.generateEd25519Keypair
import uniffi.aether_ffi.generateMlkem768Keypair
import uniffi.aether_ffi.generateRandomBytes
import uniffi.aether_ffi.generateX25519Keypair
import uniffi.aether_ffi.openRecord as ffiOpenRecord
import uniffi.aether_ffi.sealRecord as ffiSealRecord

/**
 * AETHER-Q v4 kripto-yadrosi (Rust/`aether-ffi`) ustidan Kotlin fasadi — bu qatlam
 * JNI/UniFFI chegarasini yashiradi va ilova darajasidagi protokol qarorlarini
 * (ratchet seed derivatsiyasi, profil tanlash) markazlashtiradi.
 */
object AetherCrypto {

    /** Frame'lardagi AAD uchun spec 3-bo'limdagi `profile_id` qiymatlari. */
    const val PROFILE_AUTH_AKEM: UByte = 0x05u
    const val PROFILE_COMPRESS: UByte = 0x04u

    private val LABEL_RATCHET_SEED = "AETHER-Q-MSGR/ratchet-base-seed".toByteArray(Charsets.US_ASCII)
    private val LABEL_SESSION_ID = "AETHER-Q-MSGR/session-id".toByteArray(Charsets.US_ASCII)

    fun generateX25519Identity(): KeyPair = generateX25519Keypair()

    fun generateMlKem768Identity(): KeyPair = generateMlkem768Keypair()

    fun generateEd25519Identity(): KeyPair = generateEd25519Keypair()

    fun randomBytes(len: Int): ByteArray = generateRandomBytes(len.toUInt())

    /**
     * Bitta AUTH-AKEM `shared_secret`dan ikkala tomon mustaqil ravishda bir xil
     * Compress-KEM `base_seed`/`session_id`ni hosil qiladi — alohida uzatishga
     * hojat yo'q (7-bo'limdagi HKDF-Expand mantig'iga mos, SHAKE-256 asosida).
     */
    fun deriveRatchetSeed(sharedSecret: ByteArray): ByteArray = ffiDeriveBytes(sharedSecret, LABEL_RATCHET_SEED, 32u)

    fun deriveSessionId(sharedSecret: ByteArray): ByteArray = ffiDeriveBytes(sharedSecret, LABEL_SESSION_ID, 8u)

    fun akemEncapsulate(
        pkRecipMlkem: ByteArray,
        pkRecipX25519: ByteArray,
        skSenderSign: ByteArray,
        pkSenderSign: ByteArray,
        pkRecipSign: ByteArray,
    ): AkemEncapsulation =
        ffiAkemEncapsulate(pkRecipMlkem, pkRecipX25519, skSenderSign, pkSenderSign, pkRecipSign)

    /** Imzo yaroqsiz bo'lsa ham xato tashlanmaydi — Implicit Rejection qiymati qaytadi. */
    fun akemDecapsulate(
        skRecipMlkem: ByteArray,
        skRecipX25519: ByteArray,
        pkRecipX25519: ByteArray,
        zRecip: ByteArray,
        pkSenderSign: ByteArray,
        pkRecipSign: ByteArray,
        ctMlkem: ByteArray,
        ctX25519: ByteArray,
        signature: ByteArray,
    ): ByteArray =
        ffiAkemDecapsulate(
            skRecipMlkem,
            skRecipX25519,
            pkRecipX25519,
            zRecip,
            pkSenderSign,
            pkRecipSign,
            ctMlkem,
            ctX25519,
            signature,
        )

    fun newCompressSender(sessionId: ByteArray, baseSeed: ByteArray): CompressSenderHandle =
        CompressSenderHandle(sessionId, baseSeed)

    fun newCompressRecipient(sessionId: ByteArray, baseSeed: ByteArray): CompressRecipientHandle =
        CompressRecipientHandle(sessionId, baseSeed)

    /**
     * Har bir xabar — yangi ratchet qadami (yangi mustaqil X25519 DH natijasi) bilan
     * shifrlanadi, shuning uchun AEAD counter har doim `1` bo'lishi xavfsiz: kalit
     * har safar yangi, nonce takrorlanishi faqat bitta kalit ostida muammo tug'diradi.
     */
    fun sealRecord(sharedSecret: ByteArray, sessionId: ByteArray, plaintext: ByteArray): ByteArray =
        ffiSealRecord(PROFILE_COMPRESS, sharedSecret, sessionId, true, 1u, plaintext)

    fun openRecord(sharedSecret: ByteArray, sessionId: ByteArray, frame: ByteArray): ByteArray =
        ffiOpenRecord(PROFILE_COMPRESS, sharedSecret, sessionId, true, frame)
}

/** Bitta ratchet qadamidan olingan (frame, shared_secret) juftligi — qayta eksport. */
typealias RatchetStep = CompressFrameResult
