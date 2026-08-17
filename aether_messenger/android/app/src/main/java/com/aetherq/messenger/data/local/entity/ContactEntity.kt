package com.aetherq.messenger.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/** QR orqali olingan kontaktning uzoq-muddatli ochiq kalitlari (spec 3-bo'lim primitivlari). */
@Entity(tableName = "contacts")
data class ContactEntity(
    @PrimaryKey val userId: String,
    val displayName: String,
    val edPkHex: String,
    val xPkHex: String,
    val mlkemPkHex: String,
    val createdAt: Long,
)
