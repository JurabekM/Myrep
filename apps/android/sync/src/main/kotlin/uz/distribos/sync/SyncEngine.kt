package uz.distribos.sync

import co.nstant.`in`.cbor.CborBuilder
import co.nstant.`in`.cbor.CborDecoder
import co.nstant.`in`.cbor.CborEncoder
import co.nstant.`in`.cbor.model.Array as CborArray
import co.nstant.`in`.cbor.model.ByteString
import co.nstant.`in`.cbor.model.DataItem
import co.nstant.`in`.cbor.model.Map as CborMap
import co.nstant.`in`.cbor.model.UnicodeString
import co.nstant.`in`.cbor.model.UnsignedInteger
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import uz.distribos.crypto.AetherQException
import uz.distribos.crypto.ContentType
import uz.distribos.data.db.DeadLetterEntity
import uz.distribos.data.db.EventEntity
import uz.distribos.data.db.InboxEntity
import uz.distribos.data.db.OutboxEntity
import uz.distribos.data.db.SyncDao
import java.io.ByteArrayOutputStream

/**
 * Sinxronizatsiya dvigateli — outbox, inbox, ACK va anti-entropy.
 *
 * Ikkita ajratish qat'iy saqlanadi:
 *
 * * **transport ACK ≠ biznes ACK.** Broker PUBACK bergani hodisa peer'da
 *   qo'llandi degani emas.
 * * **broker tarixiga tayanmaymiz.** Yo'qolgan hodisa broker'dan emas,
 *   peer bilan digest almashuvi orqali tiklanadi.
 */
