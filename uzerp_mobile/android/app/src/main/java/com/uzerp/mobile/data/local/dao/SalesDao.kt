package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import com.uzerp.mobile.data.local.entity.PurchaseEntity
import com.uzerp.mobile.data.local.entity.PurchaseItemEntity
import com.uzerp.mobile.data.local.entity.SalesDocEntity
import com.uzerp.mobile.data.local.entity.SalesItemEntity
import kotlinx.coroutines.flow.Flow

/** Savdo hujjati + mahsulot nomi bilan birlashtirilgan qator (ro'yxatlar uchun). */
data class SalesDocWithCustomer(
    val id: Long,
    val docType: String,
    val number: String,
    val customerId: Long?,
    val customerName: String?,
    val status: String,
    val total: java.math.BigDecimal,
    val paidAmount: java.math.BigDecimal,
    val docDate: String,
)

data class SalesItemWithProduct(
    val id: Long,
    val productId: Long,
    val productName: String,
    val unit: String,
    val quantity: java.math.BigDecimal,
    val price: java.math.BigDecimal,
    val discount: java.math.BigDecimal,
    val vatAmount: java.math.BigDecimal,
    val total: java.math.BigDecimal,
)

@Dao
interface SalesDocDao {
    @Insert
    suspend fun insert(doc: SalesDocEntity): Long

    @Update
    suspend fun update(doc: SalesDocEntity)

    @Query("SELECT * FROM sales_docs WHERE id = :id")
    suspend fun getById(id: Long): SalesDocEntity?

    @Query(
        "SELECT d.id, d.docType, d.number, d.customerId, c.name AS customerName, " +
            "d.status, d.total, d.paidAmount, d.docDate FROM sales_docs d " +
            "LEFT JOIN customers c ON c.id = d.customerId " +
            "WHERE (:docType IS NULL OR d.docType = :docType) " +
            "AND (:status IS NULL OR d.status = :status) " +
            "AND (:search IS NULL OR d.number LIKE '%' || :search || '%') " +
            "ORDER BY d.id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(
        docType: String?,
        status: String?,
        search: String?,
        limit: Int,
        offset: Int,
    ): List<SalesDocWithCustomer>

    @Query(
        "SELECT d.id, d.docType, d.number, d.customerId, c.name AS customerName, " +
            "d.status, d.total, d.paidAmount, d.docDate FROM sales_docs d " +
            "LEFT JOIN customers c ON c.id = d.customerId " +
            "WHERE d.status <> 'cancelled' ORDER BY d.id DESC LIMIT :limit",
    )
    fun observeRecent(limit: Int): Flow<List<SalesDocWithCustomer>>

    @Query(
        "SELECT i.id, i.productId, p.name AS productName, p.unit, i.quantity, " +
            "i.price, i.discount, i.vatAmount, i.total FROM sales_items i " +
            "JOIN products p ON p.id = i.productId WHERE i.docId = :docId ORDER BY i.id",
    )
    suspend fun itemsForDoc(docId: Long): List<SalesItemWithProduct>

    // SUM() natijalari CAST(... AS TEXT) bilan o'raladi — Android CursorWindow
    // REAL->String da %g (6 xonali) ishlatib katta summalarda aniqlikni
    // yo'qotadi; SQLite ning o'z cast'i 15 xonali aniq matn beradi.
    @Query(
        "SELECT CAST(SUM(CASE WHEN d.docType = 'return' THEN -d.total ELSE d.total END) AS TEXT) " +
            "FROM sales_docs d WHERE d.docType IN ('invoice','pos','return') " +
            "AND d.status IN ('confirmed','partial','paid') " +
            "AND d.docDate >= :dateFrom AND d.docDate <= :dateTo",
    )
    suspend fun netSales(dateFrom: String, dateTo: String): java.math.BigDecimal?

    /** QQS hisoboti uchun: chiqim QQS (qaytarish manfiy hisoblanadi). */
    @Query(
        "SELECT CAST(COALESCE(SUM(CASE WHEN docType = 'return' THEN -vatAmount ELSE vatAmount END), 0) AS TEXT) " +
            "FROM sales_docs WHERE docType IN ('invoice', 'pos', 'return') " +
            "AND status IN ('confirmed', 'partial', 'paid') " +
            "AND docDate >= :dateFrom AND docDate <= :dateTo",
    )
    suspend fun outputVat(dateFrom: String, dateTo: String): java.math.BigDecimal

    @Query(
        "SELECT i.productId FROM sales_docs d JOIN sales_items i ON i.docId = d.id " +
            "WHERE d.parentId = :parentId AND d.docType = 'return' " +
            "AND d.status <> 'cancelled' AND i.productId = :productId",
    )
    suspend fun returnedProductIds(parentId: Long, productId: Long): List<Long>

    @Query(
        "SELECT CAST(COALESCE(SUM(i.quantity), 0) AS TEXT) FROM sales_docs d " +
            "JOIN sales_items i ON i.docId = d.id " +
            "WHERE d.parentId = :parentId AND d.docType = 'return' " +
            "AND d.status <> 'cancelled' AND i.productId = :productId",
    )
    suspend fun returnedQuantity(parentId: Long, productId: Long): java.math.BigDecimal

