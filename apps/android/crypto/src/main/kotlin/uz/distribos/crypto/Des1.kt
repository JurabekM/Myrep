package uz.distribos.crypto

import org.bouncycastle.crypto.modes.ChaCha20Poly1305
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.KeyParameter
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.SecureRandom

/**
 * DES-1 kodek — `specs/distribos-event-seal/DES-1.md` ning Kotlin tomoni.
 *
 * ## Baytma-bayt moslik SHART
 *
 * Bu implementatsiya Python `distribos/aether_q/des1.py` bilan **aynan bir
 * xil** baytlarni ishlab chiqarishi kerak. Buni `Des1KatTest` umumiy KAT
 * fayli ustida tekshiradi: Python yozgan envelope Kotlin tomonidan
 * ochiladi va aksincha.
 *
 * ## Nima uchun AETHER-Q record qatlami emas
 *
 * AETHER-Q §8 record qatlami sessiyaviy: monotonik `seq`, tartib buzilsa
 * fatal. MQTT esa dublikat/tartibsiz. Batafsil: `docs/adr/0001`.
 *
 * ⚠ DES-1 AETHER-Q spetsifikatsiyasining qismi EMAS — u AETHER-Q
 * primitivlari ustidagi DistribOS konstruksiyasi.
 */
object Des1 {
    const val VERSION = 0x0001
    const val HEADER_SIZE = 66
    const val SIGNATURE_SIZE = 3309      // ML-DSA-65
    const val AEAD_TAG_SIZE = 16
    const val TENANT_TAG_SIZE = 16
    const val DEVICE_ID_SIZE = 16
    const val SEQ_SIZE = 12
    const val RAND_SIZE = 6

    const val MIN_ENVELOPE_SIZE = HEADER_SIZE + AEAD_TAG_SIZE + SIGNATURE_SIZE

    /**
     * Muhrni OCHMASDAN yuboruvchini o'qiydi.
     *
     * Header ochiq matn — bu arzon. Qiymat hali AUTENTIFIKATSIYALANMAGAN,
     * shuning uchun unga qaror bog'lash mumkin emas. Yagona ruxsat
     * etilgan foydalanish: o'z aks-sadomizni tashlab yuborish.
     *
     * Nega kerak: aks-sado ochilganda replay oynasi uni HUJUM deb qayd
     * etadi. Jonli sinovda 3 daqiqada 83 ta soxta «replay» yozuvi
     * to'plandi va haqiqiy hujum ular ichida ko'rinmay qolardi.
     */
    fun peekSenderDeviceId(wire: ByteArray): ByteArray? =
        if (wire.size < HEADER_SIZE) null else wire.copyOfRange(32, 48)

    val LABEL: ByteArray = "DistribOS-DES-1/AETHER-Q-v5.1/v1".toByteArray(Charsets.US_ASCII)
    val SIG_CONTEXT: ByteArray = "DES1/sig/v1".toByteArray(Charsets.US_ASCII)

    const val PROFILE_HYBRID = 0x01
    const val PROFILE_MINIMAL = 0x03

    private val random = SecureRandom()

    fun randomBytes(size: Int): ByteArray = ByteArray(size).also(random::nextBytes)
}

/** Envelope shakli buzilgan. Sabab tarmoqqa CHIQMAYDI. */
class Des1FormatException(message: String) : Exception(message)

/** DES-1 `content_type`. */
enum class ContentType(val code: Int) {
    EVENT_BATCH(1),
    ACK(2),
    SYNC_DIGEST(3),
    SYNC_REQUEST(4),
    SNAPSHOT_MANIFEST(5),
    SNAPSHOT_CHUNK(6),
    DEVICE_STATUS(7),
    REVOCATION(8),
    PROTOCOL_CONTROL(9);

    companion object {
        fun from(code: Int): ContentType =
            entries.firstOrNull { it.code == code }
                ?: throw Des1FormatException("noma'lum content_type: $code")
    }
}

