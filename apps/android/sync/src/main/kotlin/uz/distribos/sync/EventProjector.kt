package uz.distribos.sync

import co.nstant.`in`.cbor.CborDecoder
import co.nstant.`in`.cbor.model.ByteString
import co.nstant.`in`.cbor.model.Map as CborMap
import co.nstant.`in`.cbor.model.Number as CborNumber
import co.nstant.`in`.cbor.model.UnicodeString
import uz.distribos.data.db.ConflictEntity
import uz.distribos.data.db.CustomerEntity
import uz.distribos.data.db.DistribosDatabase
import uz.distribos.data.db.EventEntity
import uz.distribos.data.db.MovementEntity
import uz.distribos.data.db.OrderEntity
import uz.distribos.data.db.OrderLineEntity
import uz.distribos.data.db.PaymentEntity
import uz.distribos.data.db.ProductEntity
import uz.distribos.data.db.StockEntity
import uz.distribos.data.db.VisitEntity
import uz.distribos.domain.MovementType
import uz.distribos.domain.OrderRules
import uz.distribos.domain.OrderState
import uz.distribos.domain.PricingRules
import uz.distribos.domain.StockRules

/**
 * Deterministik proyektor — hodisalarni Room jadvallariga qo'llaydi.
 *
 * Desktopdagi `application/projector.py` bilan bir xil qoidalar:
 *
 * 1. Qoldiq va moliya — append-only, tartibga bog'liq emas.
 * 2. Katalog va mijoz — HLC bo'yicha eng kech tamg'a yutadi.
 * 3. Buyurtma holati — holat mashinasi; noqonuniy o'tish konflikt.
 *
 * Lokal va uzoq hodisa BIR XIL yo'ldan o'tadi — shuning uchun telefon
 * va desktop bir xil hodisalardan bir xil holatni hisoblaydi.
 */
class EventProjector(private val database: DistribosDatabase) {

    data class Result(
        val applied: Int = 0,
        val deferred: Int = 0,
        val conflicts: Int = 0,
    )

    private enum class Outcome { APPLIED, DEFERRED, CONFLICT }

    /**
     * Qo'llanmagan hodisalarni qayta-qayta ko'radi.
     *
     * Har o'tishda kamida bittasi qo'llansa, keyingi o'tishda unga
     * bog'liq kechiktirilganlar ham qo'llanishi mumkin. Hech narsa
     * o'zgarmasa to'xtaymiz — cheksiz aylanish yo'q.
     */
    suspend fun drain(passes: Int = 6, limit: Int = 200): Result {
        var total = Result()
        repeat(passes) {
            val pending = database.sync().unappliedEvents(limit)
            if (pending.isEmpty()) return total

            var applied = 0
            var deferred = 0
            var conflicts = 0

            for (event in pending) {
                when (apply(event)) {
                    Outcome.APPLIED -> applied++
                    Outcome.DEFERRED -> deferred++
                    Outcome.CONFLICT -> conflicts++
                }
            }
            total = Result(total.applied + applied, deferred, total.conflicts + conflicts)
            if (applied == 0 && conflicts == 0) return total
        }
        return total
    }

    private suspend fun apply(event: EventEntity): Outcome {
        val payload = try {
            decode(event.payload)
        } catch (_: Exception) {
            recordConflict(event, "CONTRACT", "payload o'qilmadi")
            markApplied(event)
            return Outcome.CONFLICT
        }

        val outcome = try {
            when (event.eventType) {
                "PRODUCT_CREATED" -> applyProduct(event, payload)
                "PRODUCT_PRICE_CHANGED" -> applyPriceChange(event, payload)
                "CUSTOMER_CREATED" -> applyCustomer(event, payload)
                "ORDER_CREATED" -> applyOrder(event, payload)
                "ORDER_STATE_CHANGED" -> applyOrderState(event, payload)
                "INVENTORY_MOVED" -> applyMovement(event, payload)
                "PAYMENT_RECORDED" -> applyPayment(event, payload)
                "PAYMENT_REVERSED" -> applyPaymentReversal(event, payload)
                "VISIT_RECORDED" -> applyVisit(event, payload)
                else -> {
                    // Noma'lum hodisa QABUL QILINMAYDI — bu eskirgan yoki
                    // soxta klient belgisi bo'lishi mumkin.
                    recordConflict(event, "UNKNOWN_TYPE", "qo'llovchi yo'q: ${event.eventType}")
                    Outcome.CONFLICT
                }
            }
        } catch (exception: Exception) {
            recordConflict(event, "APPLY_FAILED", exception.message.orEmpty().take(200))
            markApplied(event)
            return Outcome.CONFLICT
        }

        when (outcome) {
            Outcome.DEFERRED -> {
                val attempts = event.projectionAttempts + 1
                if (attempts >= MAX_ATTEMPTS) {
                    recordConflict(
                        event, "MISSING_PARENT",
                        "$attempts urinishdan keyin ham bog'liq yozuv topilmadi",
                    )
                    markApplied(event)
                    return Outcome.CONFLICT
                }
                database.sync().updateEvent(event.copy(projectionAttempts = attempts))
            }
            else -> markApplied(event)
        }
        return outcome
    }

