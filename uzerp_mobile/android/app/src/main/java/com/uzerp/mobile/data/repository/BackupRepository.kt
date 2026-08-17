package com.uzerp.mobile.data.repository

import android.content.Context
import android.net.Uri
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.FileExport
import com.uzerp.mobile.data.local.AppDatabase
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val SQLITE_MAGIC = "SQLite format 3"

/** Zaxiralash natijasi — [fileName] ko'rsatiladi (MediaStore [uri]ning oxirgi segmenti raqamli ID, fayl nomi emas). */
data class BackupResult(val uri: Uri, val fileName: String)

/**
 * Zaxira nusxa servisi — Python `backup.py` ning mobil analogi: butun
 * mahalliy SQLite bazasini bitta fayl sifatida Yuklab olinganlar papkasiga
 * nusxalaydi (tashqi server yo'q — hammasi shu qurilma ichida).
 */
@Singleton
class BackupRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val db: AppDatabase,
) {
    suspend fun backup(): BackupResult = withContext(Dispatchers.IO) {
        // WAL jurnalidagi o'zgarishlarni asosiy faylga yozib qo'yish — aks
        // holda backup fayli eng so'nggi yozuvlarsiz to'liqsiz bo'lishi mumkin.
        db.openHelper.writableDatabase.query("PRAGMA wal_checkpoint(FULL)").use { it.moveToFirst() }
        val dbFile = context.getDatabasePath(AppDatabase.DB_NAME)
        val bytes = dbFile.readBytes()
        val stamp = DateUtils.nowStr().replace(Regex("[^0-9]"), "")
        val fileName = "uzerp_backup_$stamp.db"
        val uri = FileExport.exportBinary(context, fileName, "application/octet-stream", bytes)
            ?: throw IOException("Zaxira faylini saqlab bo'lmadi.")
        BackupResult(uri, fileName)
    }

    /**
     * Tanlangan faylni joriy baza ustiga tiklaydi. Xavfsizlik uchun baza
     * yopiladi va -wal/-shm fayllari tozalanadi — chaqiruvchi shundan so'ng
     * jarayonni qayta ishga tushirishi shart (Room yopilgan bazani
     * qayta ochmaydi).
     */
    suspend fun restore(uri: Uri): Unit = withContext(Dispatchers.IO) {
        val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            ?: throw IOException("Faylni o'qib bo'lmadi.")
        val header = String(bytes.copyOfRange(0, minOf(SQLITE_MAGIC.length, bytes.size)), Charsets.ISO_8859_1)
        if (header != SQLITE_MAGIC) {
            throw IllegalArgumentException("Tanlangan fayl to'g'ri UzERP zaxira fayli emas.")
        }
        db.close()
        val dbFile = context.getDatabasePath(AppDatabase.DB_NAME)
        dbFile.writeBytes(bytes)
        listOf("-wal", "-shm", "-journal").forEach { suffix ->
            val sideFile = File(dbFile.path + suffix)
            if (sideFile.exists()) sideFile.delete()
        }
    }
}
