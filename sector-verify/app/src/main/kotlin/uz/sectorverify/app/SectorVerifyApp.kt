package uz.sectorverify.app

import android.app.Application
import android.os.StrictMode
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject
import javax.inject.Provider
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.ui.util.CrashLog

@HiltAndroidApp
class SectorVerifyApp : Application() {
    @Inject lateinit var database: Provider<SectorVerifyDatabase>

    override fun onCreate() {
        super.onCreate()
        CrashLog.install(this, BuildConfig.VERSION_NAME)
        if (BuildConfig.DEBUG) {
            StrictMode.setThreadPolicy(StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build())
            StrictMode.setVmPolicy(StrictMode.VmPolicy.Builder().detectAll().penaltyLog().build())
        }
        // Kalitni ochish (Keystore) va SQLCipher kutubxonasini yuklash asosiy oqimdan tashqarida (§5: ANR yo'q).
        // Bu yerdagi xato halokatli emas: birinchi haqiqiy so'rov uni o'z yo'lida xabar qiladi.
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch { runCatching { database.get().openHelper.writableDatabase } }
    }
}
