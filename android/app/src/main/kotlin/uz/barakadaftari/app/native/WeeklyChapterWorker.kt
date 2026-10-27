package uz.barakadaftari.app.native

import android.content.Context
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.time.Duration
import java.time.ZonedDateTime
import java.util.concurrent.TimeUnit

/**
 * Juma 09:00 — «Yangi bob / haftalik yakun». Ko'rsatgach keyingi jumani o'zi
 * rejalashtiradi. WorkManager ishlari qurilma qayta yoqilganda tiklanadi.
 */
class WeeklyChapterWorker(context: Context, params: WorkerParameters) :
    Worker(context, params) {

    override fun doWork(): Result {
        val title = inputData.getString(KEY_TITLE).orEmpty()
        val body = inputData.getString(KEY_BODY).orEmpty()
        val channel = inputData.getString(KEY_CHANNEL).orEmpty()
        ReminderScheduler.notify(applicationContext, NOTIFICATION_ID, title, body, channel)
        schedule(applicationContext, title, body, channel, ExistingWorkPolicy.APPEND_OR_REPLACE)
        return Result.success()
    }

    companion object {
        const val UNIQUE = "weekly_chapter"
        const val NOTIFICATION_ID = "weekly_chapter"
        private const val KEY_TITLE = "title"
        private const val KEY_BODY = "body"
        private const val KEY_CHANNEL = "channel"

        fun schedule(
            context: Context,
            title: String,
            body: String,
            channel: String,
            policy: ExistingWorkPolicy,
        ) {
            val now = ZonedDateTime.now(ReminderSchedule.ZONE)
            val delay = Duration.between(now, ReminderSchedule.nextFriday(now)).toMillis()
            val request = OneTimeWorkRequestBuilder<WeeklyChapterWorker>()
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .setInputData(
                    Data.Builder()
                        .putString(KEY_TITLE, title)
                        .putString(KEY_BODY, body)
                        .putString(KEY_CHANNEL, channel)
                        .build(),
                )
                .addTag(UNIQUE)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(UNIQUE, policy, request)
        }
    }
}
