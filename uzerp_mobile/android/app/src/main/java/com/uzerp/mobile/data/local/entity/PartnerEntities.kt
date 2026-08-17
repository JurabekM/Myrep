package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal

@Entity(tableName = "customers", indices = [Index(value = ["name"])])
data class CustomerEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String = "",
    val name: String,
    val tin: String = "",
    val phone: String = "",
    val email: String = "",
    val address: String = "",
    val creditLimit: BigDecimal = BigDecimal.ZERO,
    val discountPercent: BigDecimal = BigDecimal.ZERO,
    val note: String = "",
    val isActive: Boolean = true,
    val createdAt: String = "",
    val updatedAt: String = "",
)

@Entity(tableName = "suppliers", indices = [Index(value = ["name"])])
data class SupplierEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String = "",
    val name: String,
    val tin: String = "",
    val phone: String = "",
    val email: String = "",
    val address: String = "",
    val note: String = "",
    val isActive: Boolean = true,
    val createdAt: String = "",
    val updatedAt: String = "",
)

@Entity(tableName = "leads")
data class LeadEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val phone: String = "",
    val email: String = "",
    val source: String = "",
    val status: String = "new", // new|contacted|qualified|won|lost
    val customerId: Long? = null,
    val assignedTo: Long? = null,
    val note: String = "",
    val createdAt: String = "",
    val updatedAt: String = "",
)
