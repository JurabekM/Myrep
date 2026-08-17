package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "debts")
data class DebtEntity(
    @PrimaryKey val id: String,
    val direction: String, // LENT | BORROWED
    val counterparty: String,
    val amount: Double,
    val dueDate: Long,
    val isSettled: Boolean
)