/** Nega ochilmadi. FAQAT lokal log uchun — tarmoqqa qaytarilmaydi. */
enum class RejectReason {
    MALFORMED, UNKNOWN_VERSION, UNSUPPORTED_PROFILE, UNKNOWN_EPOCH, UNKNOWN_KEY,
    FOREIGN_TENANT, UNKNOWN_SENDER, REVOKED_SENDER, BAD_SIGNATURE, REPLAY,
    AEAD_FAILURE, SCHEMA_INVALID, TOO_LARGE, STALE,
}

class AetherQException(val reason: RejectReason, detail: String = "") :
    Exception(if (detail.isEmpty()) reason.name else "${reason.name}: $detail")

/**
 * Bitta `(epoch, key_id)` uchun ajratilgan kalitlar.
 *
 * `toString()` ATAYLAB qayta yozilgan: maxfiy material log'ga tushmasin.
 */
class EpochKeys(
    val epoch: Int,
    val keyId: Long,
    val aeadKey: ByteArray,
    val aeadIv: ByteArray,
    val tenantTag: ByteArray,
) {
    override fun toString(): String = "EpochKeys(epoch=$epoch, keyId=$keyId, <secrets hidden>)"
}

/** Ochiq header. AAD sifatida to'liq autentifikatsiyalanadi. */
data class Des1Header(
    val version: Int,
    val profileId: Int,
    val contentType: Int,
    val epoch: Int,
    val keyId: Long,
    val tenantTag: ByteArray,
    val senderDeviceId: ByteArray,
    val sequence: Long,
    val rand: ByteArray,
) {
    fun pack(): ByteArray {
        require(tenantTag.size == Des1.TENANT_TAG_SIZE) { "tenant_tag 16 bayt bo'lishi kerak" }
        require(senderDeviceId.size == Des1.DEVICE_ID_SIZE) { "device_id 16 bayt bo'lishi kerak" }
        require(rand.size == Des1.RAND_SIZE) { "rand 6 bayt bo'lishi kerak" }
        require(sequence >= 0) { "sequence manfiy bo'lishi mumkin emas" }

        val buffer = ByteBuffer.allocate(Des1.HEADER_SIZE).order(ByteOrder.BIG_ENDIAN)
        buffer.putShort(version.toShort())
        buffer.put(profileId.toByte())
        buffer.put(contentType.toByte())
        buffer.putInt(epoch)
        buffer.putLong(keyId)
        buffer.put(tenantTag)
        buffer.put(senderDeviceId)
        // `seq` LITTLE-endian (AETHER-Q §8.2 nonce konvensiyasi bilan bir xil).
        buffer.put(longToLe(sequence, Des1.SEQ_SIZE))
        buffer.put(rand)
        return buffer.array()
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Des1Header) return false
        return version == other.version && profileId == other.profileId &&
            contentType == other.contentType && epoch == other.epoch &&
            keyId == other.keyId && sequence == other.sequence &&
            tenantTag.contentEquals(other.tenantTag) &&
            senderDeviceId.contentEquals(other.senderDeviceId) &&
            rand.contentEquals(other.rand)
    }

    override fun hashCode(): Int {
        var result = version
        result = 31 * result + profileId
        result = 31 * result + contentType
        result = 31 * result + epoch
        result = 31 * result + keyId.hashCode()
        result = 31 * result + sequence.hashCode()
        result = 31 * result + tenantTag.contentHashCode()
        result = 31 * result + senderDeviceId.contentHashCode()
        return result
    }

    companion object {
        fun unpack(raw: ByteArray): Des1Header {
            if (raw.size < Des1.HEADER_SIZE) throw Des1FormatException("header qisqa")
            val buffer = ByteBuffer.wrap(raw, 0, Des1.HEADER_SIZE).order(ByteOrder.BIG_ENDIAN)
            val version = buffer.short.toInt() and 0xFFFF
            val profileId = buffer.get().toInt() and 0xFF
            val contentType = buffer.get().toInt() and 0xFF
            val epoch = buffer.int
            val keyId = buffer.long
            val tenantTag = ByteArray(Des1.TENANT_TAG_SIZE).also(buffer::get)
            val deviceId = ByteArray(Des1.DEVICE_ID_SIZE).also(buffer::get)
            val seqBytes = ByteArray(Des1.SEQ_SIZE).also(buffer::get)
            val rand = ByteArray(Des1.RAND_SIZE).also(buffer::get)
            return Des1Header(
                version, profileId, contentType, epoch, keyId,
                tenantTag, deviceId, leToLong(seqBytes), rand,
            )
        }
    }
}

