package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import com.uzerp.mobile.data.local.entity.CustomerEntity
import com.uzerp.mobile.data.local.entity.LeadEntity
import com.uzerp.mobile.data.local.entity.SupplierEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CustomerDao {
    @Insert
    suspend fun insert(customer: CustomerEntity): Long

    @Update
    suspend fun update(customer: CustomerEntity)

    @Query("SELECT * FROM customers WHERE id = :id")
    suspend fun getById(id: Long): CustomerEntity?

    @Query(
        "SELECT * FROM customers WHERE isActive = 1 " +
            "AND (:search IS NULL OR name LIKE '%' || :search || '%' " +
            "OR phone LIKE '%' || :search || '%') " +
            "ORDER BY name LIMIT :limit OFFSET :offset",
    )
    suspend fun search(search: String?, limit: Int, offset: Int): List<CustomerEntity>

    @Query(
        "SELECT COUNT(*) FROM customers WHERE isActive = 1 " +
            "AND (:search IS NULL OR name LIKE '%' || :search || '%' " +
            "OR phone LIKE '%' || :search || '%')",
    )
    suspend fun searchCount(search: String?): Int

    @Query("SELECT * FROM customers WHERE isActive = 1 ORDER BY name")
    fun observeAll(): Flow<List<CustomerEntity>>

    /** Hisobot uchun: to'liq to'lanmagan savdo hujjatlari bo'yicha mijozlar qarzi. */
    @Query(
        "SELECT d.customerId AS partnerId, c.name AS partnerName, " +
            "CAST(SUM(d.total - d.paidAmount) AS TEXT) AS debt FROM sales_docs d " +
            "JOIN customers c ON c.id = d.customerId " +
            "WHERE d.docType IN ('invoice', 'pos') AND d.status IN ('confirmed', 'partial') " +
            "GROUP BY d.customerId, c.name HAVING SUM(d.total - d.paidAmount) > 0 " +
            "ORDER BY SUM(d.total - d.paidAmount) DESC",
    )
    suspend fun customerDebts(): List<DebtRow>
}

data class DebtRow(val partnerId: Long, val partnerName: String, val debt: java.math.BigDecimal)

@Dao
interface SupplierDao {
    @Insert
    suspend fun insert(supplier: SupplierEntity): Long

    @Update
    suspend fun update(supplier: SupplierEntity)

    @Query("SELECT * FROM suppliers WHERE id = :id")
    suspend fun getById(id: Long): SupplierEntity?

    @Query(
        "SELECT * FROM suppliers WHERE isActive = 1 " +
            "AND (:search IS NULL OR name LIKE '%' || :search || '%') " +
            "ORDER BY name LIMIT :limit OFFSET :offset",
    )
    suspend fun search(search: String?, limit: Int, offset: Int): List<SupplierEntity>

    @Query("SELECT * FROM suppliers WHERE isActive = 1 ORDER BY name")
    fun observeAll(): Flow<List<SupplierEntity>>

    /** Hisobot uchun: to'liq to'lanmagan xaridlar bo'yicha ta'minotchilarga qarz. */
    @Query(
        "SELECT p.supplierId AS partnerId, s.name AS partnerName, " +
            "CAST(SUM(p.total - p.paidAmount) AS TEXT) AS debt FROM purchases p " +
            "JOIN suppliers s ON s.id = p.supplierId " +
            "WHERE p.status IN ('received', 'partial') " +
            "GROUP BY p.supplierId, s.name HAVING SUM(p.total - p.paidAmount) > 0 " +
            "ORDER BY SUM(p.total - p.paidAmount) DESC",
    )
    suspend fun supplierDebts(): List<DebtRow>
}

@Dao
interface LeadDao {
    @Insert
    suspend fun insert(lead: LeadEntity): Long

    @Update
    suspend fun update(lead: LeadEntity)

    @Query("SELECT * FROM leads WHERE id = :id")
    suspend fun getById(id: Long): LeadEntity?

    @Query(
        "SELECT * FROM leads WHERE (:status IS NULL OR status = :status) " +
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(status: String?, limit: Int, offset: Int): List<LeadEntity>

    @Query("SELECT * FROM leads ORDER BY id DESC")
    fun observeAll(): Flow<List<LeadEntity>>
}
