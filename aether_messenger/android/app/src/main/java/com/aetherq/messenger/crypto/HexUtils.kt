package com.aetherq.messenger.crypto

/** Baytlarni hex-satrga o'girish — identity/kontakt kalitlarini matn shaklida saqlash uchun. */
fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

fun hexToBytes(hex: String): ByteArray =
    ByteArray(hex.length / 2) { i ->
        ((Character.digit(hex[i * 2], 16) shl 4) + Character.digit(hex[i * 2 + 1], 16)).toByte()
    }
