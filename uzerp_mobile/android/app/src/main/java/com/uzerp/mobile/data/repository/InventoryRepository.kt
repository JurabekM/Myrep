package com.uzerp.mobile.data.repository

import androidx.room.withTransaction
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.InsufficientStockException
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.AppDatabase
import com.uzerp.mobile.data.local.dao.InventoryCountDao
import com.uzerp.mobile.data.local.dao.InventoryCountItemWithProduct
import com.uzerp.mobile.data.local.dao.InventoryCountWithWarehouse
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.dao.SequenceDao
import com.uzerp.mobile.data.local.dao.StockDao
import com.uzerp.mobile.data.local.dao.StockMoveDao
import com.uzerp.mobile.data.local.dao.WarehouseDao
import com.uzerp.mobile.data.local.entity.InventoryCountEntity
import com.uzerp.mobile.data.local.entity.InventoryCountItemEntity
import com.uzerp.mobile.data.local.entity.StockEntity
import com.uzerp.mobile.data.local.entity.StockMoveEntity
import com.uzerp.mobile.data.local.entity.WarehouseEntity
import java.math.BigDecimal
import java.time.Year
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.first

/** Bitta qoldiq qatori — mahsulot ma'lumotlari bilan (ekran uchun). */
data class StockOverviewRow(
    val productId: Long,
    val sku: String?,
    val name: String,
    val unit: String,
    val quantity: BigDecimal,
    val costPrice: BigDecimal,
    val minStock: BigDecimal,
) {
    val stockValue: BigDecimal get() = d(quantity.multiply(costPrice))
    val isLow: Boolean get() = minStock > BigDecimal.ZERO && quantity <= minStock
}

/**
 * Ombor servisi — Python `InventoryService` bilan bir xil qoidalar:
 * kirim/chiqim/transfer/tuzatish, har biri `stock_moves` jurnaliga yoziladi,
 * inventarizatsiya (sanoq -> farq -> avto-tuzatish).
 */
