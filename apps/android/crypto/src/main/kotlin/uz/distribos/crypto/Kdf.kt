package uz.distribos.crypto

import org.bouncycastle.crypto.digests.SHA3Digest
import org.bouncycastle.crypto.digests.SHAKEDigest
import org.bouncycastle.crypto.macs.HMac
import org.bouncycastle.crypto.params.KeyParameter

/**
 * AETHER-Q v5.1 KDF yadrosi — Kotlin tomoni.
 *
 * Python `aetherq/kdf.py` bilan **baytma-bayt** bir xil natija berishi
 * SHART: HKDF-SHA3-256 (RFC 5869), KMAC256 va cSHAKE256 (SP 800-185).
 *
 * ## Nega platforma emas, BouncyCastle
 *
 * `MessageDigest.getInstance("SHA3-256")` Android'da faqat API 28 dan,
 * `Mac.getInstance("HmacSHA3-256")` esa umuman kafolatlanmagan; SHAKE256
 * platformada YO'Q. Ya'ni platformaga tayansak:
 *
 * * minSdk 28 ga ko'tarilardi — O'zbekiston bozorida Android 8 qurilmalar
 *   hali ham ko'p;
 * * xulq qurilmadan qurilmaga farq qilishi mumkin edi.
 *
 * BouncyCastle bitta implementatsiyani beradi va u JVM testida ham,
 * telefonda ham AYNAN bir xil ishlaydi. Kriptografiyada bu muhimroq.
 */
object Kdf {

    fun sha3_256(data: ByteArray): ByteArray {
        val digest = SHA3Digest(256)
        digest.update(data, 0, data.size)
        return ByteArray(digest.digestSize).also { digest.doFinal(it, 0) }
    }

    fun shake256(data: ByteArray, length: Int): ByteArray {
        val digest = SHAKEDigest(256)
        digest.update(data, 0, data.size)
        return ByteArray(length).also { digest.doFinal(it, 0, length) }
    }

    /** PRK = HMAC-SHA3-256(salt, ikm). Bo'sh salt -> 32 bayt nol. */
    fun hkdfExtract(salt: ByteArray, ikm: ByteArray): ByteArray {
        val key = if (salt.isEmpty()) ByteArray(32) else salt
        return hmacSha3(key, ikm)
    }

    /** RFC 5869 Expand, SHA3-256 bilan. */
    fun hkdfExpand(prk: ByteArray, info: ByteArray, length: Int): ByteArray {
        require(length <= 255 * 32) { "HKDF-Expand: length juda katta" }
        val mac = HMac(SHA3Digest(256))
        mac.init(KeyParameter(prk))

        var block = ByteArray(0)
        val output = ByteArray(length)
        var produced = 0
        var counter = 1
        while (produced < length) {
            mac.reset()
            mac.update(block, 0, block.size)
            mac.update(info, 0, info.size)
            mac.update(counter.toByte())
            block = ByteArray(mac.macSize).also { mac.doFinal(it, 0) }
            val take = minOf(block.size, length - produced)
            block.copyInto(output, produced, 0, take)
            produced += take
            counter++
        }
        return output
    }

    private fun hmacSha3(key: ByteArray, data: ByteArray): ByteArray {
        val mac = HMac(SHA3Digest(256))
        mac.init(KeyParameter(key))
        mac.update(data, 0, data.size)
        return ByteArray(mac.macSize).also { mac.doFinal(it, 0) }
    }

    // --- SP 800-185 yordamchilari ----------------------------------------

    internal fun leftEncode(value: Int): ByteArray {
        if (value == 0) return byteArrayOf(1, 0)
        var remaining = value
        val bytes = ArrayDeque<Byte>()
        while (remaining > 0) {
            bytes.addFirst((remaining and 0xFF).toByte())
            remaining = remaining ushr 8
        }
        return byteArrayOf(bytes.size.toByte()) + bytes.toByteArray()
    }

    internal fun rightEncode(value: Int): ByteArray {
        if (value == 0) return byteArrayOf(0, 1)
        var remaining = value
        val bytes = ArrayDeque<Byte>()
        while (remaining > 0) {
            bytes.addFirst((remaining and 0xFF).toByte())
            remaining = remaining ushr 8
        }
        return bytes.toByteArray() + byteArrayOf(bytes.size.toByte())
    }

    internal fun encodeString(data: ByteArray): ByteArray =
        leftEncode(data.size * 8) + data

    internal fun bytepad(data: ByteArray, width: Int): ByteArray {
        val prefixed = leftEncode(width) + data
        val remainder = prefixed.size % width
        return if (remainder == 0) prefixed else prefixed + ByteArray(width - remainder)
    }

    /** cSHAKE256 (SP 800-185). name/custom bo'sh bo'lsa -> oddiy SHAKE256. */
    fun cshake256(
        data: ByteArray,
        length: Int,
        name: ByteArray = ByteArray(0),
        custom: ByteArray = ByteArray(0),
    ): ByteArray {
        if (name.isEmpty() && custom.isEmpty()) return shake256(data, length)
        val prefix = bytepad(encodeString(name) + encodeString(custom), 136)
        return shake256(prefix + data, length)
    }

    /** KMAC256 (SP 800-185). */
    fun kmac256(
        key: ByteArray,
        data: ByteArray,
        length: Int,
        custom: ByteArray = ByteArray(0),
    ): ByteArray {
        val newX = bytepad(encodeString(key), 136) + data + rightEncode(length * 8)
        return cshake256(newX, length, "KMAC".toByteArray(Charsets.US_ASCII), custom)
    }

    /**
     * Constant-time tenglik.
     *
     * `contentEquals` birinchi farqda TO'XTAYDI — bu timing orqali sirni
     * sizdiradi. Bu yerda hamma baytlar doim ko'riladi.
     */
    fun constantTimeEquals(a: ByteArray, b: ByteArray): Boolean {
        if (a.size != b.size) return false
        var difference = 0
        for (index in a.indices) {
            difference = difference or (a[index].toInt() xor b[index].toInt())
        }
        return difference == 0
    }
}
