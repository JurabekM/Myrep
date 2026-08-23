package uz.distribos.data.db

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room jadvallari.
 *
 * Desktop sxemasining **rolga mos qismi**: telefon butun korxona bazasini
 * saqlamaydi (topshiriq §6). Agentga moliyaviy tarix, boshqa agentlarning
 * mijozlari va to'liq audit jurnali yuborilmaydi.
 *
 * Pul BUTUN son (tiyin) — `Long`. Miqdor esa MATN (`String`) sifatida
 * saqlanadi va `BigDecimal` orqali hisoblanadi: `Double` da 0.1+0.2
 * muammosi ombor qoldig'ini asta-sekin buzadi.
 */

@Entity(
    tableName = "product",
    indices = [Index("sku"), Index("barcode"), Index("name")],
)
data class ProductEntity(
    @PrimaryKey val id: String,
    val sku: String,
    val barcode: String?,
    val name: String,
    val unit: String,
    val wholesalePrice: Long,
    val retailPrice: Long,
    val agentPrice: Long,
    /** `BigDecimal` matn ko'rinishida — aniqlik yo'qolmasin. */
    val minStock: String,
    val isActive: Boolean,
    val updatedAtMs: Long,
)

@Entity(
    tableName = "customer",
    indices = [Index("code"), Index("name"), Index("assignedAgentId")],
)
data class CustomerEntity(
    @PrimaryKey val id: String,
    val code: String,
    val name: String,
    val kind: String,
    val phone: String?,
    val address: String?,
    val latitude: Double?,
    val longitude: Double?,
    val priceTier: String,
    val creditLimit: Long,
    val paymentTermDays: Int,
    val assignedAgentId: String?,
    val isActive: Boolean,
    val updatedAtMs: Long,
)

@Entity(
    tableName = "sales_order",
    indices = [Index("number", unique = true), Index("customerId"), Index("state")],
)
data class OrderEntity(
    @PrimaryKey val id: String,
    val number: String,
    val customerId: String,
    val warehouseId: String?,
    val agentId: String?,
    val state: String,
    val orderedAtMs: Long,
    val subtotal: Long,
    val discountTotal: Long,
    val total: Long,
    val paidTotal: Long,
    val currency: String,
    val note: String?,
    val updatedAtMs: Long,
)

@Entity(tableName = "order_line", indices = [Index("orderId"), Index("productId")])
data class OrderLineEntity(
    @PrimaryKey val id: String,
    val orderId: String,
    val productId: String,
    val quantity: String,
    val unitPrice: Long,
    val discountPercent: String,
    val lineTotal: Long,
)

@Entity(tableName = "warehouse")
data class WarehouseEntity(
    @PrimaryKey val id: String,
    val code: String,
    val name: String,
    val isActive: Boolean,
)

/**
 * Ombor harakati — APPEND-ONLY.
 *
 * Bu jadvalda UPDATE/DELETE yo'q. Qoldiq shu yerdan hisoblanadi
 * (`StockRules.computeStock`), hech qachon qo'lda yozilmaydi.
 */
@Entity(
    tableName = "inventory_movement",
    indices = [Index("warehouseId", "productId"), Index("occurredAtMs")],
)
data class MovementEntity(
    @PrimaryKey val id: String,
    val warehouseId: String,
    val productId: String,
    val movementType: String,
    val quantity: String,
    val unitCost: Long,
    val referenceType: String?,
    val referenceId: String?,
    val occurredAtMs: Long,
    val sourceEventId: String?,
    val note: String?,
)

/** Qoldiq keshi. HAQIQAT MANBAI EMAS — harakatlardan qayta hisoblanadi. */
@Entity(tableName = "stock_snapshot", primaryKeys = ["warehouseId", "productId"])
data class StockEntity(
    val warehouseId: String,
    val productId: String,
    val quantity: String,
    val reserved: String,
    val updatedAtMs: Long,
)

@Entity(tableName = "payment", indices = [Index("customerId"), Index("occurredAtMs")])
data class PaymentEntity(
    @PrimaryKey val id: String,
    val number: String,
    val direction: String,
    val customerId: String?,
    val amount: Long,
    val currency: String,
    val method: String,
    val occurredAtMs: Long,
    val reversesPaymentId: String?,
    val isReversed: Boolean,
    val note: String?,
)

@Entity(tableName = "visit", indices = [Index("customerId"), Index("startedAtMs")])
data class VisitEntity(
    @PrimaryKey val id: String,
    val customerId: String,
    val agentId: String,
    val routeId: String?,
    val startedAtMs: Long?,
    val finishedAtMs: Long?,
    val outcome: String?,
    val latitude: Double?,
    val longitude: Double?,
    val photoPath: String?,
    val note: String?,
)

// --- sinxronizatsiya jadvallari -------------------------------------------

/**
 * Hodisa jurnali — o'zgarmas.
 *
 * `(deviceId, deviceSequence)` unique: anti-entropy shunga tayanadi va
 * dublikat yozuvni baza darajasida to'xtatadi.
 */
