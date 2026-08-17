package com.agrovision.app.data.repo

import android.content.Context
import android.os.Process
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.AppDatabase
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

data class BackupFile(val name: String, val sizeKb: Long, val createdAt: String)

/**
 * Zaxira / tiklash — SQLite faylini to'g'ridan-to'g'ri nusxalash orqali.
 *
 * MUHIM: nusxalashdan oldin `PRAGMA wal_checkpoint(FULL)` bajariladi VA
 * kursor natijasi `moveToFirst()` bilan majburiy o'qiladi. Kursor
 * iteratsiya qilinmasa, SQLite PRAGMA'ni haqiqatda bajarmasligi mumkin —
 * bu holda WAL'dagi yozuvlar asosiy faylga ko'chmay, zaxira deyarli bo'sh
 * chiqadi.
 */
@Singleton
class BackupRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
) {
    private val backupDir: File
        get() = File(context.filesDir, "backups").apply { mkdirs() }

    suspend fun create(reason: String = "manual"): BackupFile = withContext(Dispatchers.IO) {
        val database = AppDatabase.getInstance(context)
        database.openHelper.writableDatabase
            .query("PRAGMA wal_checkpoint(FULL)")
            .use { it.moveToFirst() }

        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val target = File(backupDir, "agrovision_${stamp}_$reason.db")
        context.getDatabasePath(AppDatabase.DB_NAME).copyTo(target, overwrite = true)
        rotate()
        BackupFile(target.name, target.length() / 1024, Fmt.dateTime(target.lastModified()))
    }

    fun list(): List<BackupFile> =
        backupDir.listFiles { file -> file.extension == "db" }
            ?.sortedByDescending { it.lastModified() }
            ?.map { BackupFile(it.name, it.length() / 1024, Fmt.dateTime(it.lastModified())) }
            ?: emptyList()

    /** Tiklash: baza almashtiriladi va jarayon tugatiladi (Room qayta ochilishi uchun). */
    suspend fun restore(name: String): Boolean = withContext(Dispatchers.IO) {
        val source = File(backupDir, name)
        if (!source.exists() || name.contains("..")) return@withContext false
        val dbFile = context.getDatabasePath(AppDatabase.DB_NAME)
        AppDatabase.closeInstance()
        source.copyTo(dbFile, overwrite = true)
        File("${dbFile.path}-wal").delete()
        File("${dbFile.path}-shm").delete()
        true
    }

    /**
     * Tiklashdan keyin jarayonni tugatish.
     *
     * Room ochiq bazani xotirada ushlab turadi va DAO'lar Hilt singleton
     * repozitoriylarga bog'langan — tiklangan faylni ko'rish uchun jarayon
     * qayta boshlanishi SHART. Android 10+ fon rejimidan aktivlik
     * ishga tushirishni bloklaydi, shuning uchun avtomatik qayta ochish
     * kafolatlanmaydi: foydalanuvchiga avval aniq xabar ko'rsatiladi.
     */
    fun killProcess() = Process.killProcess(Process.myPid())

    suspend fun delete(name: String): Boolean = withContext(Dispatchers.IO) {
        if (name.contains("..")) return@withContext false
        File(backupDir, name).delete()
    }

    private suspend fun rotate() {
        val keep = settingsRepository.get("backup_keep", "20").toIntOrNull() ?: 20
        backupDir.listFiles { file -> file.extension == "db" }
            ?.sortedByDescending { it.lastModified() }
            ?.drop(keep)
            ?.forEach { it.delete() }
    }
}