@Singleton
class InventoryRepository @Inject constructor(
    private val db: AppDatabase,
    private val stockDao: StockDao,
    private val stockMoveDao: StockMoveDao,
    private val warehouseDao: WarehouseDao,
    private val productDao: ProductDao,
    private val sequenceDao: SequenceDao,
    private val inventoryCountDao: InventoryCountDao,
) {
    /** Manfiy qoldiqqa ruxsat berilmaydi (Python `allow_negative_stock` bilan bir xil). */
    private val allowNegativeStock = false
    suspend fun warehouses(): List<WarehouseEntity> = warehouseDao.observeAll().first()

    suspend fun defaultWarehouseId(): Long =
        warehouseDao.defaultWarehouseId() ?: throw NotFoundException("Hech qanday ombor topilmadi.")

    suspend fun createWarehouse(name: String, address: String = ""): Long {
        if (name.isBlank()) throw ValidationException("Ombor nomi bo'sh bo'lishi mumkin emas.")
        return warehouseDao.insert(WarehouseEntity(name = name.trim(), address = address))
    }

    suspend fun stockLevel(productId: Long, warehouseId: Long): BigDecimal =
        stockDao.levelForWarehouse(productId, warehouseId)

    suspend fun totalStock(productId: Long): BigDecimal = stockDao.totalForProduct(productId)

    suspend fun stockOverview(
        page: Int = 1,
        search: String? = null,
        warehouseId: Long? = null,
    ): PageResult<StockOverviewRow> {
        // Mobil qurilmada ombor kichik (odatda yuzlab pozitsiya) — barcha
        // faol mahsulotlar xotirada filtrlanadi (server-side SQL join o'rniga
        // Kotlin darajasida, kodni soddalashtiradi va yetarlicha tez ishlaydi).
        val term = search?.trim()?.lowercase()?.ifBlank { null }
        val allProducts = productDao.search(null, null, 10_000, 0)
        val rows = allProducts
            .filter { p ->
                term == null || p.name.lowercase().contains(term) ||
                    (p.sku?.lowercase()?.contains(term) == true) ||
                    p.barcode.lowercase().contains(term)
            }
            .map { p ->
                val qty = if (warehouseId != null) {
                    stockDao.levelForWarehouse(p.id, warehouseId)
                } else {
                    stockDao.totalForProduct(p.id)
                }
                StockOverviewRow(p.id, p.sku, p.name, p.unit, qty, p.costPrice, p.minStock)
            }
        val offset = (page - 1) * PAGE_SIZE
        val pageItems = rows.drop(offset).take(PAGE_SIZE)
        return PageResult(pageItems, page, PAGE_SIZE, rows.size)
    }

    suspend fun stockValue(): BigDecimal {
        val warehouses = warehouses()
        var total = BigDecimal.ZERO
        for (w in warehouses) {
            for (s in stockDao.byWarehouse(w.id)) {
                val product = productDao.getById(s.productId) ?: continue
                total = d(total.add(s.quantity.multiply(product.costPrice)))
            }
        }
        return total
    }

    suspend fun lowStock(limit: Int = 100): List<StockOverviewRow> =
        stockOverview(page = 1, search = null).items.filter { it.isLow }.take(limit)

    // ------------------------------------------------------------------ //
    //  Harakatlar
    // ------------------------------------------------------------------ //

    suspend fun moveIn(
        productId: Long,
        warehouseId: Long,
        quantity: BigDecimal,
        unitCost: BigDecimal = BigDecimal.ZERO,
        refType: String = "",
        refId: Long? = null,
        note: String = "",
        userId: Long? = null,
    ) {
        val qty = positiveQty(quantity)
        db.withTransaction {
            changeStock(productId, warehouseId, qty)
            recordMove("in", productId, null, warehouseId, qty, d(unitCost), refType, refId, note, userId)
        }
    }

    suspend fun moveOut(
        productId: Long,
        warehouseId: Long,
        quantity: BigDecimal,
        refType: String = "",
        refId: Long? = null,
        note: String = "",
        userId: Long? = null,
    ) {
        val qty = positiveQty(quantity)
        db.withTransaction {
            ensureAvailable(productId, warehouseId, qty)
            changeStock(productId, warehouseId, qty.negate())
            recordMove("out", productId, warehouseId, null, qty, BigDecimal.ZERO, refType, refId, note, userId)
        }
    }

    suspend fun transfer(
        productId: Long,
        warehouseFrom: Long,
        warehouseTo: Long,
        quantity: BigDecimal,
        note: String = "",
        userId: Long? = null,
    ) {
        if (warehouseFrom == warehouseTo) {
            throw ValidationException("Bir xil ombor orasida ko'chirish mumkin emas.")
        }
        val qty = positiveQty(quantity)
        db.withTransaction {
            ensureAvailable(productId, warehouseFrom, qty)
            changeStock(productId, warehouseFrom, qty.negate())
            changeStock(productId, warehouseTo, qty)
            recordMove("transfer", productId, warehouseFrom, warehouseTo, qty, BigDecimal.ZERO, "transfer", null, note, userId)
        }
    }

    suspend fun adjust(productId: Long, warehouseId: Long, newQuantity: BigDecimal, note: String = "", userId: Long? = null): BigDecimal {
        val target = d(newQuantity)
        if (target < BigDecimal.ZERO) throw ValidationException("Qoldiq manfiy bo'lishi mumkin emas.")
        var diff = BigDecimal.ZERO
        db.withTransaction {
            val current = stockLevel(productId, warehouseId)
            diff = d(target.subtract(current))
            if (diff.signum() != 0) {
                changeStock(productId, warehouseId, diff)
                recordMove(
                    "adjust", productId,
                    if (diff.signum() < 0) warehouseId else null,
                    if (diff.signum() > 0) warehouseId else null,
                    diff.abs(), BigDecimal.ZERO, "adjust", null, note, userId,
                )
            }
        }
        return diff
    }

    suspend fun movesHistory(productId: Long? = null, limit: Int = 50): List<StockMoveEntity> =
        stockMoveDao.recent(productId, limit, 0)

    // ------------------------------------------------------------------ //
    //  Inventarizatsiya
    // ------------------------------------------------------------------ //

    suspend fun startCount(warehouseId: Long, userId: Long?): Long {
        var countId = 0L
        db.withTransaction {
            val number = "CNT-${Year.now().value}-%06d".format(sequenceDao.next("CNT", Year.now().value))
            countId = inventoryCountDao.insert(
                InventoryCountEntity(
                    number = number,
                    warehouseId = warehouseId,
                    status = "draft",
                    userId = userId,
                    createdAt = DateUtils.nowStr(),
                ),
            )
            for (stock in stockDao.byWarehouse(warehouseId)) {
                if (stock.quantity.signum() == 0) continue
                inventoryCountDao.insertItem(
                    InventoryCountItemEntity(
                        countId = countId,
                        productId = stock.productId,
                        expectedQty = stock.quantity,
                        actualQty = stock.quantity,
                        difference = BigDecimal.ZERO,
                    ),
                )
            }
        }
        return countId
    }

    suspend fun setCountItem(countId: Long, productId: Long, actualQty: BigDecimal) {
        val actual = d(actualQty)
        if (actual < BigDecimal.ZERO) throw ValidationException("Haqiqiy qoldiq manfiy bo'lishi mumkin emas.")
        val existing = inventoryCountDao.getItem(countId, productId)
        if (existing != null) {
            inventoryCountDao.updateItem(
                existing.copy(actualQty = actual, difference = d(actual.subtract(existing.expectedQty))),
            )
        } else {
            inventoryCountDao.insertItem(
                InventoryCountItemEntity(countId = countId, productId = productId, actualQty = actual, difference = actual),
            )
        }
    }

    suspend fun completeCount(countId: Long, userId: Long?): Int {
        val count = inventoryCountDao.getById(countId) ?: throw NotFoundException("Inventarizatsiya topilmadi.")
        if (count.status != "draft") throw ValidationException("Inventarizatsiya allaqachon yakunlangan.")
        val items = inventoryCountDao.itemsForCount(countId)
        var adjusted = 0
        for (item in items) {
            if (item.difference.signum() != 0) {
                adjust(item.productId, count.warehouseId, item.actualQty, "Inventarizatsiya ${count.number}", userId)
                adjusted++
            }
        }
        inventoryCountDao.complete(countId, DateUtils.nowStr())
        return adjusted
    }

    suspend fun countDetails(countId: Long): Pair<InventoryCountEntity, List<InventoryCountItemWithProduct>> {
        val count = inventoryCountDao.getById(countId) ?: throw NotFoundException("Inventarizatsiya topilmadi.")
        return count to inventoryCountDao.itemsForCount(countId)
    }

    suspend fun listCounts(page: Int = 1): PageResult<InventoryCountWithWarehouse> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(inventoryCountDao.page(PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    // ------------------------------------------------------------------ //
    //  Ichki yordamchilar
    // ------------------------------------------------------------------ //

    private fun positiveQty(quantity: BigDecimal): BigDecimal {
        val qty = d(quantity)
        if (qty <= BigDecimal.ZERO) throw ValidationException("Miqdor musbat bo'lishi kerak.")
        return qty
    }

    private suspend fun ensureAvailable(productId: Long, warehouseId: Long, qty: BigDecimal) {
        if (allowNegativeStock) return
        val current = stockLevel(productId, warehouseId)
        if (current < qty) {
            val product = productDao.getById(productId)
            throw InsufficientStockException(
                "Omborda yetarli emas: ${product?.name ?: "#$productId"} — qoldiq $current, kerak $qty.",
            )
        }
    }

    private suspend fun changeStock(productId: Long, warehouseId: Long, delta: BigDecimal) {
        val existing = stockDao.get(productId, warehouseId)
        val newQty = d((existing?.quantity ?: BigDecimal.ZERO).add(delta))
        stockDao.upsert(StockEntity(id = existing?.id ?: 0, productId = productId, warehouseId = warehouseId, quantity = newQty))
    }

    private suspend fun recordMove(
        moveType: String,
        productId: Long,
        warehouseFrom: Long?,
        warehouseTo: Long?,
        qty: BigDecimal,
        unitCost: BigDecimal,
        refType: String,
        refId: Long?,
        note: String,
        userId: Long?,
    ) {
        stockMoveDao.insert(
            StockMoveEntity(
                moveType = moveType,
                productId = productId,
                warehouseFrom = warehouseFrom,
                warehouseTo = warehouseTo,
                quantity = qty,
                unitCost = unitCost,
                refType = refType,
                refId = refId,
                note = note,
                userId = userId,
                createdAt = DateUtils.nowStr(),
            ),
        )
    }
}