    private suspend fun markApplied(event: EventEntity) {
        database.sync().updateEvent(event.copy(appliedAtMs = System.currentTimeMillis()))
    }

    private suspend fun recordConflict(event: EventEntity, strategy: String, detail: String) {
        database.sync().insertConflict(
            ConflictEntity(
                aggregateType = event.aggregateType,
                aggregateId = event.aggregateId,
                strategy = strategy,
                status = "NEEDS_REVIEW",
                resolution = detail,
                localValue = null,
                remoteValue = null,
                detectedAtMs = System.currentTimeMillis(),
            )
        )
    }

    // --- katalog ----------------------------------------------------------

    private suspend fun applyProduct(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("product_id") ?: return Outcome.CONFLICT
        val existing = database.products().byId(id)

        // Maydon darajasidagi HLC: kechroq tamg'a yutadi, kelish tartibi emas.
        if (existing != null && existing.updatedAtMs > event.occurredAtMs) return Outcome.APPLIED

        database.products().upsert(
            ProductEntity(
                id = id,
                sku = payload.string("sku") ?: existing?.sku.orEmpty(),
                barcode = payload.string("barcode") ?: existing?.barcode,
                name = payload.string("name") ?: existing?.name.orEmpty(),
                unit = payload.string("unit") ?: existing?.unit ?: "dona",
                wholesalePrice = payload.long("wholesale_price") ?: existing?.wholesalePrice ?: 0,
                retailPrice = payload.long("retail_price") ?: existing?.retailPrice ?: 0,
                agentPrice = payload.long("agent_price") ?: existing?.agentPrice ?: 0,
                minStock = payload.string("min_stock") ?: existing?.minStock ?: "0",
                isActive = true,
                updatedAtMs = event.occurredAtMs,
            )
        )
        return Outcome.APPLIED
    }

    private suspend fun applyPriceChange(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("product_id") ?: return Outcome.CONFLICT
        val product = database.products().byId(id) ?: return Outcome.DEFERRED
        if (product.updatedAtMs > event.occurredAtMs) return Outcome.APPLIED

        val price = payload.long("new_price") ?: return Outcome.CONFLICT
        val updated = when (payload.string("field")) {
            "wholesale_price" -> product.copy(wholesalePrice = price)
            "retail_price" -> product.copy(retailPrice = price)
            "agent_price" -> product.copy(agentPrice = price)
            else -> return Outcome.CONFLICT
        }
        database.products().upsert(updated.copy(updatedAtMs = event.occurredAtMs))
        return Outcome.APPLIED
    }

    private suspend fun applyCustomer(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("customer_id") ?: return Outcome.CONFLICT
        val existing = database.customers().byId(id)
        if (existing != null && existing.updatedAtMs > event.occurredAtMs) return Outcome.APPLIED

        database.customers().upsert(
            CustomerEntity(
                id = id,
                code = payload.string("code") ?: existing?.code.orEmpty(),
                name = payload.string("name") ?: existing?.name.orEmpty(),
                kind = payload.string("kind") ?: existing?.kind ?: "COMPANY",
                phone = payload.string("phone") ?: existing?.phone,
                address = payload.string("address") ?: existing?.address,
                latitude = payload.string("latitude")?.toDoubleOrNull() ?: existing?.latitude,
                longitude = payload.string("longitude")?.toDoubleOrNull() ?: existing?.longitude,
                priceTier = payload.string("price_tier") ?: existing?.priceTier ?: "wholesale",
                creditLimit = payload.long("credit_limit") ?: existing?.creditLimit ?: 0,
                paymentTermDays = payload.long("payment_term_days")?.toInt()
                    ?: existing?.paymentTermDays ?: 0,
                assignedAgentId = payload.string("assigned_agent_id") ?: existing?.assignedAgentId,
                isActive = true,
                updatedAtMs = event.occurredAtMs,
            )
        )
        return Outcome.APPLIED
    }

    // --- buyurtmalar ------------------------------------------------------

