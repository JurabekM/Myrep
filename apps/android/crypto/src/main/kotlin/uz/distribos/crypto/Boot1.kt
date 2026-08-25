package uz.distribos.crypto

import org.bouncycastle.crypto.modes.ChaCha20Poly1305
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.KeyParameter
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.SecureRandom

/**
 * BOOT-1 kodek — qurilmani ulash (`specs/distribos-event-seal/BOOT-1.md`).
 *
 * DES-1 envelope'ni ochish uchun epoch kaliti kerak, yangi telefonda esa
 * u yo'q. BOOT-1 shu bir marotabalik teshikni yopadi: ishonch manbai —
 * QR orqali uzatilgan bir martalik taklif siri.
 *
 * Python `distribos/aether_q/boot1.py` bilan **baytma-bayt** mos bo'lishi
 * SHART — buni `Boot1KatTest` qulflaydi.
 *
 * ⚠ BOOT-1 ham AETHER-Q spetsifikatsiyasining qismi EMAS.
 */
object Boot1 {
    const val VERSION = 0x0001
    const val HEADER_SIZE = 23
    const val INVITATION_ID_SIZE = 8
    const val NONCE_SIZE = 12
    const val AEAD_TAG_SIZE = 16

    const val MIN_ENVELOPE_SIZE = HEADER_SIZE + AEAD_TAG_SIZE

    val LABEL: ByteArray = "DistribOS-BOOT-1/AETHER-Q-v5.1/v1".toByteArray(Charsets.US_ASCII)

    private val random = SecureRandom()

    fun randomBytes(size: Int): ByteArray = ByteArray(size).also(random::nextBytes)
}

class Boot1Exception(message: String) : Exception(message)

enum class Boot1Kind(val code: Int) {
    JOIN_REQUEST(1),
    JOIN_RESPONSE(2);

    companion object {
        fun from(code: Int): Boot1Kind =
            entries.firstOrNull { it.code == code }
                ?: throw Boot1Exception("noma'lum BOOT-1 turi: $code")
    }
}

/** Taklif siridan ajratilgan yo'nalishli kalitlar. */
class Boot1Keys(
    val requestKey: ByteArray,
    val requestIv: ByteArray,
    val responseKey: ByteArray,
    val responseIv: ByteArray,
    val proofPrk: ByteArray,
) {
    override fun toString(): String = "Boot1Keys(<secrets hidden>)"

    fun forKind(kind: Boot1Kind): Pair<ByteArray, ByteArray> =
        if (kind == Boot1Kind.JOIN_REQUEST) requestKey to requestIv
        else responseKey to responseIv
}

object Boot1Codec {

    /**
     * Taklif siridan yo'nalishli kalitlar.
     *
     * Yo'nalish bo'yicha alohida kalit (AETHER-Q N3): ushlab olingan
     * so'rovni javob sifatida qayta o'ynatib bo'lmaydi.
     */
    fun deriveKeys(invitationSecret: ByteArray): Boot1Keys {
        require(invitationSecret.size == 32) { "taklif siri 32 bayt bo'lishi kerak" }

        val prk = Kdf.hkdfExtract(Boot1.LABEL, invitationSecret)
        return Boot1Keys(
            requestKey = Kdf.hkdfExpand(prk, Boot1.LABEL + "/join-request".toByteArray(), 32),
            requestIv = Kdf.hkdfExpand(prk, Boot1.LABEL + "/iv-request".toByteArray(), 12),
            responseKey = Kdf.hkdfExpand(prk, Boot1.LABEL + "/join-response".toByteArray(), 32),
            responseIv = Kdf.hkdfExpand(prk, Boot1.LABEL + "/iv-response".toByteArray(), 12),
            proofPrk = prk,
        )
    }

