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
        // Key unwrap (Keystore) and SQLCipher library load off the main thread (§5: no ANR).
        // A failure here is not fatal: the first real query reports it on its own path.
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch { runCatching { database.get().openHelper.writableDatabase } }
    }
}
