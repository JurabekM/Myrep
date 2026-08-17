package com.aetherq.messenger.data

import com.aetherq.messenger.crypto.AetherCrypto
import com.aetherq.messenger.crypto.ContactCard
import com.aetherq.messenger.crypto.Identity
import com.aetherq.messenger.crypto.hexToBytes
import com.aetherq.messenger.crypto.toHex
import com.aetherq.messenger.data.local.dao.ContactDao
import com.aetherq.messenger.data.local.dao.MessageDao
import com.aetherq.messenger.data.local.entity.ContactEntity
import com.aetherq.messenger.data.local.entity.MessageEntity
import com.aetherq.messenger.mqtt.InboundEnvelope
import com.aetherq.messenger.mqtt.MessageEnvelope
import com.aetherq.messenger.mqtt.MqttClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch

/**
 * MQTT transport, AUTH-AKEM handshake, Compress-KEM ratchet va mahalliy bazani
 * bir joyga bog'laydigan yuqori darajadagi fasad — Compose ViewModel'lar shu orqali
 * ishlaydi, JNI/protokol tafsilotlarini bilishlari shart emas.
 */
class MessengerRepository(
    private val identity: Identity,
    private val contactDao: ContactDao,
    private val messageDao: MessageDao,
    private val sessionManager: SessionManager,
    private val mqttClient: MqttClient,
) {
    // HiveMQ callback'lari background thread'da chaqiriladi — suspend DAO/kripto
    // chaqiruvlarini shu yerdan ishga tushirish uchun alohida scope kerak.
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun observeContacts(): Flow<List<ContactEntity>> = contactDao.observeAll()

    fun observeMessages(contactUserId: String): Flow<List<MessageEntity>> = messageDao.observeForContact(contactUserId)

    suspend fun addContact(card: ContactCard, displayName: String) {
        contactDao.upsert(
            ContactEntity(
                userId = card.userId,
                displayName = displayName,
                edPkHex = card.edPk,
                xPkHex = card.xPk,
                mlkemPkHex = card.mlkemPk,
                createdAt = System.currentTimeMillis(),
            ),
        )
    }

    suspend fun connectMqtt() {
        mqttClient.connectAndSubscribe { payload -> scope.launch { handleIncoming(payload) } }
    }

    /** Kontakt bilan seans yo'q bo'lsa AUTH-AKEM handshake bajarib MQTT orqali yuboradi. */
    private suspend fun ensureSession(contact: ContactEntity) {
        if (sessionManager.hasSession(contact.userId)) return

        val encaps =
            AetherCrypto.akemEncapsulate(
                pkRecipMlkem = hexToBytes(contact.mlkemPkHex),
                pkRecipX25519 = hexToBytes(contact.xPkHex),
                skSenderSign = identity.edSk,
                pkSenderSign = identity.edPk,
                pkRecipSign = hexToBytes(contact.edPkHex),
            )
        sessionManager.establishSession(contact.userId, encaps.sharedSecret)

        val envelope = MessageEnvelope.encodeHandshake(hexToBytes(identity.userId), encaps)
        mqttClient.publishTo(contact.userId, envelope)
    }

    suspend fun sendMessage(contact: ContactEntity, text: String) {
        ensureSession(contact)
        val session = sessionManager.sessionFor(contact.userId) ?: error("Seans o'rnatilmadi")

        val step = session.sender.nextFrame(hexToBytes(contact.xPkHex))
        val recordFrame = AetherCrypto.sealRecord(step.sharedSecret, session.sessionId, text.toByteArray(Charsets.UTF_8))
        val envelope = MessageEnvelope.encodeMessage(step.frame, recordFrame)
        mqttClient.publishTo(contact.userId, envelope)

        messageDao.insert(
            MessageEntity(
                contactUserId = contact.userId,
                isOutgoing = true,
                plaintext = text,
                timestamp = System.currentTimeMillis(),
            ),
        )
    }

    private suspend fun handleIncoming(payload: ByteArray) {
        when (val envelope = MessageEnvelope.decode(payload)) {
            is InboundEnvelope.Handshake -> handleHandshake(envelope)
            is InboundEnvelope.RatchetMessage -> handleRatchetMessage(envelope)
            null -> Unit
        }
    }

    private suspend fun handleHandshake(envelope: InboundEnvelope.Handshake) {
        val senderUserId = envelope.senderUserId.toHex()
        // Noma'lum yuboruvchi (QR orqali oldindan qo'shilmagan) e'tiborsiz qoldiriladi —
        // markazlashgan directory yo'q, faqat oldindan almashilgan kalitlarga ishoniladi.
        val contact = contactDao.findByUserId(senderUserId) ?: return

        val sharedSecret =
            AetherCrypto.akemDecapsulate(
                skRecipMlkem = identity.mlkemSk,
                skRecipX25519 = identity.xSk,
                pkRecipX25519 = identity.xPk,
                zRecip = identity.zRecip,
                pkSenderSign = hexToBytes(contact.edPkHex),
                pkRecipSign = identity.edPk,
                ctMlkem = envelope.ctMlkem,
                ctX25519 = envelope.ctX25519,
                signature = envelope.signature,
            )
        sessionManager.establishSession(contact.userId, sharedSecret)
    }

    private suspend fun handleRatchetMessage(envelope: InboundEnvelope.RatchetMessage) {
        val sessionIdBytes = envelope.compressFrame.copyOfRange(1, 9)
        val contactUserId = sessionManager.contactForSessionId(sessionIdBytes) ?: return
        val session = sessionManager.sessionFor(contactUserId) ?: return

        val stepSecret = session.recipient.acceptFrame(envelope.compressFrame, identity.xSk)
        val plaintext = AetherCrypto.openRecord(stepSecret, session.sessionId, envelope.recordFrame)

        messageDao.insert(
            MessageEntity(
                contactUserId = contactUserId,
                isOutgoing = false,
                plaintext = String(plaintext, Charsets.UTF_8),
                timestamp = System.currentTimeMillis(),
            ),
        )
    }
}