    private suspend fun applyOrder(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("order_id") ?: return Outcome.CONFLICT
        if (database.orders().byId(id) != null) return Outcome.APPLIED   // takror

        val customerId = payload.string("customer_id") ?: return Outcome.CONFLICT
        // Bog'liq yozuv hali kelmagan bo'lishi mumkin (tartib buzilishi) —
        // yiqilish o'rniga kechiktiramiz.
        if (database.customers().byId(customerId) == null) return Outcome.DEFERRED

        @Suppress("UNCHECKED_CAST")
        val rawLines = payload["lines"] as? List<Map<String, Any?>> ?: return Outcome.CONFLICT
        for (line in rawLines) {
            val productId = line.string("product_id") ?: return Outcome.CONFLICT
            if (database.products().byId(productId) == null) return Outcome.DEFERRED
        }

        val inputs = rawLines.map {
            PricingRules.LineInput(
                it.string("quantity") ?: "0",
                it.long("unit_price") ?: 0,
                it.string("discount_percent") ?: "0",
            )
        }
        val totals = PricingRules.computeOrderTotals(inputs)

        database.orders().upsert(
            OrderEntity(
                id = id,
                number = payload.string("number") ?: id.takeLast(8),
                customerId = customerId,
                warehouseId = payload.string("warehouse_id"),
                agentId = payload.string("agent_id"),
                state = OrderState.DRAFT.name,
                orderedAtMs = payload.long("ordered_at_ms") ?: event.occurredAtMs,
                subtotal = totals.subtotal,
                discountTotal = totals.discountTotal,
                total = totals.total,
                paidTotal = 0,
                currency = payload.string("currency") ?: "UZS",
                note = payload.string("note"),
                updatedAtMs = event.occurredAtMs,
            )
        )
        database.orders().upsertLines(
            rawLines.mapIndexed { index, line ->
                OrderLineEntity(
                    id = line.string("line_id") ?: "$id-$index",
                    orderId = id,
                    productId = line.string("product_id").orEmpty(),
                    quantity = line.string("quantity") ?: "0",
                    unitPrice = line.long("unit_price") ?: 0,
                    discountPercent = line.string("discount_percent") ?: "0",
                    lineTotal = PricingRules.lineTotal(
                        line.string("quantity") ?: "0",
                        line.long("unit_price") ?: 0,
                        line.string("discount_percent") ?: "0",
                    ),
                )
            }
        )
        return Outcome.APPLIED
    }

    private suspend fun applyOrderState(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("order_id") ?: return Outcome.CONFLICT
        val order = database.orders().byId(id) ?: return Outcome.DEFERRED

        val current = OrderState.from(order.state)
        val target = OrderState.from(payload.string("to_state") ?: return Outcome.CONFLICT)
        if (current == target) return Outcome.APPLIED   // takror

        if (!OrderRules.canTransition(current, target)) {
            // Noqonuniy o'tish JIMGINA qabul qilinmaydi: ikki qurilma zid
            // amal qilgan bo'lishi mumkin, odam ko'rishi kerak.
            database.sync().insertConflict(
                ConflictEntity(
                    aggregateType = "Order", aggregateId = id,
                    strategy = "STATE_MACHINE", status = "NEEDS_REVIEW",
                    resolution = "${current.name} -> ${target.name} mumkin emas",
                    localValue = current.name, remoteValue = target.name,
                    detectedAtMs = System.currentTimeMillis(),
                )
            )
            return Outcome.CONFLICT
        }
        database.orders().update(order.copy(state = target.name, updatedAtMs = event.occurredAtMs))
        return Outcome.APPLIED
    }

    // --- ombor ------------------------------------------------------------

    private suspend fun applyMovement(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("movement_id") ?: return Outcome.CONFLICT
        if (database.inventory().movementById(id) != null) return Outcome.APPLIED

        val warehouseId = payload.string("warehouse_id") ?: return Outcome.CONFLICT
        val productId = payload.string("product_id") ?: return Outcome.CONFLICT
        if (database.inventory().warehouseById(warehouseId) == null) return Outcome.DEFERRED
        if (database.products().byId(productId) == null) return Outcome.DEFERRED

        database.inventory().insertMovement(
            MovementEntity(
                id = id,
                warehouseId = warehouseId,
                productId = productId,
                movementType = payload.string("movement_type") ?: return Outcome.CONFLICT,
                quantity = payload.string("quantity") ?: "0",
                unitCost = payload.long("unit_cost") ?: 0,
                referenceType = payload.string("reference_type"),
                referenceId = payload.string("reference_id"),
                occurredAtMs = payload.long("occurred_at_ms") ?: event.occurredAtMs,
                sourceEventId = event.eventId,
                note = payload.string("note"),
            )
        )
        refreshStock(warehouseId, productId)
        return Outcome.APPLIED
    }

