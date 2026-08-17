package com.agrovision.mobile.data.repository

import android.content.Context
import android.os.Process
import com.agrovision.mobile.data.local.AppDatabase
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

data class BackupFile(val name: String, val sizeKb: Long, val createdAt: String)

/**
 * Mahalliy zaxira/tiklash — SQLite faylni to'g'ridan-to'g'ri nusxalash
 * (WAL checkpoint bilan), qurilma ichidagi `files/backups/` papkasida saqlanadi.
 * Hech qanday bulut/tarmoq ishtirok etmaydi.
 */
@Singleton
class BackupRepository @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context,
) {
    private val backupDir: File
        get() = File(context.filesDir, "backups").apply { mkdirs() }

    fun createBackup(reason: String = "manual"): BackupFile {
        val dbFile = context.getDatabasePath(AppDatabase.DB_NAME)
        // MUHIM: Cursor iteratsiya qilinmasa, ba'zi SQLite implementatsiyalarida
        // PRAGMA haqiqatda bajarilmay qolishi mumkin (lazy statement stepping) —
        // shuning uchun moveToFirst() bilan majburiy bajartiriladi.
        AppDatabase.getInstance(context).openHelper.writableDatabase
            .query("PRAGMA wal_checkpoint(FULL)").use { it.moveToFirst() }
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val target = File(backupDir, "agrovision_${stamp}_$reason.db")
        dbFile.copyTo(target, overwrite = true)
        return BackupFile(target.name, target.length() / 1024, stamp)
    }

    fun listBackups(): List<BackupFile> =
        backupDir.listFiles { f -> f.extension == "db" }
            ?.sortedByDescending { it.lastModified() }
            ?.map { BackupFile(it.name, it.length() / 1024, SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date(it.lastModified()))) }
            ?: emptyList()

    /** Bazani tiklaydi va jarayonni majburan tugatadi (Room qayta ochilishi uchun). */
    fun restoreBackup(name: String) {
        val source = File(backupDir, name)
        if (!source.exists()) return
        val dbFile = context.getDatabasePath(AppDatabase.DB_NAME)
        AppDatabase.closeInstance()
        source.copyTo(dbFile, overwrite = true)
        File(dbFile.path + "-wal").delete()
        File(dbFile.path + "-shm").delete()
        Process.killProcess(Process.myPid())
    }
}
