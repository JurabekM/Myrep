package com.aetherq.messenger.crypto

/**
 * Bitta qurilma ichida Alice/Bob identity'larini simulyatsiya qilib to'liq
 * AUTH-AKEM + Compress-KEM ratchet + record layer round-trip'ini tekshiradi.
 * Ikkinchi fizik qurilma/hisob yo'qligi sababli JNI chegarasini shu tarzda tasdiqlaymiz.
 */
object SelfTest {
    data class Result(val success: Boolean, val details: String)

    fun run(): Result =
        try {
            val aliceEd = AetherCrypto.generateEd25519Identity()
            val bobEd = AetherCrypto.generateEd25519Identity()
            val bobX = AetherCrypto.generateX25519Identity()
            val bobMlkem = AetherCrypto.generateMlKem768Identity()
            val bobZ = AetherCrypto.randomBytes(32)

            val encaps =
                AetherCrypto.akemEncapsulate(
                    pkRecipMlkem = bobMlkem.publicKey,
                    pkRecipX25519 = bobX.publicKey,
                    skSenderSign = aliceEd.secretKey,
                    pkSenderSign = aliceEd.publicKey,
                    pkRecipSign = bobEd.publicKey,
                )
            val bobSharedSecret =
                AetherCrypto.akemDecapsulate(
                    skRecipMlkem = bobMlkem.secretKey,
                    skRecipX25519 = bobX.secretKey,
                    pkRecipX25519 = bobX.publicKey,
                    zRecip = bobZ,
                    pkSenderSign = aliceEd.publicKey,
                    pkRecipSign = bobEd.publicKey,
                    ctMlkem = encaps.ctMlkem,
                    ctX25519 = encaps.ctX25519,
                    signature = encaps.signature,
                )
            check(encaps.sharedSecret.contentEquals(bobSharedSecret)) { "AKEM shared_secret mos kelmadi" }

            val baseSeed = AetherCrypto.deriveRatchetSeed(encaps.sharedSecret)
            val sessionId = AetherCrypto.deriveSessionId(encaps.sharedSecret)
            val aliceSender = AetherCrypto.newCompressSender(sessionId, baseSeed)
            val bobRecipient = AetherCrypto.newCompressRecipient(sessionId, baseSeed)

            val step = aliceSender.nextFrame(bobX.publicKey)
            check(step.frame.size == 77) { "Compress frame 77 bayt emas: ${step.frame.size}" }
            val bobStepSecret = bobRecipient.acceptFrame(step.frame, bobX.secretKey)
            check(step.sharedSecret.contentEquals(bobStepSecret)) { "Ratchet step shared_secret mos kelmadi" }

            val plaintext = "AETHER-Q self-test xabari".toByteArray(Charsets.UTF_8)
            val recordFrame = AetherCrypto.sealRecord(step.sharedSecret, sessionId, plaintext)
            val decrypted = AetherCrypto.openRecord(bobStepSecret, sessionId, recordFrame)
            check(decrypted.contentEquals(plaintext)) { "Record layer roundtrip mos kelmadi" }

            Result(true, "AUTH-AKEM + Compress-KEM ratchet + Record layer — barchasi JNI orqali muvaffaqiyatli o'tdi.")
        } catch (e: Exception) {
            Result(false, "Xato: ${e.message}")
        }
}