    /**
     * Telefon taklif sirini bilishini QURILMA IDENTITETIGA bog'lab isbotlaydi.
     *
     * Tegni ushlab olgan boshqa qurilma uni o'z kaliti bilan ishlatolmaydi.
     */
    fun joinProof(keys: Boot1Keys, deviceId: ByteArray, signPublicKey: ByteArray): ByteArray =
        Kdf.kmac256(
            keys.proofPrk, deviceId + signPublicKey, 32,
            "BOOT1/join".toByteArray(Charsets.US_ASCII),
        )

    fun verifyJoinProof(
        keys: Boot1Keys, deviceId: ByteArray, signPublicKey: ByteArray, proof: ByteArray,
    ): Boolean = Kdf.constantTimeEquals(joinProof(keys, deviceId, signPublicKey), proof)

    private fun packHeader(kind: Boot1Kind, invitationId: ByteArray, nonce: ByteArray): ByteArray {
        require(invitationId.size == Boot1.INVITATION_ID_SIZE) { "invitation_id 8 bayt" }
        require(nonce.size == Boot1.NONCE_SIZE) { "nonce 12 bayt" }
        return ByteBuffer.allocate(Boot1.HEADER_SIZE).order(ByteOrder.BIG_ENDIAN)
            .putShort(Boot1.VERSION.toShort())
            .put(kind.code.toByte())
            .put(invitationId)
            .put(nonce)
            .array()
    }

    fun seal(
        payload: ByteArray,
        kind: Boot1Kind,
        invitationId: ByteArray,
        keys: Boot1Keys,
    ): ByteArray {
        val (key, iv) = keys.forKind(kind)
        val salt = Boot1.randomBytes(Boot1.NONCE_SIZE)
        val nonce = ByteArray(Boot1.NONCE_SIZE) { index ->
            (iv[index].toInt() xor salt[index].toInt()).toByte()
        }
        val header = packHeader(kind, invitationId, nonce)
        return header + aead(true, key, nonce, payload, header)
    }

    fun peekInvitationId(wire: ByteArray): ByteArray {
        if (wire.size < Boot1.MIN_ENVELOPE_SIZE) throw Boot1Exception("envelope juda qisqa")
        val version = ByteBuffer.wrap(wire, 0, 2).order(ByteOrder.BIG_ENDIAN).short.toInt() and 0xFFFF
        if (version != Boot1.VERSION) throw Boot1Exception("noma'lum versiya: $version")
        return wire.copyOfRange(3, 3 + Boot1.INVITATION_ID_SIZE)
    }

    fun peekKind(wire: ByteArray): Boot1Kind {
        if (wire.size < Boot1.MIN_ENVELOPE_SIZE) throw Boot1Exception("envelope juda qisqa")
        return Boot1Kind.from(wire[2].toInt() and 0xFF)
    }

    /** Envelope'ni ochadi. Xato bo'lsa batafsilsiz `Boot1Exception`. */
    fun open(wire: ByteArray, keys: Boot1Keys, expect: Boot1Kind? = null): ByteArray {
        if (wire.size < Boot1.MIN_ENVELOPE_SIZE) throw Boot1Exception("envelope juda qisqa")

        val version = ByteBuffer.wrap(wire, 0, 2).order(ByteOrder.BIG_ENDIAN).short.toInt() and 0xFFFF
        if (version != Boot1.VERSION) throw Boot1Exception("noma'lum versiya: $version")

        val kind = Boot1Kind.from(wire[2].toInt() and 0xFF)
        if (expect != null && kind != expect) {
            throw Boot1Exception("kutilgan ${expect.name}, kelgan ${kind.name}")
        }

        val header = wire.copyOfRange(0, Boot1.HEADER_SIZE)
        val nonce = wire.copyOfRange(11, 11 + Boot1.NONCE_SIZE)
        val ciphertext = wire.copyOfRange(Boot1.HEADER_SIZE, wire.size)

        val (key, _) = keys.forKind(kind)
        return try {
            aead(false, key, nonce, ciphertext, header)
        } catch (_: Exception) {
            // Batafsil sabab CHIQMAYDI (oracle himoyasi).
            throw Boot1Exception("BOOT-1 envelope ochilmadi")
        }
    }

    private fun aead(
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
}
