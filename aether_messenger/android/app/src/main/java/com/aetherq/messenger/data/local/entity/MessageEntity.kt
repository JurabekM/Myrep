package com.aetherq.messenger.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/** Bitta matnli xabar (deshifrlangan holda saqlanadi — baza SQLCipher bilan shifrlangan). */
@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val contactUserId: String,
    val isOutgoing: Boolean,
    val plaintext: String,
    val timestamp: Long,
)
