package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey val id: String,
    val userId: String?,
    val name: String,
    val type: String, // INCOME | EXPENSE | TRANSFER
    val icon: String
)