/** Ajratilgan, lekin hali tekshirilmagan envelope qismlari. */
data class Des1Parts(
    val header: Des1Header,
    val packedHeader: ByteArray,
    val ciphertext: ByteArray,
    val signature: ByteArray,
)

object Des1Codec {

    /**
     * DES-1 kalit ajratish — AETHER-Q §4 combiner qoidalariga muvofiq.
     *
     * `profileId` va to'liq transcript har KDF'ga bind qilinadi (N1, S5):
     * 0x01 dan 0x03 ga downgrade kalitni o'zgartiradi va xabar ochilmaydi.
     */
    fun deriveEpochKeys(
        epochRootSecret: ByteArray,
        tenantId: ByteArray,
        epoch: Int,
        keyId: Long,
        profileId: Int,
    ): EpochKeys {
        require(epochRootSecret.size == 32) { "epoch_root_secret 32 bayt bo'lishi kerak" }

        val suffix = ByteBuffer.allocate(12).order(ByteOrder.BIG_ENDIAN)
            .putInt(epoch).putLong(keyId).array()
        val transcript = Kdf.sha3_256(
            byteArrayOf(profileId.toByte()) + Des1.LABEL + tenantId + suffix
        )
        val prk = Kdf.hkdfExtract(transcript, epochRootSecret)
        val aeadKey = Kdf.hkdfExpand(prk, Des1.LABEL + "/aead-key".toByteArray(), 32)
        val aeadIv = Kdf.hkdfExpand(prk, Des1.LABEL + "/aead-iv".toByteArray(), 12)
        val tagKey = Kdf.hkdfExpand(prk, Des1.LABEL + "/tenant-tag".toByteArray(), 32)
        val tenantTag = Kdf.kmac256(
            tagKey, tenantId, 32, "DES1/tenant".toByteArray(Charsets.US_ASCII)
        ).copyOf(Des1.TENANT_TAG_SIZE)
        return EpochKeys(epoch, keyId, aeadKey, aeadIv, tenantTag)
    }

    /** Envelope quradi: header + ciphertext + signature. */
    fun seal(
        plaintext: ByteArray,
        header: Des1Header,
        keys: EpochKeys,
        signer: (ByteArray) -> ByteArray,
    ): ByteArray {
        if (header.epoch != keys.epoch || header.keyId != keys.keyId) {
            throw Des1FormatException("header epoch/key_id kalitlarga mos emas")
        }
        val packed = header.pack()
        val ciphertext = aeadEncrypt(keys.aeadKey, nonce(header.sequence, keys.aeadIv), plaintext, packed)
        val signature = signer(signedBytes(packed, ciphertext))
        if (signature.size != Des1.SIGNATURE_SIZE) {
            throw Des1FormatException("kutilmagan imzo uzunligi: ${signature.size}")
        }
        return packed + ciphertext + signature
    }

