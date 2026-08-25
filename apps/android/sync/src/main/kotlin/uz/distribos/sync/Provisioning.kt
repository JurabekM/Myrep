package uz.distribos.sync

import co.nstant.`in`.cbor.CborDecoder
import co.nstant.`in`.cbor.CborEncoder
import co.nstant.`in`.cbor.model.ByteString
import co.nstant.`in`.cbor.model.Map as CborMap
import co.nstant.`in`.cbor.model.Number as CborNumber
import co.nstant.`in`.cbor.model.UnicodeString
import uz.distribos.crypto.Boot1Codec
import uz.distribos.crypto.Boot1Exception
import uz.distribos.crypto.Boot1Kind
import uz.distribos.data.db.PeerDeviceEntity
import uz.distribos.data.db.SyncDao
import java.io.ByteArrayOutputStream

/**
 * Qurilmani ulash — telefon tomoni.
 *
 * Oqim (`specs/distribos-event-seal/BOOT-1.md`):
 *
 * ```
 * 1. Telefon QR ni o'qiydi          -> Invitation
 * 2. JOIN_REQUEST yuboradi          -> protocol-control
 * 3. Desktop javob beradi           <- JOIN_RESPONSE
 * 4. Telefon tenant va epoch kalitini o'rnatadi
 * 5. Egasi desktopda qurilmani tasdiqlaydi
 * ```
 *
 * 5-qadamgacha telefon hodisa yubora oladi, lekin desktop ularni QABUL
 * QILMAYDI (faqat `ACTIVE` qurilma qabul qilinadi). Bu ataylab.
 */
