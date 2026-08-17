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
import com.uzerp.mobile.data.local.dao.CustomerDao
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.dao.SalesDocDao
import com.uzerp.mobile.data.local.dao.SalesDocWithCustomer
import com.uzerp.mobile.data.local.dao.SalesItemDao
import com.uzerp.mobile.data.local.dao.SalesItemWithProduct
import com.uzerp.mobile.data.local.dao.SequenceDao
import com.uzerp.mobile.data.local.entity.SalesDocEntity
import com.uzerp.mobile.data.local.entity.SalesItemEntity
import java.math.BigDecimal
import java.time.Year
import javax.inject.Inject
import javax.inject.Singleton

val VALID_DOC_TYPES = setOf("quotation", "order", "invoice", "pos", "return")
private val PREFIX = mapOf(
    "quotation" to "QUO", "order" to "ORD", "invoice" to "INV", "pos" to "POS", "return" to "RET",
)
private val STOCK_TYPES = setOf("invoice", "pos")
private val CONVERT_FLOW = mapOf("quotation" to "order", "order" to "invoice")

data class SaleItemInput(
    val productId: Long,
    val quantity: BigDecimal,
    val price: BigDecimal? = null,
    val discount: BigDecimal? = null,
)

data class SalesDocDetail(val doc: SalesDocEntity, val items: List<SalesItemWithProduct>)

/**
 * Savdo hujjatlari servisi — Python `SalesService` bilan bir xil biznes
 * qoidalar: 5 hujjat turi, mijoz chegirmasi avto-qo'llanadi, QQS narx
 * ichidan ajratiladi, konvertatsiya zanjiri, qaytarish limiti nazorati.
 */