    /**
     * Qoldiq keshini harakatlardan QAYTA hisoblaydi.
     *
     * Inkremental qo'shish emas, to'liq qayta hisob: kech kelgan hodisa
     * ham to'g'ri hisobga olinadi. Sekinroq, lekin TO'G'RI.
     */
    private suspend fun refreshStock(warehouseId: String, productId: String) {
        val movements = database.inventory().movementsFor(warehouseId, productId)
            .map { MovementType.from(it.movementType) to it.quantity }
        val stock = StockRules.computeStock(movements)

        database.inventory().upsertStock(
            StockEntity(
                warehouseId = warehouseId,
                productId = productId,
                quantity = stock.onHand.toPlainString(),
                reserved = stock.reserved.toPlainString(),
                updatedAtMs = System.currentTimeMillis(),
            )
        )
    }

    // --- moliya -----------------------------------------------------------

    private suspend fun applyPayment(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("payment_id") ?: return Outcome.CONFLICT
        if (database.payments().byId(id) != null) return Outcome.APPLIED

        val customerId = payload.string("customer_id")
        if (customerId != null && database.customers().byId(customerId) == null) {
            return Outcome.DEFERRED
        }

        database.payments().upsert(
            PaymentEntity(
                id = id,
                number = payload.string("number") ?: id.takeLast(8),
                direction = payload.string("direction") ?: "IN",
                customerId = customerId,
                amount = payload.long("amount") ?: 0,
                currency = payload.string("currency") ?: "UZS",
                method = payload.string("method") ?: "cash",
                occurredAtMs = payload.long("occurred_at_ms") ?: event.occurredAtMs,
                reversesPaymentId = null,
                isReversed = false,
                note = payload.string("note"),
            )
        )
        return Outcome.APPLIED
    }

    private suspend fun applyPaymentReversal(
        event: EventEntity, payload: Map<String, Any?>,
    ): Outcome {
        val id = payload.string("payment_id") ?: return Outcome.CONFLICT
        if (database.payments().byId(id) != null) return Outcome.APPLIED

        val originalId = payload.string("reverses_payment_id") ?: return Outcome.CONFLICT
        val original = database.payments().byId(originalId) ?: return Outcome.DEFERRED

        // To'lov O'CHIRILMAYDI — teskari yozuv qo'shiladi.
        database.payments().upsert(
            PaymentEntity(
                id = id,
                number = payload.string("number") ?: id.takeLast(8),
                direction = if (original.direction == "IN") "OUT" else "IN",
                customerId = original.customerId,
                amount = payload.long("amount") ?: original.amount,
                currency = original.currency,
                method = original.method,
                occurredAtMs = payload.long("occurred_at_ms") ?: event.occurredAtMs,
                reversesPaymentId = originalId,
                isReversed = false,
                note = payload.string("reason"),
            )
        )
        database.payments().update(original.copy(isReversed = true))
        return Outcome.APPLIED
    }

    private suspend fun applyVisit(event: EventEntity, payload: Map<String, Any?>): Outcome {
        val id = payload.string("visit_id") ?: return Outcome.CONFLICT
        val customerId = payload.string("customer_id") ?: return Outcome.CONFLICT
        if (database.customers().byId(customerId) == null) return Outcome.DEFERRED

        database.visits().upsert(
            VisitEntity(
                id = id,
                customerId = customerId,
                agentId = payload.string("agent_id").orEmpty(),
                routeId = payload.string("route_id"),
                startedAtMs = payload.long("started_at_ms"),
                finishedAtMs = payload.long("finished_at_ms"),
                outcome = payload.string("outcome"),
                latitude = payload.string("latitude")?.toDoubleOrNull(),
                longitude = payload.string("longitude")?.toDoubleOrNull(),
                photoPath = payload.string("photo_path"),
                note = payload.string("note"),
            )
        )
        return Outcome.APPLIED
    }

    // --- CBOR yordamchilari ------------------------------------------------

    private fun decode(payload: ByteArray): Map<String, Any?> {
        val root = CborDecoder.decode(payload).first() as CborMap
        return root.toKotlin()
    }

    private fun CborMap.toKotlin(): Map<String, Any?> =
        keys.associate { key ->
            (key as UnicodeString).string to convert(get(key))
        }

    private fun convert(item: Any?): Any? = when (item) {
        null -> null
        is UnicodeString -> item.string
        is CborNumber -> item.value.toLong()
        is ByteString -> item.bytes
        is CborMap -> item.toKotlin()
        is co.nstant.`in`.cbor.model.Array -> item.dataItems.map { convert(it) }
        else -> item.toString()
    }

    private fun Map<String, Any?>.string(key: String): String? = this[key] as? String

    private fun Map<String, Any?>.long(key: String): Long? = when (val value = this[key]) {
        is Long -> value
        is Int -> value.toLong()
        is String -> value.toLongOrNull()
        else -> null
    }

    companion object {
        const val MAX_ATTEMPTS = 12
    }
}