class ProvisioningClient(
    private val dao: SyncDao,
    private val provider: AndroidAetherQProvider,
    private val transport: MqttTransport,
    private val deviceId: ByteArray,
    private val signPublicKey: ByteArray,
    private val kemPublicKey: ByteArray,
    /**
     * Kompaniya identifikatori qabul qilinganda chaqiriladi.
     *
     * Telefon boshida O'ZINING vaqtinchalik identifikatorini ishlatadi.
     * Ulangandan keyin u kompyuternikiga ALMASHISHI shart: DES-1
     * muhri kompaniyaga bog'langan, mos kelmasa hodisalar begona deb
     * rad etiladi.
     */
    private val onTenantAdopted: (ByteArray) -> Unit = {},
) {

    class ProvisioningException(message: String) : Exception(message)

    /** QR kodidan o'qilgan taklif. */
    data class Invitation(
        val invitationId: ByteArray,
        val tenantTopicId: String,
        val secret: ByteArray,
        val role: String,
        val displayName: String,
        val expiresAt: String,
        val hostKeyFingerprint: ByteArray,
        val brokerHost: String,
        val brokerPort: Int,
        val environment: String,
    ) {
        override fun equals(other: Any?): Boolean =
            this === other || (other is Invitation && invitationId.contentEquals(other.invitationId))

        override fun hashCode(): Int = invitationId.contentHashCode()

        override fun toString(): String =
            "Invitation(role=$role, name=$displayName, <secret hidden>)"

        val isExpired: Boolean
            get() = try {
                java.time.Instant.parse(expiresAt.replace("+00:00", "Z"))
                    .isBefore(java.time.Instant.now())
            } catch (_: Exception) {
                // Muddatni o'qib bo'lmasa TAKLIF RAD ETILADI (fail-closed).
                true
            }

        companion object {
            /**
             * QR payload'ini o'qiydi.
             *
             * Python `onboarding.Invitation.to_qr_payload()` bilan bir xil
             * CBOR shakli — kalitlar qisqartirilgan (QR hajmi uchun).
             */
            fun fromQrPayload(raw: ByteArray): Invitation {
                val map = try {
                    CborDecoder.decode(raw).first() as CborMap
                } catch (exception: Exception) {
                    throw ProvisioningException("QR kod o'qilmadi")
                }

                fun text(key: String) = (map.get(UnicodeString(key)) as? UnicodeString)?.string
                fun bytes(key: String) = (map.get(UnicodeString(key)) as? ByteString)?.bytes
                fun number(key: String) = (map.get(UnicodeString(key)) as? CborNumber)?.value?.toInt()

                if (number("v") != 1) {
                    throw ProvisioningException("QR kod versiyasi qo'llab-quvvatlanmaydi")
                }

                val invitation = Invitation(
                    invitationId = (text("id") ?: throw ProvisioningException("QR to'liq emas"))
                        .chunked(2).map { it.toInt(16).toByte() }.toByteArray(),
                    tenantTopicId = text("t") ?: throw ProvisioningException("QR to'liq emas"),
                    secret = bytes("s") ?: throw ProvisioningException("QR to'liq emas"),
                    role = text("r") ?: "agent",
                    displayName = text("n") ?: "Qurilma",
                    expiresAt = text("e") ?: throw ProvisioningException("QR to'liq emas"),
                    hostKeyFingerprint = bytes("k") ?: ByteArray(0),
                    brokerHost = text("bh") ?: "broker.hivemq.com",
                    brokerPort = number("bp") ?: 8883,
                    environment = text("env") ?: "pilot",
                )

                if (invitation.secret.size != 32) {
                    throw ProvisioningException("QR kod tarkibi noto'g'ri")
                }
                if (invitation.isExpired) {
                    throw ProvisioningException(
                        "Taklif muddati o'tgan. Kompyuterda yangi QR yarating."
                    )
                }
                return invitation
            }
        }
    }

    /** Ulash natijasi — UI shuni ko'rsatadi. */
    sealed interface Result {
        data class Joined(val role: String, val epoch: Int) : Result
        data class Failed(val reason: String) : Result
    }

    private var pending: Invitation? = null

    /**
     * JOIN_REQUEST yuboradi.
     *
     * Javob asinxron keladi va `handleResponse()` orqali qayta ishlanadi.
     */
    fun requestJoin(invitation: Invitation) {
        if (!transport.isConnected()) {
            throw ProvisioningException(
                "Internet yo'q. Ulanishni tekshirib qaytadan urinib ko'ring."
            )
        }
        pending = invitation

        val keys = Boot1Codec.deriveKeys(invitation.secret)
        val payload = CborMap().apply {
            put(UnicodeString("device_id"), ByteString(deviceId))
            put(UnicodeString("sign_public_key"), ByteString(signPublicKey))
            put(UnicodeString("kem_public_key"), ByteString(kemPublicKey))
            put(UnicodeString("platform"), UnicodeString("android"))
            put(UnicodeString("display_name"), UnicodeString(invitation.displayName))
            put(
                UnicodeString("proof"),
                ByteString(Boot1Codec.joinProof(keys, deviceId, signPublicKey)),
            )
        }
        val encoded = ByteArrayOutputStream().also { CborEncoder(it).encode(payload) }.toByteArray()
        val wire = Boot1Codec.seal(encoded, Boot1Kind.JOIN_REQUEST, invitation.invitationId, keys)

        // Kompaniyaning topik fazosiga o'tamiz va OBUNA TASDIQLANGACH
        // yuboramiz.
        //
        // Ikkalasi ham majburiy:
        //  * faza — busiz so'rov bizning vaqtinchalik manzilimizga
        //    ketadi va kompyuter uni eshitmaydi;
        //  * kutish — busiz javob biz obuna bo'lgunimizcha kelib,
        //    yo'qoladi. Telefon esa abadiy «javob kutilmoqda» da
        //    qoladi va sabab hech qayerda ko'rinmaydi.
        transport.useTenantSpace(
            Topics.Space.fromTopicId(invitation.tenantTopicId, invitation.environment)
        ) {
            transport.publishRaw(wire, Topics.Channel.PROTOCOL_CONTROL)
        }
    }

    /**
     * Kelgan JOIN_RESPONSE ni qayta ishlaydi.
     *
     * Kutilmagan yoki begona javob JIMGINA e'tiborsiz qoldiriladi —
     * bu xato emas, boshqa qurilmaga qaratilgan bo'lishi mumkin.
     */
    suspend fun handleResponse(wire: ByteArray): Result? {
        val invitation = pending ?: return null

        val kind = try {
            Boot1Codec.peekKind(wire)
        } catch (_: Boot1Exception) {
            return null
        }
        if (kind != Boot1Kind.JOIN_RESPONSE) return null

        if (!Boot1Codec.peekInvitationId(wire).contentEquals(invitation.invitationId)) {
            return null   // boshqa taklif uchun
        }

        val payload = try {
            val keys = Boot1Codec.deriveKeys(invitation.secret)
            CborDecoder.decode(Boot1Codec.open(wire, keys, Boot1Kind.JOIN_RESPONSE))
                .first() as CborMap
        } catch (exception: Exception) {
            return Result.Failed("Javob ochilmadi — taklif noto'g'ri bo'lishi mumkin")
        }

        fun bytes(key: String) = (payload.get(UnicodeString(key)) as ByteString).bytes
        fun text(key: String) = (payload.get(UnicodeString(key)) as UnicodeString).string
        fun number(key: String) = (payload.get(UnicodeString(key)) as CborNumber).value.toLong()

        return try {
            val tenantId = bytes("tenant_id")
            val epoch = number("epoch").toInt()
            val keyId = number("key_id")
            val root = bytes("epoch_root_secret")
            val profile = number("profile_id").toInt()
            val role = text("role")
            val hostDeviceId = bytes("host_device_id")
            val hostSignKey = bytes("host_sign_public_key")

            if (root.size != 32) throw ProvisioningException("kalit hajmi noto'g'ri")
            if (hostSignKey.size != 1952) {
                throw ProvisioningException("kompyuter kaliti hajmi noto'g'ri")
            }
            // QR dagi barmoq izi bilan solishtiramiz. Javob allaqachon
            // taklif siri bilan autentifikatsiyalangan, bu qo'shimcha
            // qatlam — lekin arzon.
            if (invitation.hostKeyFingerprint.isNotEmpty() &&
                !uz.distribos.crypto.Kdf.constantTimeEquals(
                    keyFingerprint(hostSignKey), invitation.hostKeyFingerprint
                )
            ) {
                throw ProvisioningException("Kompyuter kaliti QR koddagiga mos emas")
            }

            // Kompaniyani QABUL QILAMIZ — kalitni o'rnatishdan OLDIN,
            // chunki epoch kaliti kompaniya identifikatoriga bog'lanadi.
            onTenantAdopted(tenantId)

            provider.installEpochKey(epoch, keyId, root, profile)

            // Desktopni tanilgan va FAOL peer sifatida yozamiz — biz
            // uni QR orqali ataylab tanladik.
            dao.upsertPeer(
                PeerDeviceEntity(
                    deviceIdHex = hostDeviceId.joinToString("") { "%02x".format(it) },
                    displayName = "Kompyuter",
                    platform = "desktop",
                    role = "owner",
                    state = "ACTIVE",
                    signPublicKey = hostSignKey,
                    kemPublicKey = ByteArray(0),
                    lastSeenAtMs = System.currentTimeMillis(),
                    lastAppliedSequence = 0,
                    isFullReplica = true,
                    revokedReason = null,
                )
            )

            pending = null
            Result.Joined(role = role, epoch = epoch)
        } catch (exception: Exception) {
            Result.Failed(exception.message ?: "Ulash bajarilmadi")
        }
    }

    val isWaiting: Boolean get() = pending != null

    companion object {
        /** Ochiq kalitning 16 baytli barmoq izi (Python bilan bir xil). */
        fun keyFingerprint(publicKey: ByteArray): ByteArray =
            uz.distribos.crypto.Kdf.sha3_256(
                "DistribOS/key-fingerprint/v1".toByteArray() + publicKey
            ).copyOf(16)
    }

    fun cancel() {
        pending = null
    }
}
