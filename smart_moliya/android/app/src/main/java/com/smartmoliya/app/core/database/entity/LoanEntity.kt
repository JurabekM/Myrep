package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "loans")
data class LoanEntity(
    @PrimaryKey val id: String,
    val principal: Double,
    val interestRate: Double,
    val dueDate: Long,
    val penaltyRatePerDay: Double
)
