package com.uzerp.mobile.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Update
import com.uzerp.mobile.data.local.entity.AuditLogEntity
import com.uzerp.mobile.data.local.entity.SequenceEntity
import com.uzerp.mobile.data.local.entity.SettingEntity
import com.uzerp.mobile.data.local.entity.UserEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface UserDao {
    @Insert
    suspend fun insert(user: UserEntity): Long

    @Update
    suspend fun update(user: UserEntity)

    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun getById(id: Long): UserEntity?

    @Query("SELECT * FROM users WHERE LOWER(username) = LOWER(:username)")
    suspend fun getByUsername(username: String): UserEntity?

    @Query("SELECT * FROM users ORDER BY id")
    fun observeAll(): Flow<List<UserEntity>>

    @Query("SELECT COUNT(*) FROM users")
    suspend fun count(): Int

    @Query("SELECT COUNT(*) FROM users WHERE role = 'administrator'")
    suspend fun countAdmins(): Int
}

@Dao
interface AuditDao {
    @Insert
    suspend fun insert(entry: AuditLogEntity): Long

    @Query(
        "SELECT * FROM audit_log WHERE (:category IS NULL OR category = :category) " +
            "ORDER BY id DESC LIMIT :limit OFFSET :offset",
    )
    suspend fun recent(category: String?, limit: Int, offset: Int): List<AuditLogEntity>

    @Query("SELECT COUNT(*) FROM audit_log WHERE (:category IS NULL OR category = :category)")
    suspend fun countByCategory(category: String?): Int
}

@Dao
interface SettingsDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(setting: SettingEntity)

    @Query("SELECT * FROM settings")
    fun observeAll(): Flow<List<SettingEntity>>

    @Query("SELECT value FROM settings WHERE key = :key")
    suspend fun getValue(key: String): String?
}

@Dao
interface SequenceDao {
    @Query("SELECT lastValue FROM sequences WHERE name = :name AND year = :year")
    suspend fun getValue(name: String, year: Int): Int?

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertIfAbsent(sequence: SequenceEntity)

    @Query("UPDATE sequences SET lastValue = lastValue + 1 WHERE name = :name AND year = :year")
    suspend fun increment(name: String, year: Int)

    /**
     * Keyingi hujjat raqamini oladi (masalan `INV-2026-000001`).
     * Bitta tranzaksiya ichida chaqiriladi — poyga holatidan himoya
     * [androidx.room.withTransaction] orqali ta'minlanadi.
     */
    @Transaction
    suspend fun next(name: String, year: Int): Int {
        insertIfAbsent(SequenceEntity(name, year, 0))
        increment(name, year)
        return getValue(name, year) ?: 1
    }
}
