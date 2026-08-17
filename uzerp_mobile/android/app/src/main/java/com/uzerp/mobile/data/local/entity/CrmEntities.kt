package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal

@Entity(
    tableName = "crm_activities",
    indices = [Index(value = ["customerId"]), Index(value = ["status"])],
)
data class CrmActivityEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val activityType: String = "note", // call|email|meeting|reminder|note|task
    val customerId: Long? = null,
    val leadId: Long? = null,
    val subject: String,
    val details: String = "",
    val dueAt: String? = null,
    val status: String = "open", // open|done
    val assignedTo: Long? = null,
    val createdBy: Long? = null,
    val createdAt: String = "",
    val doneAt: String? = null,
)

@Entity(tableName = "inventory_counts", indices = [Index(value = ["number"], unique = true)])
data class InventoryCountEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val number: String,
    val warehouseId: Long,
    val status: String = "draft", // draft|done
    val note: String = "",
    val userId: Long? = null,
    val createdAt: String = "",
    val completedAt: String? = null,
)

@Entity(tableName = "inventory_count_items", indices = [Index(value = ["countId"])])
data class InventoryCountItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val countId: Long,
    val productId: Long,
    val expectedQty: BigDecimal = BigDecimal.ZERO,
    val actualQty: BigDecimal = BigDecimal.ZERO,
    val difference: BigDecimal = BigDecimal.ZERO,
)
