package uz.distribos.sync

import com.hivemq.client.mqtt.MqttClient
import com.hivemq.client.mqtt.datatypes.MqttQos
import com.hivemq.client.mqtt.mqtt5.Mqtt5AsyncClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.UUID
import java.util.concurrent.TimeUnit
import kotlin.random.Random

/**
 * MQTT 5 transporti — faqat baytlarni tashiydi.
 *
 * Bu qatlam ochiq biznes ma'lumotini HECH QACHON ko'rmaydi: `publish`
 * faqat muhrlangan envelope qabul qiladi va buni tip tekshiruvi
 * majburlaydi.
 *
 * Broker ACK **biznes natijasi qo'llandi degani emas** — ular alohida
 * holatlar (`MQTT_PUBLISHED` va `PEER_APPLIED`).
 */
class MqttTransport(
    private val settings: BrokerSettings,
    private val topics: Topics.Space,
    private val deviceId: ByteArray,
    private val onMessage: (ByteArray, Topics.Channel?) -> Unit,
) {

    data class BrokerSettings(
        val host: String = "broker.hivemq.com",
        /** Rasmiy manbadan tekshirilgan (mqtt-dashboard.com): TLS = 8883. */
        val port: Int = 8883,
        val tlsRequired: Boolean = true,
        val cleanStart: Boolean = false,
        val sessionExpirySeconds: Long = 3600,
        val keepAliveSeconds: Int = 60,
        val username: String? = null,
        val password: String? = null,
        val maxPayloadBytes: Int = 256 * 1024,
        val profile: Profile = Profile.PUBLIC_PILOT,
    ) {
        enum class Profile { PUBLIC_PILOT, PRIVATE_PRODUCTION }

        /**
         * Ochiq broker HECH QACHON production deb belgilanmaydi.
         *
         * HiveMQ o'z shartlarida bu brokerni Production/Dev/Staging/UAT
         * muhitlarida ishlatishni MAN QILADI.
         */
        val isPublicPilot: Boolean get() = profile == Profile.PUBLIC_PILOT

        val productionSecure: Boolean get() = profile == Profile.PRIVATE_PRODUCTION

        init {
            if (host in PUBLIC_HOSTS && profile == Profile.PRIVATE_PRODUCTION) {
                throw IllegalArgumentException(
                    "'$host' ochiq broker. Uni PRIVATE_PRODUCTION profili bilan " +
                        "ishlatish taqiqlanadi."
                )
            }
            if (!tlsRequired) {
                throw IllegalArgumentException(
                    "TLS majburiy: payload muhrlangan bo'lsa ham metama'lumot ochiq qoladi."
                )
            }
        }

        companion object {
            val PUBLIC_HOSTS = setOf("broker.hivemq.com", "broker.mqttdashboard.com")
        }
    }

    data class Status(
        val connected: Boolean = false,
        val lastError: String? = null,
        val reconnectAttempts: Int = 0,
        val published: Long = 0,
        val received: Long = 0,
        /** Broker CONNACK'da qaytargan HAQIQIY qiymat — biz so'ragan emas. */
        val negotiatedSessionExpiry: Long? = null,
    )

    private val _status = MutableStateFlow(Status())
    val status: StateFlow<Status> = _status.asStateFlow()

    private var client: Mqtt5AsyncClient? = null

    fun isConnected(): Boolean = _status.value.connected

    fun connect() {
        val builder = MqttClient.builder()
            .useMqttVersion5()
            .identifier("distribos-${deviceId.take(8).joinToString("") { "%02x".format(it) }}")
            .serverHost(settings.host)
            .serverPort(settings.port)
            .automaticReconnect()
            // Exponential backoff + jitter: jitter'siz butun mesh brokerni
            // bir vaqtda "uradi" va broker bizni ban qilishi mumkin.
            .initialDelay(1, TimeUnit.SECONDS)
            .maxDelay(5, TimeUnit.MINUTES)
            .applyAutomaticReconnect()

        if (settings.tlsRequired) {
            builder.sslWithDefaultConfig()
        }

        val async = builder.buildAsync()
        client = async

        var connect = async.connectWith()
            .cleanStart(settings.cleanStart)
            .sessionExpiryInterval(settings.sessionExpirySeconds)
            .keepAlive(settings.keepAliveSeconds)

        if (settings.username != null) {
            connect = connect.simpleAuth()
                .username(settings.username)
                .password((settings.password ?: "").toByteArray())
                .applySimpleAuth()
        }

        connect.send().whenComplete { ack, error ->
            if (error != null) {
                _status.value = _status.value.copy(
                    connected = false,
                    lastError = error.message,
                    reconnectAttempts = _status.value.reconnectAttempts + 1,
                )
                return@whenComplete
            }
            _status.value = _status.value.copy(
                connected = true,
                lastError = null,
                // Broker cheklovlarini TAXMIN QILMAYMIZ — CONNACK'dan o'qiymiz.
                negotiatedSessionExpiry =
                    ack.sessionExpiryInterval.orElse(settings.sessionExpirySeconds),
            )
            subscribeAll(async)
        }
    }

    private fun subscribeAll(async: Mqtt5AsyncClient) {
        for ((topic, qos) in topics.subscriptions(deviceId)) {
            async.subscribeWith()
                .topicFilter(topic)
                .qos(MqttQos.fromCode(qos) ?: MqttQos.AT_LEAST_ONCE)
                .callback { message ->
                    val payload = message.payloadAsBytes
                    _status.value = _status.value.copy(received = _status.value.received + 1)

                    // Hajm chegarasi transport darajasida: katta paket
                    // kripto qatlamiga umuman yetib bormaydi (DoS himoyasi).
                    if (payload.size > settings.maxPayloadBytes) return@callback

                    try {
                        onMessage(payload, Topics.parseChannel(message.topic.toString()))
                    } catch (_: Exception) {
                        // Bitta buzuq xabar butun tinglovchini o'ldirmasin.
                    }
                }
                .send()
        }
    }

    fun disconnect() {
        client?.disconnect()
        client = null
        _status.value = _status.value.copy(connected = false)
    }

    /**
     * Muhrlangan envelope'ni publish qiladi.
     *
     * Faqat `Sealed` qabul qilinadi — ochiq `ByteArray` emas. Bu "ochiq
     * matn brokerga chiqib ketdi" xatosini tip darajasida imkonsiz qiladi.
     */
    fun publish(
        envelope: AndroidAetherQProvider.Sealed,
        channel: Topics.Channel,
        partition: String = "0",
        targetDeviceId: ByteArray? = null,
    ) {
        val async = client ?: return
        if (envelope.wire.size > settings.maxPayloadBytes) return

        val topic = if (targetDeviceId != null) {
            topics.deviceTopic(channel, targetDeviceId)
        } else {
            topics.publishTopic(channel, partition)
        }

        async.publishWith()
            .topic(topic)
            .payload(envelope.wire)
            .qos(MqttQos.fromCode(Topics.CHANNEL_QOS.getValue(channel)) ?: MqttQos.AT_LEAST_ONCE)
            // Retained faqat presence uchun (ADR-0003): broker ma'lumotlar
            // ombori emas.
            .retain(channel in Topics.RETAIN_ALLOWED)
            .send()

        _status.value = _status.value.copy(published = _status.value.published + 1)
    }

    companion object {
        /** Exponential backoff + full jitter (Python bilan bir xil qoida). */
        fun backoffMillis(attempt: Int, random: Random = Random.Default): Long {
            val ceiling = minOf(300_000L, 1_000L shl minOf(attempt, 10))
            return random.nextLong(1_000L, maxOf(1_001L, ceiling))
        }

        fun newCorrelationId(): ByteArray =
            UUID.randomUUID().toString().toByteArray()
    }
}
