package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal

@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val parentId: Long? = null,
    val isActive: Boolean = true,
)

@Entity(
    tableName = "products",
    indices = [
        Index(value = ["sku"], unique = true),
        Index(value = ["barcode"]),
        Index(value = ["name"]),
    ],
)
data class ProductEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sku: String? = null,
    val barcode: String = "",
    val name: String,
    val categoryId: Long? = null,
    val unit: String = "dona",
    val costPrice: BigDecimal = BigDecimal.ZERO,
    val salePrice: BigDecimal = BigDecimal.ZERO,
    val vatRate: BigDecimal = BigDecimal("12"),
    val minStock: BigDecimal = BigDecimal.ZERO,
    val description: String = "",
    val isActive: Boolean = true,
    val createdAt: String = "",
    val updatedAt: String = "",
)

@Entity(tableName = "warehouses")
data class WarehouseEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val address: String = "",
    val isActive: Boolean = true,
)

@Entity(
    tableName = "stock",
    indices = [Index(value = ["productId", "warehouseId"], unique = true)],
)
data class StockEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val productId: Long,
    val warehouseId: Long,
    val quantity: BigDecimal = BigDecimal.ZERO,
)

@Entity(
    tableName = "stock_moves",
    indices = [Index(value = ["productId"]), Index(value = ["createdAt"])],
)
data class StockMoveEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val moveType: String, // in | out | transfer | adjust
    val productId: Long,
    val warehouseFrom: Long? = null,
    val warehouseTo: Long? = null,
    val quantity: BigDecimal,
    val unitCost: BigDecimal = BigDecimal.ZERO,
    val refType: String = "",
    val refId: Long? = null,
    val note: String = "",
    val userId: Long? = null,
    val createdAt: String = "",
)
