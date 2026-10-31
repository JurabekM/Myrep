package uz.epiradar.app

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import uz.epiradar.engine.model.Settings
import java.util.concurrent.TimeUnit

/** Fon sinxronlash: manbalarni yangilaydi, yangi xavflar haqida xabar beradi, vidjetni yangilaydi. */
class SyncWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val repo = (applicationContext as EpiRadarApp).repository
        return try {
            val result = repo.sync()
            result.notifications.forEach { Notifier.show(applicationContext, it) }
            RiskWidgetProvider.update(applicationContext, result.snapshot)
            // Hech bir manba ishlamasa (masalan, internet yo'q) — keyinroq qayta urinish.
            if (result.snapshot.sources.none { it.ok }) Result.retry() else Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}

object SyncScheduler {
    private const val WORK = "epiradar-sync"

    fun schedule(
        context: Context,
        settings: Settings,
        replace: Boolean,
    ) {
        val request =
            PeriodicWorkRequestBuilder<SyncWorker>(settings.syncHours.toLong(), TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
        WorkManager
            .getInstance(context)
            .enqueueUniquePeriodicWork(
                WORK,
                if (replace) ExistingPeriodicWorkPolicy.UPDATE else ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
    }
}
