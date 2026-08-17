package com.uzerp.mobile.data.repository

import androidx.room.withTransaction
import com.uzerp.mobile.core.AppEvent
import com.uzerp.mobile.core.AppEventBus
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.StateException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.core.extractVat
import com.uzerp.mobile.data.local.AppDatabase
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.dao.PurchaseDao
import com.uzerp.mobile.data.local.dao.PurchaseItemDao
import com.uzerp.mobile.data.local.dao.PurchaseItemWithProduct
import com.uzerp.mobile.data.local.dao.PurchaseWithSupplier
import com.uzerp.mobile.data.local.dao.SequenceDao
import com.uzerp.mobile.data.local.entity.PurchaseEntity
import com.uzerp.mobile.data.local.entity.PurchaseItemEntity
import java.math.BigDecimal
import java.time.Year
import javax.inject.Inject
import javax.inject.Singleton

data class PurchaseItemInput(val productId: Long, val quantity: BigDecimal, val price: BigDecimal)
data class PurchaseDetail(val purchase: PurchaseEntity, val items: List<PurchaseItemWithProduct>)

/**
 * Xarid servisi — Python `PurchaseService` bilan bir xil: draft -> received
 * (ombor kirimi + o'rtacha tannarx yangilanadi), bekor qilishda teskari kirim.
 */
