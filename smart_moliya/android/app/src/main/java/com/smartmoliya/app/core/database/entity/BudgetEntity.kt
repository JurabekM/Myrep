package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "budgets")
data class BudgetEntity(
    @PrimaryKey val id: String,
    val categoryId: String?,
    val period: String, // DAILY | WEEKLY | MONTHLY
    val limitAmount: Double,
    val startDate: Long
)
