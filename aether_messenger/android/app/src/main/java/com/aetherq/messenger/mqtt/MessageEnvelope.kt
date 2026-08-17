package com.aetherq.messenger.mqtt

import uniffi.aether_ffi.AkemEncapsulation
import java.io.ByteArrayOutputStream

private const val TYPE_HANDSHAKE: Byte = 0x01
private const val TYPE_MESSAGE: Byte = 0x02

private const val USER_ID_LEN = 8
private const val CT_MLKEM_LEN = 1088 // ML-KEM-768 ciphertext — spec 2-bo'lim jadvali, qat'iy o'lcham
private const val CT_X25519_LEN = 32
private const val SIGNATURE_LEN = 64 // Ed25519 — qat'iy o'lcham
private const val COMPRESS_FRAME_LEN = 77 // spec 4.2-bo'lim

sealed class InboundEnvelope {
    data class Handshake(
        val senderUserId: ByteArray,
        val ctMlkem: ByteArray,
        val ctX25519: ByteArray,
        val signature: ByteArray,
    ) : InboundEnvelope()

    data class RatchetMessage(
        val compressFrame: ByteArray,
        val recordFrame: ByteArray,
    ) : InboundEnvelope()
}

/**
 * MQTT payload'ga qadab yuboriladigan, ilova darajasidagi binary frame format.
 * Har bir maydon spec-primitivlaridan kelib chiqqan qat'iy o'lchamga ega bo'lgani
 * uchun (ML-KEM-768 ct, Ed25519 sig, Compress-KEM frame — barchasi belgilangan
 * o'lchamda) uzunlik-prefikslar kerak emas — faqat oxirgi maydon (record ciphertext)
 * o'zgaruvchan uzunlikka ega va "qolgan barcha baytlar" sifatida o'qiladi.
 */
object MessageEnvelope {

    fun encodeHandshake(senderUserId: ByteArray, encaps: AkemEncapsulation): ByteArray {
        require(senderUserId.size == USER_ID_LEN) { "senderUserId $USER_ID_LEN bayt bo'lishi SHART" }
        require(encaps.ctMlkem.size == CT_MLKEM_LEN) { "ct_mlkem kutilmagan uzunlik: ${encaps.ctMlkem.size}" }
        require(encaps.ctX25519.size == CT_X25519_LEN) { "ct_x25519 kutilmagan uzunlik: ${encaps.ctX25519.size}" }
        require(encaps.signature.size == SIGNATURE_LEN) { "signature kutilmagan uzunlik: ${encaps.signature.size}" }

        val out = ByteArrayOutputStream(1 + USER_ID_LEN + CT_MLKEM_LEN + CT_X25519_LEN + SIGNATURE_LEN)
        out.write(TYPE_HANDSHAKE.toInt())
        out.write(senderUserId)
        out.write(encaps.ctMlkem)
        out.write(encaps.ctX25519)
        out.write(encaps.signature)
        return out.toByteArray()
    }

    fun encodeMessage(compressFrame: ByteArray, recordFrame: ByteArray): ByteArray {
        require(compressFrame.size == COMPRESS_FRAME_LEN) { "compress_frame 77 bayt bo'lishi SHART" }
        val out = ByteArrayOutputStream(1 + COMPRESS_FRAME_LEN + recordFrame.size)
        out.write(TYPE_MESSAGE.toInt())
        out.write(compressFrame)
        out.write(recordFrame)
        return out.toByteArray()
    }

    fun decode(payload: ByteArray): InboundEnvelope? {
        if (payload.isEmpty()) return null
        return when (payload[0]) {
            TYPE_HANDSHAKE -> decodeHandshake(payload)
            TYPE_MESSAGE -> decodeMessage(payload)
            else -> null
        }
    }

    private fun decodeHandshake(payload: ByteArray): InboundEnvelope.Handshake? {
        val expected = 1 + USER_ID_LEN + CT_MLKEM_LEN + CT_X25519_LEN + SIGNATURE_LEN
        if (payload.size != expected) return null

        var offset = 1
        val userId = payload.copyOfRange(offset, offset + USER_ID_LEN); offset += USER_ID_LEN
        val ctMlkem = payload.copyOfRange(offset, offset + CT_MLKEM_LEN); offset += CT_MLKEM_LEN
        val ctX25519 = payload.copyOfRange(offset, offset + CT_X25519_LEN); offset += CT_X25519_LEN
        val signature = payload.copyOfRange(offset, offset + SIGNATURE_LEN)
        return InboundEnvelope.Handshake(userId, ctMlkem, ctX25519, signature)
    }

    private fun decodeMessage(payload: ByteArray): InboundEnvelope.RatchetMessage? {
        val minLen = 1 + COMPRESS_FRAME_LEN
        if (payload.size < minLen) return null
        val compressFrame = payload.copyOfRange(1, 1 + COMPRESS_FRAME_LEN)
        val recordFrame = payload.copyOfRange(1 + COMPRESS_FRAME_LEN, payload.size)
        return InboundEnvelope.RatchetMessage(compressFrame, recordFrame)
    }
}
