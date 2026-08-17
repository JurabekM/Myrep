package uz.buildcontrol.mobile.data.sync

import android.util.Log
import com.hivemq.client.mqtt.MqttClient
import com.hivemq.client.mqtt.datatypes.MqttQos
import com.hivemq.client.mqtt.mqtt3.Mqtt3BlockingClient
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
import java.util.UUID
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.TimeUnit

/**
 * MQTT transport for free public brokers — the same protocol the desktop uses.
 *
 * Each row lives on its own **retained** topic:
 *
 *     <prefix>/<workspace>/<Entity>/<uid>     retain=1, QoS 1
 *
 * Because replication is last-write-wins per row, the set of retained messages
 * *is* the shared state: a phone that has never connected receives the whole
 * snapshot the moment it subscribes, and live edits arrive afterwards.
 *
 * A public broker is open to anyone who guesses the topic, so payloads can be
 * sealed with [Crypto] using a passphrase shared by the team.
 */
class MqttTransport(
    private val host: String = DEFAULT_HOST,
    private val port: Int = DEFAULT_PORT,
    private val tenant: String = "buildcontrol",
    private val prefix: String = DEFAULT_PREFIX,
    private val useTls: Boolean = true,
    private val username: String = "",
    private val password: String = "",
    passphrase: String = "",
) : SyncTransport {

    override val key: String = "mqtt"

    private val cryptoKey: ByteArray? =
        passphrase.takeIf { it.isNotBlank() }?.let { Crypto.deriveKey(it, tenant) }

    private val inbox = ConcurrentLinkedQueue<Change>()
    private var client: Mqtt3BlockingClient? = null
    @Volatile private var lastMessageAt = 0L
    @Volatile private var failure: String? = null

    private val root get() = "$prefix/$tenant"

    private fun topic(entity: String, uid: String) = "$root/$entity/$uid"

    override fun describe(): String {
        val scheme = if (useTls) "mqtts" else "mqtt"
        val sealed = if (cryptoKey != null) " · shifrlangan" else ""
        return "$scheme://$host:$port/$root$sealed"
    }

    // -- connection ---------------------------------------------------------- //
    private fun connected(): Mqtt3BlockingClient {
        client?.let { return it }
        val builder = MqttClient.builder()
            .useMqttVersion3()
            .identifier("bc-" + UUID.randomUUID().toString().replace("-", "").take(12))
            .serverHost(host)
            .serverPort(port)
        if (useTls) builder.sslWithDefaultConfig()
        if (username.isNotBlank()) {
            builder.simpleAuth()
                .username(username)
                .password(password.toByteArray())
                .applySimpleAuth()
        }
        val fresh = builder.buildBlocking()
        try {
            fresh.connectWith().cleanSession(true).keepAlive(30).send()
        } catch (exc: Exception) {
            throw TransportException("Brokerga ulanib bo'lmadi: ${exc.message}", exc)
        }

        try {
            fresh.toAsync().subscribeWith()
                .topicFilter("$root/#")
                .qos(MqttQos.AT_LEAST_ONCE)
                .callback { publish ->
                    lastMessageAt = System.currentTimeMillis()
                    val payload = publish.payloadAsBytes
                    if (payload.isNotEmpty()) accept(payload)
                }
                .send()
                .get(10, TimeUnit.SECONDS)
        } catch (exc: Exception) {
            fresh.disconnect()
            throw TransportException("Obuna bo'lib bo'lmadi: ${exc.message}", exc)
        }

        client = fresh
        waitQuiet()
        return fresh
    }

    private fun accept(payload: ByteArray) {
        try {
            val body = Crypto.decrypt(payload, cryptoKey)
            val owner = body["tenant"]?.jsonPrimitive?.contentOrNull
            if (owner != null && owner != tenant) return
            inbox.add(Change.fromWire(body, ""))
        } catch (exc: Crypto.DecryptionException) {
            failure = exc.message
        } catch (exc: Exception) {
            Log.w(TAG, "unreadable payload", exc)
        }
    }

    /** Wait until the broker stops pushing the retained snapshot. */
    private fun waitQuiet() {
        lastMessageAt = System.currentTimeMillis()
        val deadline = System.currentTimeMillis() + DRAIN_TIMEOUT_MS
        while (System.currentTimeMillis() < deadline) {
            if (System.currentTimeMillis() - lastMessageAt > QUIET_MS) return
            Thread.sleep(100)
        }
    }

    fun close() {
        val open = client
        client = null
        try {
            open?.disconnect()
        } catch (exc: Exception) {
            Log.d(TAG, "disconnect failed", exc)
        }
    }

    // -- transport API -------------------------------------------------------- //
    override fun check(): String {
        try {
            connected()
            return "OK · $host:$port · ${inbox.size} ta yozuv topildi"
        } finally {
            close()
        }
    }

    override fun push(changes: List<Change>): Int {
        if (changes.isEmpty()) return 0
        val open = connected()
        changes.forEach { change ->
            val body = change.toWire(tenant)
            val payload = if (cryptoKey != null) {
                Crypto.encrypt(body, cryptoKey)
            } else {
                SyncJson.encodeToString(JsonObject.serializer(), body).toByteArray()
            }
            try {
                open.publishWith()
                    .topic(topic(change.entity, change.uid))
                    .payload(payload)
                    .qos(MqttQos.AT_LEAST_ONCE)
                    .retain(true)
                    .send()
            } catch (exc: Exception) {
                throw TransportException("Xabar yuborilmadi: ${exc.message}", exc)
            }
        }
        return changes.size
    }

    override fun pull(after: String, limit: Int): List<Change> {
        connected()
        failure?.let {
            failure = null
            throw TransportException(it)
        }
        val batch = ArrayList<Change>(minOf(limit, inbox.size))
        while (batch.size < limit) {
            batch.add(inbox.poll() ?: break)
        }
        return batch
    }

    companion object {
        private const val TAG = "MqttTransport"
        const val DEFAULT_HOST = "broker.hivemq.com"
        const val DEFAULT_PORT = 8883
        const val DEFAULT_PREFIX = "buildcontrol"
        private const val QUIET_MS = 1_500L
        private const val DRAIN_TIMEOUT_MS = 20_000L

        /** Well-known free brokers offered in the settings screen. */
        val PUBLIC_BROKERS: List<Triple<String, Int, String>> = listOf(
            Triple("broker.hivemq.com", 8883, "HiveMQ (ommaviy, TLS)"),
            Triple("broker.emqx.io", 8883, "EMQX (ommaviy, TLS)"),
            Triple("test.mosquitto.org", 8886, "Mosquitto (ommaviy, TLS)"),
        )
    }
}
