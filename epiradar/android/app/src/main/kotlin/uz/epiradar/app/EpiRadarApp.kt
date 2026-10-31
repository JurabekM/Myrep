package uz.epiradar.app

import android.app.Application

/** Ilova kirish nuqtasi: bildirishnoma kanallari va fon sinxronlash jadvali. */
class EpiRadarApp : Application() {
    val repository: Repository by lazy { Repository(this) }

    override fun onCreate() {
        super.onCreate()
        Notifier.createChannels(this)
        SyncScheduler.schedule(this, repository.settings(), replace = false)
    }
}
