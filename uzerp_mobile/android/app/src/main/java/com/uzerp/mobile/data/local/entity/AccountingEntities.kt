package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal

/** Hisoblar rejasi (O'zbekiston NAS-21 asosida). */
@Entity(tableName = "accounts", indices = [Index(value = ["code"], unique = true)])
data class AccountEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String,
    val name: String,
    val type: String, // asset|contra_asset|liability|equity|income|expense
    val isCash: Boolean = false,
    val isBank: Boolean = false,
    val parentCode: String = "",
    val isActive: Boolean = true,
)

@Entity(
    tableName = "journal_entries",
    indices = [Index(value = ["entryDate"]), Index(value = ["refType"])],
)
data class JournalEntryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val number: String,
    val entryDate: String,
    val memo: String = "",
    val refType: String = "",
    val refId: Long? = null,
    val userId: Long? = null,
    val isPosted: Boolean = true,
    val createdAt: String = "",
)

@Entity(
    tableName = "journal_lines",
    indices = [Index(value = ["entryId"]), Index(value = ["accountId"])],
)
data class JournalLineEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val entryId: Long,
    val accountId: Long,
    val debit: BigDecimal = BigDecimal.ZERO,
    val credit: BigDecimal = BigDecimal.ZERO,
    val partnerType: String = "",
    val partnerId: Long? = null,
)

@Entity(
    tableName = "payments",
    indices = [Index(value = ["number"], unique = true), Index(value = ["paymentDate"])],
)
data class PaymentEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val number: String,
    val paymentType: String, // in | out
    val method: String = "cash",
    val accountId: Long? = null,
    val corrAccountId: Long? = null,
    val partnerType: String = "",
    val partnerId: Long? = null,
    val refType: String = "",
    val refId: Long? = null,
    val amount: BigDecimal = BigDecimal.ZERO,
    val paymentDate: String = "",
    val note: String = "",
    val userId: Long? = null,
    val createdAt: String = "",
)

@Entity(tableName = "assets")
data class AssetEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String = "",
    val name: String,
    val purchaseDate: String = "",
    val cost: BigDecimal = BigDecimal.ZERO,
    val salvageValue: BigDecimal = BigDecimal.ZERO,
    val usefulLifeMonths: Int = 60,
    val depreciationMethod: String = "straight_line",
    val accumulatedDepreciation: BigDecimal = BigDecimal.ZERO,
    val status: String = "active",
    val note: String = "",
    val createdAt: String = "",
)
