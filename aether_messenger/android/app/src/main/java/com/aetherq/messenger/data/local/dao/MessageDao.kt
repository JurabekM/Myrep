package com.aetherq.messenger.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.aetherq.messenger.data.local.entity.MessageEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MessageDao {
    @Insert
    suspend fun insert(message: MessageEntity): Long

    @Query("SELECT * FROM messages WHERE contactUserId = :contactUserId ORDER BY timestamp ASC")
    fun observeForContact(contactUserId: String): Flow<List<MessageEntity>>
}
