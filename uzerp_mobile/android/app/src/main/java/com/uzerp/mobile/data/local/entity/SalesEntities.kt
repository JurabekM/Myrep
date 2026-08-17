package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal

/** Savdo hujjati: quotation | order | invoice | pos | return. */
@Entity(
    tableName = "sales_docs",
    indices = [
        Index(value = ["number"], unique = true),
        Index(value = ["customerId"]),
        Index(value = ["docType", "status"]),
        Index(value = ["docDate"]),
    ],
)
data class SalesDocEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val docType: String,
    val number: String,
    val customerId: Long? = null,
    val warehouseId: Long? = null,
    val status: String = "draft",
    val subtotal: BigDecimal = BigDecimal.ZERO,
    val discount: BigDecimal = BigDecimal.ZERO,
    val vatAmount: BigDecimal = BigDecimal.ZERO,
    val total: BigDecimal = BigDecimal.ZERO,
    val paidAmount: BigDecimal = BigDecimal.ZERO,
    val currency: String = "UZS",
    val note: String = "",
    val userId: Long? = null,
    val parentId: Long? = null,
    val docDate: String = "",
    val createdAt: String = "",
    val updatedAt: String = "",
)

@Entity(tableName = "sales_items", indices = [Index(value = ["docId"])])
data class SalesItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val docId: Long,
    val productId: Long,
    val quantity: BigDecimal = BigDecimal.ONE,
    val price: BigDecimal = BigDecimal.ZERO,
    val discount: BigDecimal = BigDecimal.ZERO,
    val vatRate: BigDecimal = BigDecimal("12"),
    val vatAmount: BigDecimal = BigDecimal.ZERO,
    val total: BigDecimal = BigDecimal.ZERO,
)

@Entity(
    tableName = "purchases",
    indices = [Index(value = ["number"], unique = true), Index(value = ["supplierId"])],
)
data class PurchaseEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val number: String,
    val supplierId: Long? = null,
    val warehouseId: Long? = null,
    val status: String = "draft",
    val subtotal: BigDecimal = BigDecimal.ZERO,
    val vatAmount: BigDecimal = BigDecimal.ZERO,
    val total: BigDecimal = BigDecimal.ZERO,
    val paidAmount: BigDecimal = BigDecimal.ZERO,
    val note: String = "",
    val userId: Long? = null,
    val docDate: String = "",
    val createdAt: String = "",
    val updatedAt: String = "",
)

@Entity(tableName = "purchase_items", indices = [Index(value = ["purchaseId"])])
data class PurchaseItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val purchaseId: Long,
    val productId: Long,
    val quantity: BigDecimal = BigDecimal.ONE,
    val price: BigDecimal = BigDecimal.ZERO,
    val vatRate: BigDecimal = BigDecimal("12"),
    val vatAmount: BigDecimal = BigDecimal.ZERO,
    val total: BigDecimal = BigDecimal.ZERO,
)
