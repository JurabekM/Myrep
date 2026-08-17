package com.smartmoliya.app.core.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Offline rejim uchun lokal vazifa/mukofot (Family Mode'ning bir qurilmalik varianti).
 * Status: PENDING -> DONE -> APPROVED (tasdiqlanganda mukofot hamyonga tushadi).
 */
@Entity(tableName = "local_tasks")
data class LocalTaskEntity(
    @PrimaryKey val id: String,
    val title: String,
    val rewardAmount: Double,
    val status: String, // PENDING | DONE | APPROVED
    val createdAt: Long
)