@Singleton
class PurchaseRepository @Inject constructor(
    private val db: AppDatabase,
    private val purchaseDao: PurchaseDao,
    private val purchaseItemDao: PurchaseItemDao,
    private val productDao: ProductDao,
    private val sequenceDao: SequenceDao,
    private val inventoryRepository: InventoryRepository,
    private val eventBus: AppEventBus,
) {
    suspend fun create(
        supplierId: Long?,
        warehouseId: Long,
        items: List<PurchaseItemInput>,
        userId: Long?,
        note: String = "",
        docDate: String? = null,
    ): Long {
        if (items.isEmpty()) throw ValidationException("Xaridda kamida bitta pozitsiya bo'lishi kerak.")
        val lines = items.map { raw ->
            val product = productDao.getById(raw.productId) ?: throw NotFoundException("Mahsulot topilmadi (id=${raw.productId}).")
            val qty = d(raw.quantity)
            if (qty <= BigDecimal.ZERO) throw ValidationException("${product.name}: miqdor musbat bo'lsin.")
            val price = d(raw.price)
            if (price < BigDecimal.ZERO) throw ValidationException("${product.name}: narx manfiy bo'lmasin.")
            val vatRate = d(product.vatRate)
            val total = d(qty.multiply(price))
            val vatAmount = if (vatRate.signum() > 0) extractVat(total, vatRate) else BigDecimal.ZERO
            Pair(raw, PurchaseItemEntity(purchaseId = 0, productId = product.id, quantity = qty, price = price, vatRate = vatRate, vatAmount = vatAmount, total = total))
        }
        val subtotal = d(lines.fold(BigDecimal.ZERO) { acc, (_, l) -> acc.add(l.total) })
        val vatTotal = d(lines.fold(BigDecimal.ZERO) { acc, (_, l) -> acc.add(l.vatAmount) })

        var purchaseId = 0L
        db.withTransaction {
            val year = Year.now().value
            val number = "PUR-$year-%06d".format(sequenceDao.next("PUR", year))
            val now = DateUtils.nowStr()
            purchaseId = purchaseDao.insert(
                PurchaseEntity(
                    number = number, supplierId = supplierId, warehouseId = warehouseId, status = "draft",
                    subtotal = subtotal, vatAmount = vatTotal, total = subtotal, paidAmount = BigDecimal.ZERO,
                    note = note, userId = userId, docDate = docDate ?: DateUtils.todayStr(), createdAt = now, updatedAt = now,
                ),
            )
            for ((_, line) in lines) purchaseItemDao.insert(line.copy(purchaseId = purchaseId))
        }
        return purchaseId
    }

    suspend fun get(purchaseId: Long): PurchaseDetail {
        val purchase = purchaseDao.getById(purchaseId) ?: throw NotFoundException("Xarid topilmadi (id=$purchaseId).")
        return PurchaseDetail(purchase, purchaseItemDao.itemsForPurchase(purchaseId))
    }

    suspend fun list(page: Int = 1, status: String? = null): PageResult<PurchaseWithSupplier> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(purchaseDao.search(status, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun receive(purchaseId: Long, userId: Long?) {
        val detail = get(purchaseId)
        val purchase = detail.purchase
        if (purchase.status != "draft") throw StateException("Faqat qoralama xaridni qabul qilish mumkin.")
        val warehouseId = purchase.warehouseId ?: throw ValidationException("Xaridda ombor ko'rsatilmagan.")

        db.withTransaction {
            for (item in detail.items) {
                updateAverageCost(item.productId, item.quantity, item.price)
                inventoryRepository.moveIn(item.productId, warehouseId, item.quantity, item.price, "purchase", purchaseId, purchase.number, userId)
            }
            purchaseDao.update(purchase.copy(status = "received", updatedAt = DateUtils.nowStr()))
        }
        eventBus.emit(AppEvent.PurchaseReceived(purchaseId, userId))
    }

    suspend fun cancel(purchaseId: Long, userId: Long?) {
        val detail = get(purchaseId)
        val purchase = detail.purchase
        if (purchase.status == "cancelled") throw StateException("Xarid allaqachon bekor qilingan.")
        if (purchase.paidAmount.signum() > 0) throw StateException("To'lov qilingan xaridni bekor qilib bo'lmaydi.")
        val warehouseId = purchase.warehouseId

        db.withTransaction {
            if (purchase.status == "received" && warehouseId != null) {
                for (item in detail.items) {
                    inventoryRepository.moveOut(item.productId, warehouseId, item.quantity, "purchase_cancel", purchaseId, purchase.number, userId)
                }
            }
            purchaseDao.update(purchase.copy(status = "cancelled", updatedAt = DateUtils.nowStr()))
        }
    }

    suspend fun registerPayment(purchaseId: Long, amount: BigDecimal, userId: Long?) {
        val detail = get(purchaseId)
        val purchase = detail.purchase
        if (purchase.status !in setOf("received", "partial")) throw StateException("Faqat qabul qilingan xaridga to'lov qilish mumkin.")
        val pay = d(amount)
        if (pay <= BigDecimal.ZERO) throw ValidationException("To'lov summasi musbat bo'lishi kerak.")
        val remaining = d(purchase.total.subtract(purchase.paidAmount))
        if (pay > remaining) throw ValidationException("To'lov qoldiq qarzdan oshib ketdi (qoldiq: $remaining).")
        val newPaid = d(purchase.paidAmount.add(pay))
        val status = if (newPaid >= purchase.total) "paid" else "partial"
        purchaseDao.update(purchase.copy(paidAmount = newPaid, status = status, updatedAt = DateUtils.nowStr()))
    }

    /** O'rtacha tannarx: `(eski_qoldiq*eski_narx + kirim*kirim_narx) / (eski_qoldiq+kirim)`. */
    private suspend fun updateAverageCost(productId: Long, incomingQty: BigDecimal, incomingPrice: BigDecimal) {
        val product = productDao.getById(productId) ?: return
        val oldQty = inventoryRepository.totalStock(productId)
        val oldCost = d(product.costPrice)
        val denominator = oldQty.add(incomingQty)
        val newCost = if (denominator.signum() <= 0) {
            incomingPrice
        } else {
            d(oldQty.multiply(oldCost).add(incomingQty.multiply(incomingPrice)).divide(denominator, 10, java.math.RoundingMode.HALF_UP))
        }
        if (newCost != oldCost) productDao.setCostPrice(productId, newCost)
    }
}
