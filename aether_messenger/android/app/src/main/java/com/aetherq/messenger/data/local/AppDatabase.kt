package com.aetherq.messenger.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.aetherq.messenger.data.local.dao.ContactDao
import com.aetherq.messenger.data.local.dao.MessageDao
import com.aetherq.messenger.data.local.entity.ContactEntity
import com.aetherq.messenger.data.local.entity.MessageEntity
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory

/** Offline mahalliy baza — SQLCipher bilan AES-256 shifrlangan (`DatabaseKeyProvider` orqali). */
@Database(entities = [ContactEntity::class, MessageEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun contactDao(): ContactDao
    abstract fun messageDao(): MessageDao

    companion object {
        const val DATABASE_NAME = "aether_messenger.db"

        fun build(context: Context): AppDatabase {
            System.loadLibrary("sqlcipher")
            val passphrase = DatabaseKeyProvider(context).getOrCreatePassphrase()
            val factory = SupportOpenHelperFactory(passphrase)

            return Room.databaseBuilder(context, AppDatabase::class.java, DATABASE_NAME)
                .openHelperFactory(factory)
                .fallbackToDestructiveMigration()
                .build()
        }
    }
}
