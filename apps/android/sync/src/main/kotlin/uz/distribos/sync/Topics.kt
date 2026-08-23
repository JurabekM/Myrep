package uz.distribos.sync

import uz.distribos.crypto.Kdf

/**
 * MQTT topik dizayni — Python `distribos/mqtt/topics.py` bilan bir xil.
 *
 * Topik nomida HECH QANDAY ochiq ma'lumot bo'lmaydi: korxona nomi,
 * telefon, mijoz, mahsulot — hech biri. Tenant va qurilma
 * identifikatorlari domain-ajratilgan hash orqali opaque qilinadi.
 *
 * Topikni bilish hech narsa bermaydi: xabar DES-1 bilan muhrlangan.
 */
object Topics {

    const val ROOT = "aetherq/v5.1/distribos"

    private val SEGMENT = Regex("^[a-z0-9_-]{1,64}$")

    enum class Channel(val value: String) {
        EVENTS("events"),
        ACKS("acks"),
        SYNC_REQUESTS("sync-requests"),
        SYNC_RESPONSES("sync-responses"),
        SNAPSHOT_MANIFESTS("snapshot-manifests"),
        SNAPSHOT_CHUNKS("snapshot-chunks"),
        DEVICE_STATUS("device-status"),
        REVOCATIONS("revocations"),
        PROTOCOL_CONTROL("protocol-control");

        companion object {
            fun from(value: String): Channel? = entries.firstOrNull { it.value == value }
        }
    }

    /** Retained faqat presence uchun (ADR-0003) — broker ombor emas. */
    val RETAIN_ALLOWED: Set<Channel> = setOf(Channel.DEVICE_STATUS)

    /**
     * QoS 1 + ilova darajasidagi idempotentlik.
     *
     * QoS 2 avtomatik "to'g'ri javob" deb olinmaydi: u broker uchun
     * qimmat va mobil batareyani ko'proq sarflaydi.
     */
    val CHANNEL_QOS: Map<Channel, Int> = mapOf(
        Channel.EVENTS to 1,
        Channel.ACKS to 1,
        Channel.SYNC_REQUESTS to 1,
        Channel.SYNC_RESPONSES to 1,
        Channel.SNAPSHOT_MANIFESTS to 1,
        Channel.SNAPSHOT_CHUNKS to 1,
        Channel.DEVICE_STATUS to 0,
        Channel.REVOCATIONS to 1,
        Channel.PROTOCOL_CONTROL to 1,
    )

    class TopicException(message: String) : Exception(message)

    /** Topikda ishlatiladigan tenant identifikatori (opaque). */
    fun opaqueTenantId(tenantId: ByteArray): String =
        Kdf.sha3_256("DistribOS/topic/tenant/v1".toByteArray() + tenantId)
            .copyOf(16).joinToString("") { "%02x".format(it) }

    /** Topikda ishlatiladigan qurilma identifikatori (opaque). */
    fun deviceTopicId(deviceId: ByteArray): String =
        Kdf.sha3_256("DistribOS/topic/device/v1".toByteArray() + deviceId)
            .copyOf(8).joinToString("") { "%02x".format(it) }

    class Space(private val tenantTopicId: String, private val environment: String) {

        /**
         * Fazoning o'ziga xosligi.
         *
         * Ikki faza teng bo'lsa ularga QAYTA obuna bo'lish kerak emas.
         * Bu muhim: bir xil topikka ikki marta obuna bo'lingan qurilma
         * har xabarni IKKI NUSXADA oladi va ikkinchisi takror himoyasi
         * tomonidan «hujum» deb rad etiladi.
         */
        val id: String get() = "$tenantTopicId/$environment"

        override fun equals(other: Any?): Boolean =
            this === other || (other is Space && other.id == id)

        override fun hashCode(): Int = id.hashCode()


        init {
            for (segment in listOf(tenantTopicId, environment)) {
                if (!SEGMENT.matches(segment)) {
                    throw TopicException("topik segmenti yaroqsiz: $segment")
                }
            }
        }

        private fun base(channel: Channel) =
            "$ROOT/$tenantTopicId/$environment/${channel.value}"

        fun publishTopic(channel: Channel, partition: String = "0"): String {
            if (!SEGMENT.matches(partition)) {
                throw TopicException("partition yaroqsiz: $partition")
            }
            return "${base(channel)}/$partition"
        }

        fun deviceTopic(channel: Channel, deviceId: ByteArray): String =
            "${base(channel)}/${deviceTopicId(deviceId)}"

        /**
         * `#` emas, `+` — bitta daraja.
         *
         * `#` butun daraxtni ochadi va kerak bo'lmagan trafikni tortadi;
         * mobil qurilmada bu batareya va mobil internet sarfi degani.
         */
        fun subscribePattern(channel: Channel): String = "${base(channel)}/+"

        /**
         * Bu qurilma obuna bo'lishi kerak bo'lgan topiklar.
         *
         * Telefon `snapshot-chunks` va `sync-responses` ni FAQAT o'ziga
         * yo'naltirilgan topikda tinglaydi — boshqalarga ketayotgan katta
         * oqimni tortmaydi.
         */
        fun subscriptions(deviceId: ByteArray): List<Pair<String, Int>> {
            val broadcast = listOf(
                Channel.EVENTS, Channel.ACKS, Channel.SYNC_REQUESTS,
                Channel.DEVICE_STATUS, Channel.REVOCATIONS, Channel.PROTOCOL_CONTROL,
            )
            val directed = listOf(
                Channel.SYNC_RESPONSES, Channel.SNAPSHOT_MANIFESTS, Channel.SNAPSHOT_CHUNKS,
            )
            return broadcast.map { subscribePattern(it) to CHANNEL_QOS.getValue(it) } +
                directed.map { deviceTopic(it, deviceId) to CHANNEL_QOS.getValue(it) }
        }

        companion object {
            fun create(tenantId: ByteArray, environment: String): Space =
                Space(opaqueTenantId(tenantId), environment.lowercase())

            /**
             * Taklifdan kelgan tayyor topik identifikatoridan quriladi.
             *
             * Ulanmagan telefonda kompaniya identifikatorining O'ZI yo'q —
             * QR faqat uning yopiq (opaque) topik ko'rinishini tashiydi.
             * JOIN_REQUEST ni AYNAN shu fazoga yuborish kerak, aks holda
             * kompyuter uni hech qachon eshitmaydi.
             */
            fun fromTopicId(tenantTopicId: String, environment: String): Space =
                Space(tenantTopicId, environment.lowercase())
        }
    }

    fun parseChannel(topic: String): Channel? {
        if (!topic.startsWith(ROOT)) return null
        val parts = topic.split("/")
        return if (parts.size < 6) null else Channel.from(parts[5])
    }
}