    /** Hisobot uchun: davr ichidagi tasdiqlangan savdo hujjatlari soni. */
    @Query(
        "SELECT COUNT(*) FROM sales_docs WHERE docType IN ('invoice', 'pos') " +
            "AND status IN ('confirmed', 'partial', 'paid') " +
            "AND docDate >= :dateFrom AND docDate <= :dateTo",
    )
    suspend fun countInRange(dateFrom: String, dateTo: String): Int

    /** Analitika uchun: oylar bo'yicha sof savdo dinamikasi (qaytarish manfiy hisoblanadi). */
    @Query(
        "SELECT substr(docDate, 1, 7) AS ym, " +
            "CAST(COALESCE(SUM(CASE WHEN docType = 'return' THEN -total ELSE total END), 0) AS TEXT) AS total " +
            "FROM sales_docs WHERE docType IN ('invoice', 'pos', 'return') " +
            "AND status IN ('confirmed', 'partial', 'paid') AND docDate >= :dateFrom " +
            "GROUP BY ym ORDER BY ym",
    )
    suspend fun monthlySales(dateFrom: String): List<MonthlySalesRow>
}

data class MonthlySalesRow(val ym: String, val total: java.math.BigDecimal)

@Dao
interface SalesItemDao {
    @Insert
    suspend fun insert(item: SalesItemEntity): Long

    /** Hisobot uchun: davr ichida eng ko'p sotilgan mahsulotlar (daromad bo'yicha). */
    @Query(
        "SELECT i.productId, p.name AS productName, p.unit, " +
            "CAST(SUM(i.quantity) AS TEXT) AS totalQty, CAST(SUM(i.total) AS TEXT) AS totalRevenue " +
            "FROM sales_items i " +
            "JOIN sales_docs d ON d.id = i.docId " +
            "JOIN products p ON p.id = i.productId " +
            "WHERE d.docType IN ('invoice', 'pos') AND d.status IN ('confirmed', 'partial', 'paid') " +
            "AND d.docDate >= :dateFrom AND d.docDate <= :dateTo " +
            "GROUP BY i.productId, p.name, p.unit ORDER BY SUM(i.total) DESC LIMIT :limit",
    )
    suspend fun topProducts(dateFrom: String, dateTo: String, limit: Int): List<TopProductRow>
}

data class TopProductRow(
    val productId: Long,
    val productName: String,
    val unit: String,
    val totalQty: java.math.BigDecimal,
    val totalRevenue: java.math.BigDecimal,
)

@Dao
interface PurchaseDao {
    @Insert
    suspend fun insert(purchase: PurchaseEntity): Long

    @Update
    suspend fun update(purchase: PurchaseEntity)

    @Query("SELECT * FROM purchases WHERE id = :id")
    suspend fun getById(id: Long): PurchaseEntity?

    @Query(
        "SELECT p.*, s.name AS supplierName FROM purchases p " +
            "LEFT JOIN suppliers s ON s.id = p.supplierId " +
            "WHERE (:status IS NULL OR p.status = :status) " +
            "ORDER BY p.id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(status: String?, limit: Int, offset: Int): List<PurchaseWithSupplier>

    /** QQS hisoboti uchun: kirim QQS. */
    @Query(
        "SELECT CAST(COALESCE(SUM(vatAmount), 0) AS TEXT) FROM purchases " +
            "WHERE status IN ('received', 'partial', 'paid') " +
            "AND docDate >= :dateFrom AND docDate <= :dateTo",
    )
    suspend fun inputVat(dateFrom: String, dateTo: String): java.math.BigDecimal

    /** Hisobot uchun: davr ichidagi qabul qilingan xaridlar soni. */
    @Query(
        "SELECT COUNT(*) FROM purchases WHERE status IN ('received', 'partial', 'paid') " +
            "AND docDate >= :dateFrom AND docDate <= :dateTo",
    )
    suspend fun countInRange(dateFrom: String, dateTo: String): Int

    /** Hisobot uchun: davr ichidagi xaridlar jami summasi. */
    @Query(
        "SELECT CAST(COALESCE(SUM(total), 0) AS TEXT) FROM purchases WHERE status IN ('received', 'partial', 'paid') " +
            "AND docDate >= :dateFrom AND docDate <= :dateTo",
    )
    suspend fun totalInRange(dateFrom: String, dateTo: String): java.math.BigDecimal
}

data class PurchaseWithSupplier(
    val id: Long,
    val number: String,
    val supplierId: Long?,
    val supplierName: String?,
    val status: String,
    val total: java.math.BigDecimal,
    val paidAmount: java.math.BigDecimal,
    val docDate: String,
)

@Dao
interface PurchaseItemDao {
    @Insert
    suspend fun insert(item: PurchaseItemEntity): Long

    @Query(
        "SELECT i.*, p.name AS productName, p.unit FROM purchase_items i " +
            "JOIN products p ON p.id = i.productId WHERE i.purchaseId = :purchaseId",
    )
    suspend fun itemsForPurchase(purchaseId: Long): List<PurchaseItemWithProduct>
}

data class PurchaseItemWithProduct(
    val id: Long,
    val purchaseId: Long,
    val productId: Long,
    val productName: String,
    val unit: String,
    val quantity: java.math.BigDecimal,
    val price: java.math.BigDecimal,
    val vatRate: java.math.BigDecimal,
    val vatAmount: java.math.BigDecimal,
    val total: java.math.BigDecimal,
)
