package uz.barakadaftari.app.native

import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/**
 * JVM testlarida Android Keystore yo'q — o'rniga dasturiy AES-256 kalit.
 * Wrap/unwrap mantig'i va fayl formati aynan bir xil.
 */
fun softwareAesKey(): SecretKey = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

fun ByteArray.hex(): String = joinToString("") { "%02x".format(it) }

fun hexBytes(hex: String): ByteArray =
    hex.replace(" ", "").chunked(2).map { it.toInt(16).toByte() }.toByteArray()
