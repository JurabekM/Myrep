package uz.epiradar.app

import android.app.Application

/** Ilova kirish nuqtasi: bildirishnoma kanallari va fon sinxronlash jadvali. */
class EpiRadarApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifier.createChannels(this)
        SyncScheduler.schedule(this, Repository.get(this).settings(), replace = false)
    }
}
