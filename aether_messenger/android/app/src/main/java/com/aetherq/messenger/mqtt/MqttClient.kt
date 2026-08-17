package com.aetherq.messenger.mqtt

import com.hivemq.client.mqtt.datatypes.MqttQos
import com.hivemq.client.mqtt.mqtt5.Mqtt5AsyncClient
import com.hivemq.client.mqtt.mqtt5.Mqtt5Client
import java.util.UUID
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.suspendCancellableCoroutine

private const val BROKER_HOST = "broker.hivemq.com"
private const val BROKER_PORT = 8883
private const val TOPIC_PREFIX = "aetherq/msgr/"

/**
 * `broker.hivemq.com` public MQTT broker'i ustidan yupqa transport qatlami.
 * Xavfsizlik butunlay E2E shifrlashga (AUTH-AKEM + Compress-KEM + record layer)
 * tayanadi — broker ishonchsiz hisoblanadi, faqat marshrutlash uchun ishlatiladi.
 */
class MqttClient(private val ownUserId: String) {

    private val client: Mqtt5AsyncClient =
        Mqtt5Client.builder()
            .identifier("aetherq-$ownUserId-${UUID.randomUUID()}")
            .serverHost(BROKER_HOST)
            .serverPort(BROKER_PORT)
            .sslWithDefaultConfig()
            .buildAsync()

    /** Brokerga ulanadi va o'z inbox topic'iga (`aetherq/msgr/<ownUserId>`) obuna bo'ladi. */
    suspend fun connectAndSubscribe(onMessage: (ByteArray) -> Unit) {
        suspendCancellableCoroutine { cont ->
            client.connectWith().send().whenComplete { _, connectError ->
                if (connectError != null) {
                    cont.resumeWithException(connectError)
                    return@whenComplete
                }
                client.subscribeWith()
                    .topicFilter(TOPIC_PREFIX + ownUserId)
                    .qos(MqttQos.AT_LEAST_ONCE)
                    .callback { publish -> onMessage(publish.payloadAsBytes) }
                    .send()
                    .whenComplete { _, subscribeError ->
                        if (subscribeError != null) {
                            cont.resumeWithException(subscribeError)
                        } else {
                            cont.resume(Unit)
                        }
                    }
            }
        }
    }

    fun publishTo(recipientUserId: String, payload: ByteArray) {
        client.publishWith()
            .topic(TOPIC_PREFIX + recipientUserId)
            .qos(MqttQos.AT_LEAST_ONCE)
            .payload(payload)
            .send()
    }

    fun disconnect() {
        client.disconnect()
    }
}
