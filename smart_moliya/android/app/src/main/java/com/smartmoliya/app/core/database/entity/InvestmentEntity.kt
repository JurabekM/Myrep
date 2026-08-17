package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "investments")
data class InvestmentEntity(
    @PrimaryKey val id: String,
    val assetType: String, // GOLD | USD | CRYPTO | STOCK | ETF | BOND
    val quantity: Double,
    val avgPrice: Double
)