@Entity(
    tableName = "event_log",
    indices = [
        Index("eventId", unique = true),
        Index("deviceId", "deviceSequence", unique = true),
        Index("appliedAtMs"),
        Index("aggregateType", "aggregateId"),
    ],
)
data class EventEntity(
    @PrimaryKey(autoGenerate = true) val rowId: Long = 0,
    val eventId: String,
    val eventType: String,
    val schemaVersion: Int,
    val aggregateType: String,
    val aggregateId: String,
    val actorId: String?,
    val deviceId: ByteArray,
    val deviceSequence: Long,
    val occurredAtMs: Long,
    val logicalTimestamp: String,
    val correlationId: String?,
    val causationId: String?,
    val idempotencyKey: String?,
    /** CBOR kodlangan payload. */
    val payload: ByteArray,
    val isLocal: Boolean,
    val appliedAtMs: Long?,
    val projectionAttempts: Int = 0,
) {
    override fun equals(other: Any?): Boolean =
        this === other || (other is EventEntity && eventId == other.eventId)

    override fun hashCode(): Int = eventId.hashCode()
}

/** Yuborilishi kerak bo'lgan hodisalar. */
@Entity(tableName = "outbox", indices = [Index("eventId", unique = true), Index("state")])
data class OutboxEntity(
    @PrimaryKey(autoGenerate = true) val rowId: Long = 0,
    val eventId: String,
    val state: String,
    val channel: String,
    val attempts: Int,
    val lastAttemptAtMs: Long?,
    val nextAttemptAtMs: Long?,
    val lastError: String?,
    val createdAtMs: Long,
)

/** Qabul qilingan hodisalar — deduplikatsiya reyestri. */
@Entity(
    tableName = "inbox",
    indices = [Index("eventId", unique = true), Index("senderDeviceId", "senderSequence")],
)
data class InboxEntity(
    @PrimaryKey(autoGenerate = true) val rowId: Long = 0,
    val eventId: String,
    val senderDeviceId: ByteArray,
    val senderSequence: Long,
    val epoch: Int,
    val receivedAtMs: Long,
    val duplicateCount: Int = 0,
) {
    override fun equals(other: Any?): Boolean =
        this === other || (other is InboxEntity && eventId == other.eventId)

    override fun hashCode(): Int = eventId.hashCode()
}

/** Tanilgan qurilmalar. */
@Entity(tableName = "peer_device")
data class PeerDeviceEntity(
    @PrimaryKey val deviceIdHex: String,
    val displayName: String,
    val platform: String,
    val role: String,
    val state: String,
    val signPublicKey: ByteArray,
    val kemPublicKey: ByteArray,
    val lastSeenAtMs: Long?,
    val lastAppliedSequence: Long,
    val isFullReplica: Boolean,
    val revokedReason: String?,
) {
    override fun equals(other: Any?): Boolean =
        this === other || (other is PeerDeviceEntity && deviceIdHex == other.deviceIdHex)

    override fun hashCode(): Int = deviceIdHex.hashCode()
}

/** Epoch kaliti. `rootSecretWrapped` — Android Keystore bilan o'ralgan. */
@Entity(tableName = "epoch_key", primaryKeys = ["epoch", "keyId"])
data class EpochKeyEntity(
    val epoch: Int,
    val keyId: Long,
    val rootSecretWrapped: ByteArray,
    val profileId: Int,
    val isCurrent: Boolean,
    val createdAtMs: Long,
) {
    override fun equals(other: Any?): Boolean =
        this === other || (other is EpochKeyEntity && epoch == other.epoch && keyId == other.keyId)

    override fun hashCode(): Int = 31 * epoch + keyId.hashCode()
}

/** Anti-replay oynasi (AETHER-Q N5/S6). */
@Entity(tableName = "replay_window", primaryKeys = ["epoch", "deviceIdHex"])
data class ReplayWindowEntity(
    val epoch: Int,
    val deviceIdHex: String,
    val highestSequence: Long,
    val bitmap: ByteArray,
    val updatedAtMs: Long,
) {
    override fun equals(other: Any?): Boolean =
        this === other ||
            (other is ReplayWindowEntity && epoch == other.epoch && deviceIdHex == other.deviceIdHex)

    override fun hashCode(): Int = 31 * epoch + deviceIdHex.hashCode()
}

/** Bu qurilmaning o'z monotonik hisoblagichi. Bitta qator. */
@Entity(tableName = "device_sequence")
data class DeviceSequenceEntity(
    @PrimaryKey val deviceIdHex: String,
    val nextSequence: Long,
)

/** Qo'llab bo'lmagan xabarlar — jimgina tashlanmaydi. */
@Entity(tableName = "dead_letter")
data class DeadLetterEntity(
    @PrimaryKey(autoGenerate = true) val rowId: Long = 0,
    val eventId: String?,
    val channel: String,
    val reason: String,
    val detail: String?,
    val rawSizeBytes: Int,
    val occurredAtMs: Long,
    val resolvedAtMs: Long?,
)

/** Aniqlangan konflikt — avtomatik yashirilmaydi. */
@Entity(tableName = "conflict")
data class ConflictEntity(
    @PrimaryKey(autoGenerate = true) val rowId: Long = 0,
    val aggregateType: String,
    val aggregateId: String,
    val strategy: String,
    val status: String,
    val resolution: String?,
    val localValue: String?,
    val remoteValue: String?,
    val detectedAtMs: Long,
)