@Singleton
class SalesRepository @Inject constructor(
    private val db: AppDatabase,
    private val salesDocDao: SalesDocDao,
    private val salesItemDao: SalesItemDao,
    private val productDao: ProductDao,
    private val customerDao: CustomerDao,
    private val sequenceDao: SequenceDao,
    private val inventoryRepository: InventoryRepository,
    private val eventBus: AppEventBus,
) {
    suspend fun createDoc(
        docType: String,
        customerId: Long?,
        warehouseId: Long?,
        items: List<SaleItemInput>,
        userId: Long?,
        note: String = "",
        discount: BigDecimal = BigDecimal.ZERO,
        docDate: String? = null,
        parentId: Long? = null,
    ): Long {
        if (docType !in VALID_DOC_TYPES) throw ValidationException("Noma'lum hujjat turi: $docType")
        val customer = customerId?.let { customerDao.getById(it) }
        val lines = buildLines(items, customer?.discountPercent ?: BigDecimal.ZERO)
        val totals = computeTotals(lines, d(discount))

        var effectiveWarehouse = warehouseId
        if (docType in STOCK_TYPES && effectiveWarehouse == null) {
            effectiveWarehouse = inventoryRepository.defaultWarehouseId()
        }

        var docId = 0L
        db.withTransaction {
            val year = Year.now().value
            val number = "${PREFIX.getValue(docType)}-$year-%06d".format(sequenceDao.next(PREFIX.getValue(docType), year))
            val now = DateUtils.nowStr()
            docId = salesDocDao.insert(
                SalesDocEntity(
                    docType = docType, number = number, customerId = customerId, warehouseId = effectiveWarehouse,
                    status = "draft", subtotal = totals.subtotal, discount = totals.discount,
                    vatAmount = totals.vatAmount, total = totals.total, paidAmount = BigDecimal.ZERO,
                    note = note, userId = userId, parentId = parentId, docDate = docDate ?: DateUtils.todayStr(),
                    createdAt = now, updatedAt = now,
                ),
            )
            for (line in lines) {
                salesItemDao.insert(
                    SalesItemEntity(
                        docId = docId, productId = line.productId, quantity = line.quantity, price = line.price,
                        discount = line.discount, vatRate = line.vatRate, vatAmount = line.vatAmount, total = line.total,
                    ),
                )
            }
        }
        return docId
    }

    suspend fun getDoc(docId: Long): SalesDocDetail {
        val doc = salesDocDao.getById(docId) ?: throw NotFoundException("Hujjat topilmadi (id=$docId).")
        return SalesDocDetail(doc, salesDocDao.itemsForDoc(docId))
    }

    suspend fun list(
        page: Int = 1,
        docType: String? = null,
        status: String? = null,
        search: String? = null,
    ): PageResult<SalesDocWithCustomer> {
        val offset = (page - 1) * PAGE_SIZE
        val items = salesDocDao.search(docType, status, search?.trim()?.ifBlank { null }, PAGE_SIZE, offset)
        return PageResult(items, page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun confirm(docId: Long, userId: Long?) {
        val detail = getDoc(docId)
        val doc = detail.doc
        if (doc.status != "draft") throw StateException("Faqat qoralama hujjatni tasdiqlash mumkin.")
        val requiresStock = doc.docType in STOCK_TYPES || doc.docType == "return"
        val warehouseId = doc.warehouseId
        if (requiresStock && warehouseId == null) throw ValidationException("Hujjatda ombor ko'rsatilmagan.")

        db.withTransaction {
            if (warehouseId != null) {
                when {
                    doc.docType in STOCK_TYPES -> for (item in detail.items) {
                        inventoryRepository.moveOut(item.productId, warehouseId, item.quantity, doc.docType, docId, doc.number, userId)
                    }
                    doc.docType == "return" -> for (item in detail.items) {
                        inventoryRepository.moveIn(item.productId, warehouseId, item.quantity, item.price, "return", docId, doc.number, userId)
                    }
                }
            }
            salesDocDao.update(doc.copy(status = "confirmed", updatedAt = DateUtils.nowStr()))
        }
        eventBus.emit(AppEvent.SaleConfirmed(docId, doc.docType, userId))
    }

    suspend fun cancel(docId: Long, userId: Long?) {
        val detail = getDoc(docId)
        val doc = detail.doc
        if (doc.status == "cancelled") throw StateException("Hujjat allaqachon bekor qilingan.")
        if (doc.paidAmount.signum() > 0) {
            throw StateException("To'lov qilingan hujjatni bekor qilib bo'lmaydi — qaytarish rasmiylashtiring.")
        }
        val warehouseId = doc.warehouseId
        val stockMoved = doc.status in setOf("confirmed", "partial", "paid") &&
            (doc.docType in STOCK_TYPES || doc.docType == "return") && warehouseId != null

        db.withTransaction {
            if (stockMoved && warehouseId != null) {
                for (item in detail.items) {
                    if (doc.docType == "return") {
                        inventoryRepository.moveOut(item.productId, warehouseId, item.quantity, "return_cancel", docId, doc.number, userId)
                    } else {
                        inventoryRepository.moveIn(item.productId, warehouseId, item.quantity, BigDecimal.ZERO, "sale_cancel", docId, doc.number, userId)
                    }
                }
            }
            salesDocDao.update(doc.copy(status = "cancelled", updatedAt = DateUtils.nowStr()))
        }
    }

    suspend fun convert(docId: Long, userId: Long?): Long {
        val detail = getDoc(docId)
        val doc = detail.doc
        val target = CONVERT_FLOW[doc.docType] ?: throw StateException("${doc.docType} hujjatini konvertatsiya qilib bo'lmaydi.")
        if (doc.status == "cancelled") throw StateException("Bekor qilingan hujjatni konvertatsiya qilib bo'lmaydi.")

        val newItems = detail.items.map { SaleItemInput(it.productId, it.quantity, it.price, it.discount) }
        return createDoc(
            target, doc.customerId, doc.warehouseId, newItems, userId,
            note = "${doc.number} asosida", discount = doc.discount, parentId = docId,
        )
    }

    suspend fun createReturn(parentId: Long, items: List<SaleItemInput>, userId: Long?, note: String = ""): Long {
        val parentDetail = getDoc(parentId)
        val parent = parentDetail.doc
        if (parent.docType !in STOCK_TYPES) throw StateException("Faqat hisob-faktura yoki POS savdodan qaytarish mumkin.")
        if (parent.status !in setOf("confirmed", "partial", "paid")) {
            throw StateException("Faqat tasdiqlangan hujjatdan qaytarish mumkin.")
        }

        val soldQty = parentDetail.items.associate { it.productId to it.quantity }
        val prices = parentDetail.items.associate { it.productId to it.price }
        val returnItems = mutableListOf<SaleItemInput>()
        for (raw in items) {
            val sold = soldQty[raw.productId] ?: throw ValidationException("Mahsulot #${raw.productId} bu hujjatda sotilmagan.")
            if (raw.quantity <= BigDecimal.ZERO) throw ValidationException("Qaytarish miqdori musbat bo'lishi kerak.")
            val alreadyReturned = salesDocDao.returnedQuantity(parentId, raw.productId)
            if (raw.quantity > d(sold.subtract(alreadyReturned))) {
                throw ValidationException("Mahsulot #${raw.productId}: qaytarish miqdori sotilganidan oshib ketdi.")
            }
            returnItems.add(SaleItemInput(raw.productId, raw.quantity, prices[raw.productId]))
        }

        val returnId = createDoc(
            "return", parent.customerId, parent.warehouseId, returnItems, userId,
            note = note.ifBlank { "${parent.number} bo'yicha qaytarish" }, parentId = parentId,
        )
        confirm(returnId, userId)
        return returnId
    }

    suspend fun registerPayment(docId: Long, amount: BigDecimal, userId: Long?) {
        val detail = getDoc(docId)
        val doc = detail.doc
        if (doc.docType !in setOf("invoice", "pos", "order")) throw StateException("Bu turdagi hujjatga to'lov qabul qilinmaydi.")
        if (doc.status !in setOf("confirmed", "partial")) throw StateException("Faqat tasdiqlangan hujjatga to'lov qabul qilinadi.")
        val pay = d(amount)
        if (pay <= BigDecimal.ZERO) throw ValidationException("To'lov summasi musbat bo'lishi kerak.")
        val remaining = d(doc.total.subtract(doc.paidAmount))
        if (pay > remaining) throw ValidationException("To'lov qoldiqdan oshib ketdi (qoldiq: $remaining).")
        val newPaid = d(doc.paidAmount.add(pay))
        val status = if (newPaid >= doc.total) "paid" else "partial"
        salesDocDao.update(doc.copy(paidAmount = newPaid, status = status, updatedAt = DateUtils.nowStr()))
    }

    /** POS savdo: yaratish + tasdiqlash — to'lov chaqiruvchi tomonidan (PaymentRepository) amalga oshiriladi. */
    suspend fun posSale(
        items: List<SaleItemInput>,
        userId: Long?,
        customerId: Long? = null,
        warehouseId: Long? = null,
    ): Long {
        val docId = createDoc("pos", customerId, warehouseId, items, userId)
        confirm(docId, userId)
        return docId
    }

    // ------------------------------------------------------------------ //
    //  Ichki hisob-kitob
    // ------------------------------------------------------------------ //

    private data class Line(
        val productId: Long, val quantity: BigDecimal, val price: BigDecimal,
        val discount: BigDecimal, val vatRate: BigDecimal, val vatAmount: BigDecimal, val total: BigDecimal,
    )

    private data class Totals(val subtotal: BigDecimal, val discount: BigDecimal, val vatAmount: BigDecimal, val total: BigDecimal)

    private suspend fun buildLines(items: List<SaleItemInput>, customerDiscountPercent: BigDecimal): List<Line> {
        if (items.isEmpty()) throw ValidationException("Hujjatda kamida bitta pozitsiya bo'lishi kerak.")
        return items.map { raw ->
            val product = productDao.getById(raw.productId) ?: throw NotFoundException("Mahsulot topilmadi (id=${raw.productId}).")
            val qty = d(raw.quantity)
            if (qty <= BigDecimal.ZERO) throw ValidationException("${product.name}: miqdor musbat bo'lsin.")
            val price = d(raw.price ?: product.salePrice)
            if (price < BigDecimal.ZERO) throw ValidationException("${product.name}: narx manfiy bo'lmasin.")

            val gross = d(qty.multiply(price))
            var lineDiscount = d(raw.discount ?: BigDecimal.ZERO)
            if (lineDiscount.signum() == 0 && customerDiscountPercent.signum() > 0) {
                lineDiscount = d(gross.multiply(customerDiscountPercent).divide(BigDecimal(100)))
            }
            if (lineDiscount < BigDecimal.ZERO || lineDiscount > gross) {
                throw ValidationException("${product.name}: chegirma 0 dan $gross gacha bo'lsin.")
            }

            val total = d(gross.subtract(lineDiscount))
            val vatRate = d(product.vatRate)
            val vatAmount = if (vatRate.signum() > 0) extractVat(total, vatRate) else BigDecimal.ZERO
            Line(product.id, qty, price, lineDiscount, vatRate, vatAmount, total)
        }
    }

    private fun computeTotals(lines: List<Line>, docDiscount: BigDecimal): Totals {
        val subtotal = d(lines.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.total) })
        val vatSum = d(lines.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.vatAmount) })
        if (docDiscount < BigDecimal.ZERO || docDiscount > subtotal) {
            throw ValidationException("Hujjat chegirmasi 0 dan $subtotal gacha bo'lishi kerak.")
        }
        val total = d(subtotal.subtract(docDiscount))
        val vatAmount = if (subtotal.signum() > 0) d(vatSum.multiply(total).divide(subtotal, 10, java.math.RoundingMode.HALF_UP)) else BigDecimal.ZERO
        return Totals(subtotal, docDiscount, vatAmount, total)
    }
}
