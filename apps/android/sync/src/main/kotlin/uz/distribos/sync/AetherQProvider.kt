package uz.distribos.sync

import uz.distribos.crypto.AetherQException
import uz.distribos.crypto.ContentType
import uz.distribos.crypto.Des1
import uz.distribos.crypto.Des1Codec
import uz.distribos.crypto.Des1FormatException
import uz.distribos.crypto.Des1Header
import uz.distribos.crypto.EpochKeys
import uz.distribos.crypto.MlDsa65
import uz.distribos.crypto.RejectReason
import uz.distribos.data.db.EpochKeyEntity
import uz.distribos.data.db.ReplayWindowEntity
import uz.distribos.data.db.SyncDao
import java.security.SecureRandom
import java.util.concurrent.atomic.AtomicLong

/**
 * `AetherQ51Provider` ning Android tomoni.
 *
 * Kripto BU YERDA O'YLAB TOPILMAYDI — hamma narsa `:crypto` modulidan
 * keladi. Bu sinf ularni Room bazasi bilan bog'laydi: kalit qayerda,
 * kim bekor qilingan, qaysi `seq` allaqachon ko'rilgan.
 *
 * Ochish tartibi DES-1 spetsifikatsiyasidagi 11 qadamga QAT'IY amal
 * qiladi va fail-closed.
 */
