package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/** Foydalanuvchilar (autentifikatsiya + RBAC). */
@Entity(tableName = "users", indices = [Index(value = ["username"], unique = true)])
data class UserEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val username: String,
    val passwordHash: String,
    val fullName: String = "",
    val role: String = "guest",
    val email: String = "",
    val phone: String = "",
    val isActive: Boolean = true,
    val failedAttempts: Int = 0,
    val lockedUntil: String? = null,
    val lastLogin: String? = null,
    val mustChangePassword: Boolean = false,
    val createdAt: String = "",
    val updatedAt: String = "",
)

/** Audit va xavfsizlik hodisalari jurnali. */
@Entity(
    tableName = "audit_log",
    indices = [Index(value = ["createdAt"]), Index(value = ["category"])],
)
data class AuditLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val userId: Long? = null,
    val username: String = "",
    val action: String,
    val entity: String = "",
    val entityId: String = "",
    val details: String = "",
    val category: String = "audit",
    val createdAt: String = "",
)

/** Tizim sozlamalari (kompaniya nomi, STIR va h.k.). */
@Entity(tableName = "settings")
data class SettingEntity(
    @PrimaryKey val key: String,
    val value: String = "",
    val updatedAt: String = "",
)

/** Hujjat raqamlash hisoblagichlari (yil kesimida). */
@Entity(tableName = "sequences", primaryKeys = ["name", "year"])
data class SequenceEntity(
    val name: String,
    val year: Int,
    val lastValue: Int = 0,
)
