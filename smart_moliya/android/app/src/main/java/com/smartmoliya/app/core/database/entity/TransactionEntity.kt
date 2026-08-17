package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "transactions",
    foreignKeys = [
        ForeignKey(
            entity = WalletEntity::class,
            parentColumns = ["id"],
            childColumns = ["walletId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = CategoryEntity::class,
            parentColumns = ["id"],
            childColumns = ["categoryId"],
            onDelete = ForeignKey.SET_NULL
        )
    ],
    indices = [Index("walletId"), Index("categoryId"), Index("occurredAt")]
)
data class TransactionEntity(
    @PrimaryKey val id: String,
    val walletId: String,
    val categoryId: String?,
    val type: String, // INCOME | EXPENSE | TRANSFER
    val amount: Double,
    val currency: String,
    val note: String?,
    val source: String, // MANUAL | VOICE | OCR_RECEIPT | BANK_SYNC | AI_SUGGESTED
    val occurredAt: Long,
    val syncStatus: String, // PENDING | SYNCED | CONFLICT
    val version: Int
)
