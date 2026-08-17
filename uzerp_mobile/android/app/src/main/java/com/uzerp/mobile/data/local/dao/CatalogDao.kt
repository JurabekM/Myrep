package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.uzerp.mobile.data.local.entity.CategoryEntity
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.local.entity.StockEntity
import com.uzerp.mobile.data.local.entity.StockMoveEntity
import com.uzerp.mobile.data.local.entity.WarehouseEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CategoryDao {
    @Insert
    suspend fun insert(category: CategoryEntity): Long

    @Query("SELECT * FROM categories WHERE isActive = 1 ORDER BY name")
    fun observeAll(): Flow<List<CategoryEntity>>
}

@Dao
interface ProductDao {
    @Insert
    suspend fun insert(product: ProductEntity): Long

    @Update
    suspend fun update(product: ProductEntity)

    @Query("UPDATE products SET sku = :sku WHERE id = :id")
    suspend fun setSku(id: Long, sku: String)

    @Query("UPDATE products SET costPrice = :cost WHERE id = :id")
    suspend fun setCostPrice(id: Long, cost: java.math.BigDecimal)

    @Query("UPDATE products SET isActive = 0 WHERE id = :id")
    suspend fun deactivate(id: Long)

    @Query("SELECT * FROM products WHERE id = :id")
    suspend fun getById(id: Long): ProductEntity?

    @Query("SELECT * FROM products WHERE barcode = :barcode AND isActive = 1 LIMIT 1")
    suspend fun findByBarcode(barcode: String): ProductEntity?

    @Query(
        "SELECT * FROM products WHERE isActive = 1 " +
            "AND (:search IS NULL OR name LIKE '%' || :search || '%' " +
            "OR sku LIKE '%' || :search || '%' OR barcode LIKE '%' || :search || '%') " +
            "AND (:categoryId IS NULL OR categoryId = :categoryId) " +
            "ORDER BY name LIMIT :limit OFFSET :offset",
    )
    suspend fun search(
        search: String?,
        categoryId: Long?,
        limit: Int,
        offset: Int,
    ): List<ProductEntity>

    @Query(
        "SELECT COUNT(*) FROM products WHERE isActive = 1 " +
            "AND (:search IS NULL OR name LIKE '%' || :search || '%' " +
            "OR sku LIKE '%' || :search || '%' OR barcode LIKE '%' || :search || '%') " +
            "AND (:categoryId IS NULL OR categoryId = :categoryId)",
    )
    suspend fun searchCount(search: String?, categoryId: Long?): Int

    @Query("SELECT * FROM products WHERE isActive = 1 ORDER BY name")
    fun observeActive(): Flow<List<ProductEntity>>

    /**
     * Kam qolgan mahsulotlar (faqat min. zaxira belgilanganlar orasidan).
     *
     * MUHIM: taqqoslashda ikkala tomon CAST(... AS REAL) qilinadi — minStock
     * TEXT ustun, SUM() esa REAL qiymat; SQLite'da affinity'siz REAL qiymat
     * TEXT qiymatdan HAR DOIM kichik sanaladi (tur tartibi bo'yicha), ya'ni
     * cast'siz shart doim TRUE bo'lib har qanday mahsulot "kam qolgan" deb
     * chiqadi. currentStock esa CAST(... AS TEXT) — CursorWindow %g aniqlik
     * yo'qotishidan himoya.
     */
    @Query(
        "SELECT p.id, p.name, p.sku, p.unit, p.minStock, " +
            "CAST(COALESCE((SELECT SUM(s.quantity) FROM stock s WHERE s.productId = p.id), 0) AS TEXT) AS currentStock " +
            "FROM products p WHERE p.isActive = 1 AND CAST(p.minStock AS REAL) > 0 " +
            "AND COALESCE((SELECT SUM(CAST(s.quantity AS REAL)) FROM stock s WHERE s.productId = p.id), 0) <= CAST(p.minStock AS REAL) " +
            "ORDER BY p.name",
    )
    suspend fun lowStockProducts(): List<LowStockRow>
}

data class LowStockRow(
    val id: Long,
    val name: String,
    val sku: String?,
    val unit: String,
    val minStock: java.math.BigDecimal,
    val currentStock: java.math.BigDecimal,
)

@Dao
interface WarehouseDao {
    @Insert
    suspend fun insert(warehouse: WarehouseEntity): Long

    @Query("SELECT * FROM warehouses WHERE isActive = 1 ORDER BY id")
    fun observeAll(): Flow<List<WarehouseEntity>>

    @Query("SELECT id FROM warehouses WHERE isActive = 1 ORDER BY id LIMIT 1")
    suspend fun defaultWarehouseId(): Long?
}

@Dao
interface StockDao {
    @Query("SELECT * FROM stock WHERE productId = :productId AND warehouseId = :warehouseId")
    suspend fun get(productId: Long, warehouseId: Long): StockEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(stock: StockEntity)

    @Query("SELECT CAST(COALESCE(SUM(quantity), 0) AS TEXT) FROM stock WHERE productId = :productId")
    suspend fun totalForProduct(productId: Long): java.math.BigDecimal

    @Query(
        "SELECT CAST(COALESCE(SUM(quantity), 0) AS TEXT) FROM stock " +
            "WHERE productId = :productId AND warehouseId = :warehouseId",
    )
    suspend fun levelForWarehouse(productId: Long, warehouseId: Long): java.math.BigDecimal

    @Query("SELECT * FROM stock WHERE warehouseId = :warehouseId AND CAST(quantity AS REAL) <> 0")
    suspend fun byWarehouse(warehouseId: Long): List<StockEntity>
}

@Dao
interface StockMoveDao {
    @Insert
    suspend fun insert(move: StockMoveEntity): Long

    @Query(
        "SELECT * FROM stock_moves WHERE " +
            "(:productId IS NULL OR productId = :productId) " +
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun recent(productId: Long?, limit: Int, offset: Int): List<StockMoveEntity>
}
