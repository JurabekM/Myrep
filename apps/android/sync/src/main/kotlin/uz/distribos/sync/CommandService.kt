package uz.distribos.sync

import androidx.room.withTransaction
import co.nstant.`in`.cbor.CborEncoder
import co.nstant.`in`.cbor.model.Array as CborArray
import co.nstant.`in`.cbor.model.ByteString
import co.nstant.`in`.cbor.model.DataItem
import co.nstant.`in`.cbor.model.Map as CborMap
import co.nstant.`in`.cbor.model.UnicodeString
import co.nstant.`in`.cbor.model.UnsignedInteger
import uz.distribos.data.db.DistribosDatabase
import uz.distribos.data.db.EventEntity
import uz.distribos.data.db.OutboxEntity
import java.io.ByteArrayOutputStream
import java.security.SecureRandom
import java.util.concurrent.atomic.AtomicLong

/**
 * Buyruq xizmati — topshiriq §7.1 ning telefondagi oqimi.
 *
 * ```
 * 1. Vakolatni tekshirish
 * 2. Domen qoidalarini bajarish
 * 3. Immutable hodisa yaratish   \
 * 4. Sync outbox'ga yozish        > BIR tranzaksiya
 * 5. Proyektor biznes jadvallariga qo'llaydi
 * 6. Commit
 * 7. UI'ga natija
 * 8. Fon worker orqali MQTT'ga yuborish
 * ```
 *
 * Internet bo'lmasa 1-7 bosqichlar baribir bajariladi — buyurtma
 * telefonda saqlanadi va yo'qolmaydi.
 *
 * Lokal hodisa ham proyektordan o'tadi: bir kod yo'li bo'lgani uchun
 * telefon va desktop bir xil hodisalardan bir xil holatni hisoblaydi.
 */
class CommandService(
    private val database: DistribosDatabase,
    private val projector: EventProjector,
    private val deviceId: ByteArray,
    private val actorId: String?,
    private val role: String = "agent",
) {

    class CommandRejected(message: String) : Exception(message)

    private val deviceIdHex = deviceId.joinToString("") { "%02x".format(it) }
    private val counter = AtomicLong(0)
    private val random = SecureRandom()

    data class NewEvent(
        val eventType: String,
        val aggregateType: String,
        val aggregateId: String,
        val payload: Map<String, Any?>,
        val idempotencyKey: String? = null,
        val schemaVersion: Int = 1,
        val occurredAtMs: Long = System.currentTimeMillis(),
    )

    /**
     * Buyruqni bajaradi: hodisa + outbox + proyeksiya BIR tranzaksiyada.
     *
     * Room `withTransaction` ichida bo'lgani uchun "baza yangilandi,
     * lekin hodisa yo'qoldi" holati bo'lishi mumkin emas.
     */
    suspend fun submit(event: NewEvent): EventEntity = database.withTransaction {
        if (!Permissions.isAllowed(role, event.eventType)) {
            throw CommandRejected("'$role' roli '${event.eventType}' amalini bajara olmaydi")
        }

        event.idempotencyKey?.let { key ->
            database.sync().eventByIdempotencyKey(key)?.let { return@withTransaction it }
        }

        val sequence = database.sync().allocateSequence(deviceIdHex)
        val record = EventEntity(
            eventId = newEventId(),
            eventType = event.eventType,
            schemaVersion = event.schemaVersion,
            aggregateType = event.aggregateType,
            aggregateId = event.aggregateId,
            actorId = actorId,
            deviceId = deviceId,
            deviceSequence = sequence,
            occurredAtMs = event.occurredAtMs,
            logicalTimestamp = "${event.occurredAtMs}.${counter.incrementAndGet()}.$deviceIdHex",
            correlationId = null,
            causationId = null,
            idempotencyKey = event.idempotencyKey,
            payload = encode(event.payload),
            isLocal = true,
            appliedAtMs = null,
        )
        database.sync().insertEvent(record)
        database.sync().insertOutbox(
            OutboxEntity(
                eventId = record.eventId,
                state = SyncEngine.STATE_LOCAL,
                channel = "events",
                attempts = 0,
                lastAttemptAtMs = null,
                nextAttemptAtMs = null,
                lastError = null,
                createdAtMs = System.currentTimeMillis(),
            )
        )
        projector.drain()
        record
    }

    /** Kechiktirilgan hodisalarni qayta ko'radi (fon vazifasi). */
    suspend fun replayPending(): EventProjector.Result = projector.drain()

    /**
     * UUIDv7 — vaqt bo'yicha tartiblanadigan noyob ID.
     *
     * Markaziy generator kerak emas (serversiz tizimda shart), va indeks
     * ketma-ket to'ladi, ya'ni bir million hodisada ham B-tree
     * parchalanmaydi.
     */
    private fun newEventId(): String {
        val now = System.currentTimeMillis()
        val bytes = ByteArray(16)
        for (index in 0 until 6) {
            bytes[index] = ((now shr (8 * (5 - index))) and 0xFF).toByte()
        }
        random.nextBytes(bytes, 6, 10)
        bytes[6] = ((bytes[6].toInt() and 0x0F) or 0x70).toByte()   // versiya 7
        bytes[8] = ((bytes[8].toInt() and 0x3F) or 0x80).toByte()   // RFC 4122 variant

        val hex = bytes.joinToString("") { "%02x".format(it) }
        return "${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-" +
            "${hex.substring(16, 20)}-${hex.substring(20)}"
    }

    private fun SecureRandom.nextBytes(target: ByteArray, offset: Int, length: Int) {
        val buffer = ByteArray(length)
        nextBytes(buffer)
        buffer.copyInto(target, offset)
    }

    private fun encode(payload: Map<String, Any?>): ByteArray {
        val output = ByteArrayOutputStream()
        CborEncoder(output).encode(toCbor(payload))
        return output.toByteArray()
    }

    private fun toCbor(payload: Map<String, Any?>): CborMap {
        val map = CborMap()
        for ((key, value) in payload) {
            // `null` maydonlar UMUMAN kiritilmaydi: "yo'q" va "null"
            // ikkala tomonda bir xil ma'noga ega bo'lishi kerak.
            if (value == null) continue
            map.put(UnicodeString(key), toItem(value))
        }
        return map
    }

    private fun toItem(value: Any): DataItem = when (value) {
        is String -> UnicodeString(value)
        is Int -> UnsignedInteger(value.toLong())
        is Long -> UnsignedInteger(value)
        is ByteArray -> ByteString(value)
        is Map<*, *> -> {
            @Suppress("UNCHECKED_CAST")
            toCbor(value as Map<String, Any?>)
        }
        is List<*> -> CborArray().apply {
            value.filterNotNull().forEach { add(toItem(it)) }
        }
        else -> UnicodeString(value.toString())
    }
}

