package com.agrovision.app.data.repo

import android.content.Context
import com.agrovision.app.data.local.AppDatabase
import com.agrovision.app.data.local.DemoSeeder
import com.agrovision.app.data.local.TableCountRow
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Birinchi ishga tushirish oqimi (desktop `run.py initialize()` analogi):
 * papkalar/baza → ma'lumotnoma → (tanlansa) namuna ma'lumotlar → ML modellari.
 */
@Singleton
class BootstrapRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val database: AppDatabase,
    private val settingsRepository: SettingsRepository,
    private val mlRepository: MlRepository,
    private val authRepository: AuthRepository,
) {
    /** Ma'lumotnoma va sozlamalarni tayyorlaydi. Yangi o'rnatishda `true`. */
    suspend fun prepare(): Boolean {
        val fresh = DemoSeeder.bootstrap(database, context)
        settingsRepository.ensureDefaults()
        settingsRepository.loadGlobals()
        return fresh
    }

    suspend fun hasDemoData(): Boolean = DemoSeeder.hasDemoBusinessData(database)

    /** Namuna ma'lumotlar to'plamini yaratadi va ML modellarini o'qitadi. */
    suspend fun loadDemoData(onProgress: (String, Int) -> Unit) {
        DemoSeeder.seedDemoBusinessData(database) { progress ->
            onProgress(progress.step, progress.percent)
        }
        onProgress("ML modellari o'qitilmoqda", 100)
        mlRepository.trainAll { step -> onProgress(step, 100) }
        authRepository.audit("demo_data_loaded", details = "Namuna ma'lumotlar to'plami yaratildi")
    }

    /** Modellar mavjud bo'lmasa o'qitadi (masalan ma'lumot qo'lda kiritilgandan keyin). */
    suspend fun ensureModels(onProgress: (String) -> Unit = {}) {
        if (database.yieldDao().count() >= 20) mlRepository.trainIfNeeded(onProgress)
    }

    suspend fun tableCounts(): List<TableCountRow> = database.tableCounts()
}