class AndroidAetherQProvider(
    private val dao: SyncDao,
    private val tenantId: ByteArray,
    private val deviceId: ByteArray,
    private val signPublicKey: ByteArray,
    private val signPrivateKey: ByteArray,
    private val keyVault: KeyVault,
    private val profileId: Int = Des1.PROFILE_HYBRID,
    private val maxPayloadBytes: Int = 256 * 1024,
) {
    init {
        require(profileId == Des1.PROFILE_HYBRID || profileId == Des1.PROFILE_MINIMAL) {
            "Faqat 0x01 va 0x03 profillari qo'llab-quvvatlanadi"
        }
    }

    private val deviceIdHex = deviceId.joinToString("") { "%02x".format(it) }
    private val random = SecureRandom()
    private val keyCache = HashMap<Pair<Int, Long>, EpochKeys>()
    private val localSequence = AtomicLong(0)

    data class Sealed(
        val wire: ByteArray,
        val contentType: ContentType,
        val epoch: Int,
        val senderDeviceId: ByteArray,
    )

    data class Opened(
        val payload: ByteArray,
        val contentType: ContentType,
        val epoch: Int,
        val senderDeviceId: ByteArray,
        val sequence: Long,
    )

    // --- kalitlar ---------------------------------------------------------

    private suspend fun epochKeys(epoch: Int, keyId: Long): EpochKeys {
        keyCache[epoch to keyId]?.let { return it }

        val record = dao.epochKey(epoch, keyId)
            ?: throw AetherQException(RejectReason.UNKNOWN_KEY, "epoch=$epoch keyId=$keyId")
        val root = keyVault.unwrap(record.rootSecretWrapped, keyContext(epoch, keyId))
        val keys = Des1Codec.deriveEpochKeys(root, tenantId, epoch, keyId, record.profileId)
        keyCache[epoch to keyId] = keys
        return keys
    }

    private suspend fun currentEpoch(): EpochKeyEntity =
        dao.currentEpochKey()
            ?: throw AetherQException(RejectReason.UNKNOWN_EPOCH, "joriy epoch kaliti yo'q")

    /**
     * Yangi epoch ochadi.
     *
     * Eski kalit O'CHIRILMAYDI: uzoq vaqt ulanmagan qurilma qaytganda
     * uning eski hodisalari hali ham ochilishi kerak.
     */
    suspend fun rotateKeys(): Int {
        val current = dao.currentEpochKey()
        val nextEpoch = (current?.epoch ?: 0) + 1
        val root = ByteArray(32).also(random::nextBytes)

        dao.clearCurrentEpochKeys()
        dao.upsertEpochKey(
            EpochKeyEntity(
                epoch = nextEpoch,
                keyId = 1L,
                rootSecretWrapped = keyVault.wrap(root, keyContext(nextEpoch, 1L)),
                profileId = profileId,
                isCurrent = true,
                createdAtMs = System.currentTimeMillis(),
            )
        )
        keyCache.clear()
        return nextEpoch
    }

    /** Desktop bergan epoch kalitini o'rnatadi (provisioning natijasi). */
    suspend fun installEpochKey(epoch: Int, keyId: Long, rootSecret: ByteArray, profile: Int) {
        require(rootSecret.size == 32) { "epoch root secret 32 bayt bo'lishi kerak" }
        dao.clearCurrentEpochKeys()
        dao.upsertEpochKey(
            EpochKeyEntity(
                epoch = epoch, keyId = keyId,
                rootSecretWrapped = keyVault.wrap(rootSecret, keyContext(epoch, keyId)),
                profileId = profile, isCurrent = true,
                createdAtMs = System.currentTimeMillis(),
            )
        )
        keyCache.clear()
    }

    // --- muhrlash ---------------------------------------------------------

    suspend fun seal(
        payload: ByteArray,
        contentType: ContentType,
        sequence: Long? = null,
    ): Sealed {
        if (payload.size + Des1.MIN_ENVELOPE_SIZE > maxPayloadBytes) {
            throw AetherQException(
                RejectReason.TOO_LARGE, "${payload.size} bayt, chegara $maxPayloadBytes"
            )
        }

        val record = currentEpoch()
        val keys = epochKeys(record.epoch, record.keyId)
        val seq = sequence ?: localSequence.incrementAndGet()

        val header = Des1Header(
            version = Des1.VERSION,
            profileId = profileId,
            contentType = contentType.code,
            epoch = record.epoch,
            keyId = record.keyId,
            tenantTag = keys.tenantTag,
            senderDeviceId = deviceId,
            sequence = seq,
            // Hodisa `seq` i berilganda `rand` NOL: qayta yuborish
            // (retry) aynan bir xil baytlarni beradi va peer uni takror
            // deb tanaydi, yangi xabar deb emas.
            rand = if (sequence != null) ByteArray(Des1.RAND_SIZE)
            else ByteArray(Des1.RAND_SIZE).also(random::nextBytes),
        )

        val wire = Des1Codec.seal(payload, header, keys) { message ->
            MlDsa65.sign(signPrivateKey, message)
        }
        return Sealed(wire, contentType, record.epoch, deviceId)
    }

    // --- ochish -----------------------------------------------------------

    /**
     * DES-1 envelope'ni ochadi va TO'LIQ tekshiradi.
     *
     * Rad etish sababi lokal yoziladi, lekin tarmoqqa QAYTARILMAYDI
     * (AETHER-Q N15 — oracle himoyasi).
     */
    suspend fun open(wire: ByteArray): Opened {
        // 1. Hajm
        if (wire.size > maxPayloadBytes) {
            throw AetherQException(RejectReason.TOO_LARGE, "${wire.size}")
        }

        val parts = try {
            Des1Codec.split(wire)
        } catch (exception: Des1FormatException) {
            throw AetherQException(RejectReason.MALFORMED, exception.message.orEmpty())
        }
        val header = parts.header

        // 2-3. Versiya va profil
        if (header.version != Des1.VERSION) {
            throw AetherQException(RejectReason.UNKNOWN_VERSION, "${header.version}")
        }
        if (header.profileId != Des1.PROFILE_HYBRID && header.profileId != Des1.PROFILE_MINIMAL) {
            throw AetherQException(RejectReason.UNSUPPORTED_PROFILE, "${header.profileId}")
        }

        // 4-5. Epoch va kalit
        val keys = epochKeys(header.epoch, header.keyId)

        // 6. Tenant izolyatsiyasi (constant-time)
        if (!Des1Codec.tenantTagMatches(header, keys)) {
            throw AetherQException(RejectReason.FOREIGN_TENANT)
        }

        // 7. Jo'natuvchi ma'lum va bekor qilinmagan.
        //    DIQQAT: bu imzo tekshiruvidan OLDIN. Bekor qilingan
        //    qurilmaning imzosi matematik jihatdan hali ham TO'G'RI.
        val senderHex = header.senderDeviceId.joinToString("") { "%02x".format(it) }
        val peer = dao.peer(senderHex) ?: throw AetherQException(RejectReason.UNKNOWN_SENDER)
        if (peer.state == "REVOKED") {
            throw AetherQException(RejectReason.REVOKED_SENDER)
        }

        // 8. Imzo
        val signedBytes = Des1Codec.signedBytes(parts.packedHeader, parts.ciphertext)
        if (!MlDsa65.verify(peer.signPublicKey, parts.signature, signedBytes)) {
            throw AetherQException(RejectReason.BAD_SIGNATURE)
        }

        // 9. Replay
        if (checkAndRecordReplay(header.epoch, senderHex, header.sequence)) {
            throw AetherQException(RejectReason.REPLAY, "seq=${header.sequence}")
        }

        // 10. AEAD
        val payload = try {
            Des1Codec.openAead(header, parts.ciphertext, keys)
        } catch (_: Des1FormatException) {
            throw AetherQException(RejectReason.AEAD_FAILURE)
        }

        // 11. Schema validatsiyasi chaqiruvchi tomonda.
        return Opened(
            payload = payload,
            contentType = ContentType.from(header.contentType),
            epoch = header.epoch,
            senderDeviceId = header.senderDeviceId,
            sequence = header.sequence,
        )
    }

    // --- replay oynasi ----------------------------------------------------

    /** `true` — bu takror. Sliding-window bitmap, AETHER-Q N5. */
    suspend fun checkAndRecordReplay(epoch: Int, deviceIdHex: String, sequence: Long): Boolean {
        val capacity = BITMAP_BYTES * 8
        val window = dao.replayWindow(epoch, deviceIdHex)

        if (window == null) {
            val bitmap = ByteArray(BITMAP_BYTES)
            bitmap[0] = 1
            dao.upsertReplayWindow(
                ReplayWindowEntity(epoch, deviceIdHex, sequence, bitmap, System.currentTimeMillis())
            )
            return false
        }

        var bitmap = java.math.BigInteger(1, window.bitmap.reversedArray())

        if (sequence > window.highestSequence) {
            val shift = (sequence - window.highestSequence).toInt()
            bitmap = if (shift >= capacity) java.math.BigInteger.ZERO
            else bitmap.shiftLeft(shift).and(mask(capacity))
            bitmap = bitmap.or(java.math.BigInteger.ONE)
            dao.upsertReplayWindow(
                window.copy(
                    highestSequence = sequence,
                    bitmap = toFixedLe(bitmap),
                    updatedAtMs = System.currentTimeMillis(),
                )
            )
            return false
        }

        val offset = (window.highestSequence - sequence).toInt()
        if (offset >= capacity) return true          // oynadan chetda — juda eski
        if (bitmap.testBit(offset)) return true      // allaqachon ko'rilgan

        dao.upsertReplayWindow(
            window.copy(
                bitmap = toFixedLe(bitmap.setBit(offset)),
                updatedAtMs = System.currentTimeMillis(),
            )
        )
        return false
    }

    fun publicIdentity(): DeviceIdentity =
        DeviceIdentity(deviceId, signPublicKey, "5.1.0")

    data class DeviceIdentity(
        val deviceId: ByteArray,
        val signPublicKey: ByteArray,
        val protocolVersion: String,
    ) {
        override fun equals(other: Any?): Boolean =
            this === other || (other is DeviceIdentity && deviceId.contentEquals(other.deviceId))

        override fun hashCode(): Int = deviceId.contentHashCode()
    }

    companion object {
        /** Oxirgi 8192 ta `seq` aniq kuzatiladi (AETHER-Q N5: kamida 2^20 oyna). */
        const val BITMAP_BYTES = 1024

        fun keyContext(epoch: Int, keyId: Long): ByteArray =
            "DistribOS/epoch-root/v1".toByteArray() +
                java.nio.ByteBuffer.allocate(12).putInt(epoch).putLong(keyId).array()

        private fun mask(bits: Int): java.math.BigInteger =
            java.math.BigInteger.ONE.shiftLeft(bits).subtract(java.math.BigInteger.ONE)

        private fun toFixedLe(value: java.math.BigInteger): ByteArray {
            val big = value.toByteArray()          // big-endian, ehtimol ishora bayti bilan
            val trimmed = if (big.size > 1 && big[0] == 0.toByte()) big.copyOfRange(1, big.size) else big
            val little = trimmed.reversedArray()
            return if (little.size >= BITMAP_BYTES) little.copyOf(BITMAP_BYTES)
            else little + ByteArray(BITMAP_BYTES - little.size)
        }
    }
}
