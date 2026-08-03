package uz.dehqonkomakchi.app.work

import android.Manifest
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import uz.dehqonkomakchi.app.DehqonApp
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.data.repo.IrrigationRepository
import uz.dehqonkomakchi.app.data.repo.IrrigationUrgency
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.first

/**
 * Daily background check: fetches (or falls back to cached) weather and, if the irrigation
 * advisor says watering may be worthwhile soon, posts a low-pressure reminder notification.
 * Never posts a "hold off" notification — those are informational-only, shown in-app.
 */
@HiltWorker
class IrrigationReminderWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val userPrefs: UserPrefs,
    private val irrigationRepository: IrrigationRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val settings = userPrefs.settings.first()
        if (!settings.notificationsEnabled || settings.region.isBlank()) return Result.success()

        return try {
            val weather = irrigationRepository.getWeather(settings.region)
            val suggestion = irrigationRepository.suggest(weather, settings.lastWateredEpochDay)
            if (suggestion.urgency == IrrigationUrgency.WATER_SOON) {
                postNotification(suggestion.messageUzbek)
            }
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    private fun postNotification(message: String) {
        val context = applicationContext
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        val notification = NotificationCompat.Builder(context, DehqonApp.IRRIGATION_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(context.getString(R.string.irrigation_reminder_title))
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setAutoCancel(true)
            .build()
        val manager = context.getSystemService(NotificationManager::class.java)
        manager?.notify(NOTIFICATION_ID, notification)
    }

    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val WORK_NAME = "irrigation_reminder_daily"

        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<IrrigationReminderWorker>(1, TimeUnit.DAYS)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.KEEP, request)
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
