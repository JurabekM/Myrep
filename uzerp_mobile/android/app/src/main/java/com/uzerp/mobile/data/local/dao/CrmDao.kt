package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import com.uzerp.mobile.data.local.entity.CrmActivityEntity
import com.uzerp.mobile.data.local.entity.InventoryCountEntity
import com.uzerp.mobile.data.local.entity.InventoryCountItemEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CrmActivityDao {
    @Insert
    suspend fun insert(activity: CrmActivityEntity): Long

    @Query("UPDATE crm_activities SET status = 'done', doneAt = :doneAt WHERE id = :id")
    suspend fun markDone(id: Long, doneAt: String)

    @Query("SELECT * FROM crm_activities WHERE id = :id")
    suspend fun getById(id: Long): CrmActivityEntity?

    @Query(
        "SELECT * FROM crm_activities WHERE (:status IS NULL OR status = :status) " +
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun search(status: String?, limit: Int, offset: Int): List<CrmActivityEntity>

    @Query(
        "SELECT * FROM crm_activities WHERE status = 'open' AND dueAt IS NOT NULL " +
            "AND dueAt <= :now ORDER BY dueAt LIMIT :limit",
    )
    fun observeDueReminders(now: String, limit: Int): Flow<List<CrmActivityEntity>>

    @Query(
        "SELECT * FROM crm_activities WHERE customerId = :customerId " +
            "ORDER BY id DESC LIMIT :limit",
    )
    suspend fun forCustomer(customerId: Long, limit: Int): List<CrmActivityEntity>
}

@Dao
interface InventoryCountDao {
    @Insert
    suspend fun insert(count: InventoryCountEntity): Long

    @Insert
    suspend fun insertItem(item: InventoryCountItemEntity): Long

    @Update
    suspend fun updateItem(item: InventoryCountItemEntity)

    @Query("UPDATE inventory_counts SET status = 'done', completedAt = :completedAt WHERE id = :id")
    suspend fun complete(id: Long, completedAt: String)

    @Query("SELECT * FROM inventory_counts WHERE id = :id")
    suspend fun getById(id: Long): InventoryCountEntity?

    @Query(
        "SELECT * FROM inventory_count_items WHERE countId = :countId " +
            "AND productId = :productId",
    )
    suspend fun getItem(countId: Long, productId: Long): InventoryCountItemEntity?

    @Query(
        "SELECT i.*, p.name AS productName, p.unit, p.sku FROM inventory_count_items i " +
            "JOIN products p ON p.id = i.productId WHERE i.countId = :countId ORDER BY p.name",
    )
    suspend fun itemsForCount(countId: Long): List<InventoryCountItemWithProduct>

    @Query(
        "SELECT c.*, w.name AS warehouseName FROM inventory_counts c " +
            "JOIN warehouses w ON w.id = c.warehouseId ORDER BY c.id DESC " +
            "LIMIT :limit OFFSET :offset",
    )
    suspend fun page(limit: Int, offset: Int): List<InventoryCountWithWarehouse>
}

data class InventoryCountItemWithProduct(
    val id: Long,
    val countId: Long,
    val productId: Long,
    val expectedQty: java.math.BigDecimal,
    val actualQty: java.math.BigDecimal,
    val difference: java.math.BigDecimal,
    val productName: String,
    val unit: String,
    val sku: String?,
)

data class InventoryCountWithWarehouse(
    val id: Long,
    val number: String,
    val warehouseId: Long,
    val status: String,
    val createdAt: String,
    val completedAt: String?,
    val warehouseName: String,
)