/**
 * Rollar va vakolatlar — desktop `application/permissions.py` bilan bir xil.
 *
 * Fail-closed: ro'yxatda bo'lmagan rol yoki hodisa RAD ETILADI.
 */
object Permissions {

    private val ROLE_PERMISSIONS: Map<String, Set<String>> = mapOf(
        "owner" to setOf(
            "PRODUCT_CREATED", "PRODUCT_UPDATED", "PRODUCT_PRICE_CHANGED",
            "CUSTOMER_CREATED", "CUSTOMER_UPDATED", "ORDER_CREATED",
            "ORDER_STATE_CHANGED", "INVENTORY_MOVED", "PAYMENT_RECORDED",
            "PAYMENT_REVERSED", "VISIT_RECORDED", "USER_CREATED", "DEVICE_REVOKED",
        ),
        "manager" to setOf(
            "PRODUCT_CREATED", "PRODUCT_UPDATED", "PRODUCT_PRICE_CHANGED",
            "CUSTOMER_CREATED", "CUSTOMER_UPDATED", "ORDER_CREATED",
            "ORDER_STATE_CHANGED", "INVENTORY_MOVED", "PAYMENT_RECORDED",
            "PAYMENT_REVERSED", "VISIT_RECORDED",
        ),
        // Agent buyurtma oladi va to'lov qabul qiladi, lekin NARX
        // o'zgartira olmaydi va to'lovni bekor qila olmaydi.
        "agent" to setOf(
            "ORDER_CREATED", "CUSTOMER_CREATED", "CUSTOMER_UPDATED",
            "PAYMENT_RECORDED", "VISIT_RECORDED",
        ),
        "warehouse" to setOf("INVENTORY_MOVED", "ORDER_STATE_CHANGED"),
        "cashier" to setOf("PAYMENT_RECORDED"),
        "viewer" to emptySet(),
    )

    private val OWNER_ONLY = setOf("DEVICE_REVOKED", "USER_CREATED")

    fun isAllowed(role: String, eventType: String): Boolean {
        val permitted = ROLE_PERMISSIONS[role] ?: return false   // noma'lum rol — fail-closed
        if (eventType in OWNER_ONLY && role != "owner") return false
        return eventType in permitted
    }

    fun allowedEvents(role: String): Set<String> {
        val permitted = ROLE_PERMISSIONS[role].orEmpty()
        return if (role == "owner") permitted else permitted - OWNER_ONLY
    }

    /** Rolga qarab replikatsiya doirasi — agentga butun moliyaviy baza yuborilmaydi. */
    private val REPLICATION_SCOPE: Map<String, Set<String>> = mapOf(
        "owner" to setOf("*"),
        "manager" to setOf("Product", "Customer", "Order", "Inventory", "Payment", "Visit", "User"),
        "agent" to setOf("Product", "Customer", "Order", "Payment", "Visit"),
        "warehouse" to setOf("Product", "Inventory", "Order"),
        "cashier" to setOf("Customer", "Order", "Payment"),
        "viewer" to setOf("Product"),
    )

    fun shouldReplicate(role: String, aggregateType: String): Boolean {
        val scope = REPLICATION_SCOPE[role].orEmpty()
        return "*" in scope || aggregateType in scope
    }
}