    /** Envelope'ni qismlarga ajratadi. Kriptografik tekshiruv QILMAYDI. */
    fun split(wire: ByteArray): Des1Parts {
        if (wire.size < Des1.MIN_ENVELOPE_SIZE) {
            throw Des1FormatException("envelope juda qisqa: ${wire.size}")
        }
        val packed = wire.copyOfRange(0, Des1.HEADER_SIZE)
        val ciphertext = wire.copyOfRange(Des1.HEADER_SIZE, wire.size - Des1.SIGNATURE_SIZE)
        val signature = wire.copyOfRange(wire.size - Des1.SIGNATURE_SIZE, wire.size)
        if (ciphertext.size < Des1.AEAD_TAG_SIZE) {
            throw Des1FormatException("ciphertext tag'siz")
        }
        return Des1Parts(Des1Header.unpack(packed), packed, ciphertext, signature)
    }

    /** AEAD ochadi. Tag xato bo'lsa batafsilsiz xato (N15 oracle himoyasi). */
    fun openAead(header: Des1Header, ciphertext: ByteArray, keys: EpochKeys): ByteArray =
        try {
            aeadDecrypt(keys.aeadKey, nonce(header.sequence, keys.aeadIv), ciphertext, header.pack())
        } catch (_: Exception) {
            throw Des1FormatException("AEAD ochilmadi")
        }

    /** Constant-time tenant tekshiruvi. */
    fun tenantTagMatches(header: Des1Header, keys: EpochKeys): Boolean =
        Kdf.constantTimeEquals(header.tenantTag, keys.tenantTag)

    /** Imzo ostidagi baytlar: kontekst + header + SHA3-256(ciphertext). */
    fun signedBytes(packedHeader: ByteArray, ciphertext: ByteArray): ByteArray =
        Des1.SIG_CONTEXT + packedHeader + Kdf.sha3_256(ciphertext)

    /** nonce = seq XOR IV_ep (little-endian, 96 bit). */
    internal fun nonce(sequence: Long, iv: ByteArray): ByteArray {
        val seqBytes = longToLe(sequence, 12)
        return ByteArray(12) { index -> (seqBytes[index].toInt() xor iv[index].toInt()).toByte() }
    }

    // AEAD ham BouncyCastle orqali — platformadagi ChaCha20-Poly1305
    // Android'da faqat API 28 dan mavjud (Kdf.kt izohiga qarang).
    private fun aeadProcess(
        forEncryption: Boolean, key: ByteArray, nonce: ByteArray,
        input: ByteArray, aad: ByteArray,
    ): ByteArray {
        val engine = ChaCha20Poly1305()
        engine.init(forEncryption, AEADParameters(KeyParameter(key), 128, nonce, aad))
        val output = ByteArray(engine.getOutputSize(input.size))
        var written = engine.processBytes(input, 0, input.size, output, 0)
        written += engine.doFinal(output, written)
        return if (written == output.size) output else output.copyOf(written)
    }

    private fun aeadEncrypt(
        key: ByteArray, nonce: ByteArray, plaintext: ByteArray, aad: ByteArray,
    ): ByteArray = aeadProcess(true, key, nonce, plaintext, aad)

    private fun aeadDecrypt(
        key: ByteArray, nonce: ByteArray, ciphertext: ByteArray, aad: ByteArray,
    ): ByteArray = aeadProcess(false, key, nonce, ciphertext, aad)
}

// --- kichik yordamchilar --------------------------------------------------

/** Songa little-endian ko'rinish (Python `int.to_bytes(n, "little")` bilan bir xil). */
internal fun longToLe(value: Long, size: Int): ByteArray {
    val out = ByteArray(size)
    var remaining = value
    for (index in 0 until minOf(size, 8)) {
        out[index] = (remaining and 0xFF).toByte()
        remaining = remaining ushr 8
    }
    return out
}

internal fun leToLong(bytes: ByteArray): Long {
    var value = 0L
    for (index in minOf(bytes.size, 8) - 1 downTo 0) {
        value = (value shl 8) or (bytes[index].toLong() and 0xFF)
    }
    return value
}

internal fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

internal fun String.hexToBytes(): ByteArray =
    chunked(2).map { it.toInt(16).toByte() }.toByteArray()