class SyncEngine(
    private val dao: SyncDao,
    private val provider: AndroidAetherQProvider,
    private val transport: MqttTransport,
    private val projector: EventProjector,
    private val deviceId: ByteArray,
) {

    private val deviceIdHex: String = deviceId.joinToString("") { "%02x".format(it) }

    data class Stats(
        val publishedEvents: Long = 0,
        val receivedEvents: Long = 0,
        val duplicates: Long = 0,
        val applied: Long = 0,
        val conflicts: Long = 0,
        val rejected: Long = 0,
        val rejections: Map<String, Int> = emptyMap(),
    )

    private val _stats = MutableStateFlow(Stats())
    val stats: StateFlow<Stats> = _stats.asStateFlow()

    private val publishLock = Mutex()

    // --- chiqish yo'nalishi -----------------------------------------------

    /**
     * Outbox'dagi hodisalarni batch qilib yuboradi.
     *
     * Yuborilmasa (offline) outbox TEGILMAYDI — hodisa yo'qolmaydi.
     * ML-DSA imzosi 3309 bayt, shuning uchun batch SHART.
     */
    suspend fun publishPending(limit: Int = MAX_BATCH): Int = publishLock.withLock {
        if (!transport.isConnected()) return 0

        // Ulanmagan qurilma HECH NARSA yubormaydi. Uning kompaniyasi
        // hali yo'q — vaqtinchalik, o'zi o'ylab topgan manzil bor xolos.
        // U yerga yozish foydasiz (hech kim eshitmaydi) va zararli
        // (ochiq brokerda keraksiz iz qoldiradi).
        //
        // Hodisalar YO'QOLMAYDI: ular outbox'da turadi va ulangandan
        // keyin odatdagidek yuboriladi.
        if (dao.activePeerCount(deviceIdHex) == 0) return 0

        val now = System.currentTimeMillis()
        val pending = dao.pendingOutbox(now, limit)
        if (pending.isEmpty()) return 0

        val events = pending.mapNotNull { dao.eventById(it.eventId) }
        if (events.isEmpty()) return 0

        val payload = encodeEventBatch(events)
        val sealed = try {
            provider.seal(payload, ContentType.EVENT_BATCH)
        } catch (exception: AetherQException) {
            markFailure(pending, exception.message.orEmpty())
            return 0
        }

        transport.publish(sealed, Topics.Channel.EVENTS)

        for (entry in pending) {
            dao.updateOutbox(
                entry.copy(
                    state = STATE_PUBLISHED,
                    attempts = entry.attempts + 1,
                    lastAttemptAtMs = now,
                    lastError = null,
                )
            )
        }
        _stats.value = _stats.value.copy(
            publishedEvents = _stats.value.publishedEvents + events.size
        )
        return events.size
    }

    private suspend fun markFailure(entries: List<OutboxEntity>, error: String) {
        val now = System.currentTimeMillis()
        for (entry in entries) {
            val attempts = entry.attempts + 1
            val deadLettered = attempts >= MAX_ATTEMPTS
            dao.updateOutbox(
                entry.copy(
                    state = if (deadLettered) STATE_DEAD_LETTER else entry.state,
                    attempts = attempts,
                    lastAttemptAtMs = now,
                    lastError = error.take(500),
                    nextAttemptAtMs = now + backoffMillis(attempts),
                )
            )
            if (deadLettered) {
                // Jimgina tashlanmaydi — diagnostikada ko'rinadi.
                dao.insertDeadLetter(
                    DeadLetterEntity(
                        eventId = entry.eventId, channel = entry.channel,
                        reason = "MAX_ATTEMPTS", detail = error.take(500),
                        rawSizeBytes = 0, occurredAtMs = now, resolvedAtMs = null,
                    )
                )
            }
        }
    }

    // --- kirish yo'nalishi ------------------------------------------------

    suspend fun handleInbound(wire: ByteArray, channel: Topics.Channel? = null) {
        // O'Z AKS-SADOMIZ — muhrni OCHMASDAN tashlanadi. Ochishga
        // urinish replay oynasiga tushadi va SOXTA hujum yozuvi
        // yaratadi (jonli sinovda 3 daqiqada 83 ta).
        if (uz.distribos.crypto.Des1.peekSenderDeviceId(wire)?.contentEquals(deviceId) == true) {
            return
        }

        val opened = try {
            provider.open(wire)
        } catch (exception: AetherQException) {
            noteRejection(exception.reason.name)
            // Kim yuborganini YOZAMIZ. Busiz «xabar rad etildi» yozuvi
            // bilan hech nima qilib bo'lmaydi: qaysi qurilma, qaysi
            // ketma-ketlik — hech biri ko'rinmaydi. Qiymat
            // autentifikatsiyalanmagan, shuning uchun u faqat
            // DIAGNOSTIKA uchun va qaror qabul qilishda ishlatilmaydi.
            val sender = uz.distribos.crypto.Des1.peekSenderDeviceId(wire)
                ?.joinToString("") { "%02x".format(it) }?.take(12)
            dao.insertDeadLetter(
                DeadLetterEntity(
                    eventId = null, channel = channel?.value ?: "unknown",
                    reason = exception.reason.name,
                    detail = if (sender != null) "yuboruvchi $sender" else null,
                    rawSizeBytes = wire.size, occurredAtMs = System.currentTimeMillis(),
                    resolvedAtMs = null,
                )
            )
            return
        }

        // Ikkinchi to'siq — endi AUTENTIFIKATSIYALANGAN qiymat bo'yicha.
        // Yuqoridagi tekshiruv tez, lekin ishonchsiz headerga tayanadi;
        // bu esa qat'iy. Ikkalasi ham kerak.
        if (opened.senderDeviceId.contentEquals(deviceId)) return

        when (opened.contentType) {
            ContentType.EVENT_BATCH -> handleEventBatch(opened)
            ContentType.ACK -> handleAck(opened)
            ContentType.SYNC_DIGEST -> handleDigest(opened)
            ContentType.SYNC_REQUEST -> handleSyncRequest(opened)
            else -> Unit
        }
    }

    private suspend fun handleEventBatch(opened: AndroidAetherQProvider.Opened) {
        val events = try {
            decodeEventBatch(opened.payload)
        } catch (_: Exception) {
            noteRejection("SCHEMA_INVALID")
            return
        }

        val appliedIds = mutableListOf<String>()
        for (event in events) {
            _stats.value = _stats.value.copy(receivedEvents = _stats.value.receivedEvents + 1)

            val existing = dao.inboxEntry(event.eventId)
            if (existing != null) {
                // Takror — biznes natijasi IKKINCHI marta qo'llanmaydi.
                dao.updateInbox(existing.copy(duplicateCount = existing.duplicateCount + 1))
                _stats.value = _stats.value.copy(duplicates = _stats.value.duplicates + 1)
                appliedIds += event.eventId
                continue
            }

            dao.insertInbox(
                InboxEntity(
                    eventId = event.eventId,
                    senderDeviceId = opened.senderDeviceId,
                    senderSequence = event.deviceSequence,
                    epoch = opened.epoch,
                    receivedAtMs = System.currentTimeMillis(),
                )
            )
            try {
                dao.insertEvent(event.copy(isLocal = false, appliedAtMs = null))
            } catch (_: Exception) {
                // `(deviceId, deviceSequence)` unique — dublikat baza
                // darajasida to'xtatildi. Bu normal, xato emas.
            }
            appliedIds += event.eventId
        }

        // Butun batch yozilgandan KEYIN qo'llaymiz: batch ichida hodisa
        // o'z ota-onasidan oldin turishi mumkin, `drain` tartibni o'zi
        // hal qiladi.
        val result = projector.drain()
        _stats.value = _stats.value.copy(
            applied = _stats.value.applied + result.applied,
            conflicts = _stats.value.conflicts + result.conflicts,
        )

        advanceCheckpoint(opened.senderDeviceId, events.map { it.deviceSequence })

        if (appliedIds.isNotEmpty()) sendAck(opened.senderDeviceId, appliedIds)
    }

    /**
     * Peer bo'yicha checkpoint faqat UZLUKSIZ ketma-ketlik uchun suriladi.
     *
     * Agar 5 va 7 kelib 6 kelmagan bo'lsa, checkpoint 5 da qoladi — aks
     * holda 6 abadiy yo'qolardi.
     */
    private suspend fun advanceCheckpoint(peerDeviceId: ByteArray, sequences: List<Long>) {
        if (sequences.isEmpty()) return
        val hex = peerDeviceId.joinToString("") { "%02x".format(it) }
        val peer = dao.peer(hex) ?: return

        var current = peer.lastAppliedSequence
        for (sequence in sequences.sorted()) {
            when {
                sequence == current + 1 -> current += 1
                sequence <= current -> Unit
                else -> break   // bo'shliq bor
            }
        }
        dao.upsertPeer(
            peer.copy(lastAppliedSequence = current, lastSeenAtMs = System.currentTimeMillis())
        )
    }

    // --- ACK --------------------------------------------------------------

    private suspend fun sendAck(target: ByteArray, eventIds: List<String>) {
        if (!transport.isConnected()) return
        try {
            val payload = encodeStringList("applied", eventIds)
            transport.publish(
                provider.seal(payload, ContentType.ACK), Topics.Channel.ACKS, targetDeviceId = target
            )
        } catch (_: Exception) {
            // ACK yetkazilmasa ham hodisa qo'llangan — peer keyingi
            // digest almashuvida buni aniqlaydi.
        }
    }

    private suspend fun handleAck(opened: AndroidAetherQProvider.Opened) {
        val applied = try {
            decodeStringList(opened.payload, "applied")
        } catch (_: Exception) {
            return
        }
        for (entry in dao.outboxFor(applied)) {
            dao.updateOutbox(entry.copy(state = STATE_PEER_APPLIED))
        }
    }

    // --- anti-entropy ------------------------------------------------------

    suspend fun buildDigest(): Map<String, Long> =
        dao.digest().associate { row ->
            row.deviceId.joinToString("") { "%02x".format(it) } to row.highest
        }

    suspend fun sendDigest() {
        if (!transport.isConnected()) return
        val digest = buildDigest()
        transport.publish(
            provider.seal(encodeDigest(digest), ContentType.SYNC_DIGEST),
            Topics.Channel.SYNC_REQUESTS,
        )
    }

    /**
     * Peer digest'ini ko'rib IKKI tomonlama ish qiladi: bizda yo'qni
     * so'raymiz VA peer'da yo'qni yuboramiz.
     *
     * Faqat tortish bo'lsa, hodisani YO'QOTGAN tomon o'zi digest
     * yuborishi kerak bo'lardi — lekin u nimani yo'qotganini bilmaydi.
     */
    private suspend fun handleDigest(opened: AndroidAetherQProvider.Opened) {
        if (!transport.isConnected()) return
        val remote = try {
            decodeDigest(opened.payload)
        } catch (_: Exception) {
            return
        }
        val local = buildDigest()

        val wanted = remote.filter { (device, highest) -> highest > (local[device] ?: 0L) }
            .mapValues { (device, highest) -> ((local[device] ?: 0L) + 1) to highest }
        if (wanted.isNotEmpty()) {
            transport.publish(
                provider.seal(encodeRanges(wanted), ContentType.SYNC_REQUEST),
                Topics.Channel.SYNC_REQUESTS, targetDeviceId = opened.senderDeviceId,
            )
        }

        val missingForPeer = local.filter { (device, highest) -> highest > (remote[device] ?: 0L) }
            .mapValues { (device, highest) -> ((remote[device] ?: 0L) + 1) to highest }
        if (missingForPeer.isNotEmpty()) {
            pushRanges(missingForPeer, opened.senderDeviceId)
        }
    }

    private suspend fun handleSyncRequest(opened: AndroidAetherQProvider.Opened) {
        if (!transport.isConnected()) return
        val ranges = try {
            decodeRanges(opened.payload)
        } catch (_: Exception) {
            return
        }
        pushRanges(ranges, opened.senderDeviceId)
    }

    private suspend fun pushRanges(
        ranges: Map<String, Pair<Long, Long>>, target: ByteArray,
    ) {
        val batch = mutableListOf<EventEntity>()
        for ((deviceHex, range) in ranges) {
            val bytes = deviceHex.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
            batch += dao.eventsInRange(bytes, range.first, range.second, MAX_BATCH)
        }
        if (batch.isEmpty()) return

        // Qayta muhrlanadi (yangi nonce — replay oynasidan o'tadi), lekin
        // `eventId` o'zgarmaydi, ya'ni qabul qiluvchi dedup qiladi.
        transport.publish(
            provider.seal(encodeEventBatch(batch), ContentType.EVENT_BATCH),
            Topics.Channel.SYNC_RESPONSES, targetDeviceId = target,
        )
    }

    // --- diagnostika -------------------------------------------------------

    private fun noteRejection(reason: String) {
        val current = _stats.value
        _stats.value = current.copy(
            rejected = current.rejected + 1,
            rejections = current.rejections + (reason to (current.rejections[reason] ?: 0) + 1),
        )
    }

    suspend fun queueDepth(): Pair<Int, Int> = dao.queueDepth() to dao.deadLetterCount()

    // --- CBOR kodlash ------------------------------------------------------

    private fun encodeEventBatch(events: List<EventEntity>): ByteArray {
        val output = ByteArrayOutputStream()
        val array = CborArray()
        for (event in events) {
            val map = CborMap()
            map.put(UnicodeString("event_id"), UnicodeString(event.eventId))
            map.put(UnicodeString("event_type"), UnicodeString(event.eventType))
            map.put(UnicodeString("schema_version"), UnsignedInteger(event.schemaVersion.toLong()))
            map.put(UnicodeString("aggregate_type"), UnicodeString(event.aggregateType))
            map.put(UnicodeString("aggregate_id"), UnicodeString(event.aggregateId))
            map.put(UnicodeString("device_sequence"), UnsignedInteger(event.deviceSequence))
            map.put(UnicodeString("occurred_at_ms"), UnsignedInteger(event.occurredAtMs))
            map.put(UnicodeString("logical_timestamp"), UnicodeString(event.logicalTimestamp))
            map.put(UnicodeString("payload"), ByteString(event.payload))
            event.actorId?.let { map.put(UnicodeString("actor_id"), UnicodeString(it)) }
            event.idempotencyKey?.let {
                map.put(UnicodeString("idempotency_key"), UnicodeString(it))
            }
            array.add(map)
        }
        val root = CborMap()
        root.put(UnicodeString("events"), array)
        CborEncoder(output).encode(root)
        return output.toByteArray()
    }

    private fun decodeEventBatch(payload: ByteArray): List<EventEntity> {
        val root = CborDecoder.decode(payload).first() as CborMap
        val array = root.get(UnicodeString("events")) as CborArray
        return array.dataItems.map { item ->
            val map = item as CborMap
            EventEntity(
                eventId = map.text("event_id"),
                eventType = map.text("event_type"),
                schemaVersion = map.number("schema_version").toInt(),
                aggregateType = map.text("aggregate_type"),
                aggregateId = map.text("aggregate_id"),
                actorId = map.optionalText("actor_id"),
                deviceId = ByteArray(0),   // jo'natuvchi envelope'dan olinadi
                deviceSequence = map.number("device_sequence"),
                occurredAtMs = map.number("occurred_at_ms"),
                logicalTimestamp = map.text("logical_timestamp"),
                correlationId = null,
                causationId = null,
                idempotencyKey = map.optionalText("idempotency_key"),
                payload = (map.get(UnicodeString("payload")) as ByteString).bytes,
                isLocal = false,
                appliedAtMs = null,
            )
        }
    }

    private fun encodeStringList(key: String, values: List<String>): ByteArray {
        val output = ByteArrayOutputStream()
        CborEncoder(output).encode(
            CborBuilder().addMap()
                .putArray(key).apply { values.forEach { add(it) } }.end()
                .end().build()
        )
        return output.toByteArray()
    }

    private fun decodeStringList(payload: ByteArray, key: String): List<String> {
        val root = CborDecoder.decode(payload).first() as CborMap
        val array = root.get(UnicodeString(key)) as CborArray
        return array.dataItems.map { (it as UnicodeString).string }
    }

    private fun encodeDigest(digest: Map<String, Long>): ByteArray {
        val output = ByteArrayOutputStream()
        val inner = CborMap()
        digest.forEach { (device, highest) ->
            inner.put(UnicodeString(device), UnsignedInteger(highest))
        }
        val root = CborMap()
        root.put(UnicodeString("digest"), inner)
        CborEncoder(output).encode(root)
        return output.toByteArray()
    }

    private fun decodeDigest(payload: ByteArray): Map<String, Long> {
        val root = CborDecoder.decode(payload).first() as CborMap
        val inner = root.get(UnicodeString("digest")) as CborMap
        return inner.keys.associate { key ->
            (key as UnicodeString).string to (inner.get(key) as UnsignedInteger).value.toLong()
        }
    }

    private fun encodeRanges(ranges: Map<String, Pair<Long, Long>>): ByteArray {
        val output = ByteArrayOutputStream()
        val inner = CborMap()
        ranges.forEach { (device, range) ->
            val pair = CborArray()
            pair.add(UnsignedInteger(range.first))
            pair.add(UnsignedInteger(range.second))
            inner.put(UnicodeString(device), pair)
        }
        val root = CborMap()
        root.put(UnicodeString("ranges"), inner)
        CborEncoder(output).encode(root)
        return output.toByteArray()
    }

    private fun decodeRanges(payload: ByteArray): Map<String, Pair<Long, Long>> {
        val root = CborDecoder.decode(payload).first() as CborMap
        val inner = root.get(UnicodeString("ranges")) as CborMap
        return inner.keys.associate { key ->
            val pair = inner.get(key) as CborArray
            (key as UnicodeString).string to (
                (pair.dataItems[0] as UnsignedInteger).value.toLong() to
                    (pair.dataItems[1] as UnsignedInteger).value.toLong()
                )
        }
    }

    private fun CborMap.text(key: String): String =
        (get(UnicodeString(key)) as UnicodeString).string

    private fun CborMap.optionalText(key: String): String? =
        (get(UnicodeString(key)) as? UnicodeString)?.string

    private fun CborMap.number(key: String): Long =
        (get(UnicodeString(key)) as UnsignedInteger).value.toLong()

    companion object {
        const val MAX_BATCH = 50
        const val MAX_ATTEMPTS = 8

        const val STATE_LOCAL = "LOCAL_COMMITTED"
        const val STATE_PUBLISHED = "MQTT_PUBLISHED"
        const val STATE_PEER_APPLIED = "PEER_APPLIED"
        const val STATE_DEAD_LETTER = "DEAD_LETTER"

        fun backoffMillis(attempts: Int): Long =
            minOf(3_600_000L, 1_000L shl minOf(attempts, 12))
    }
}

private fun DataItem.asMap(): CborMap = this as CborMap
