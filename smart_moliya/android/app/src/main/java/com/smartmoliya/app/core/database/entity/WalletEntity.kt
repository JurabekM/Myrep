package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "wallets")
data class WalletEntity(
    @PrimaryKey val id: String,
    val name: String,
    val currency: String,
    val balance: Double,
    val isShared: Boolean,
    val syncStatus: String,
    val version: Int,
    val updatedAt: Long
)
