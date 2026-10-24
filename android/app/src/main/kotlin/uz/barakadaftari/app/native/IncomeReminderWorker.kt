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
 * «Daromadni yozdingizmi?» — onboarding'dagi daromad turiga mos (Vazifa 15).
 * Ko'rsatgach keyingisini o'zi rejalashtiradi; summa yozilmaydi.
 */
class IncomeReminderWorker(context: Context, params: WorkerParameters) :
    Worker(context, params) {

    override fun doWork(): Result {
        val kind = IncomeReminderKind.ofRaw(inputData.getInt(KEY_KIND, 0)) ?: IncomeReminderKind.DAILY
        val day = inputData.getInt(KEY_DAY, 1)
        val title = inputData.getString(KEY_TITLE).orEmpty()
        val body = inputData.getString(KEY_BODY).orEmpty()
        val channel = inputData.getString(KEY_CHANNEL).orEmpty()
        ReminderScheduler.notify(applicationContext, NOTIFICATION_ID, title, body, channel)
        schedule(applicationContext, kind, day, title, body, channel, ExistingWorkPolicy.APPEND_OR_REPLACE)
        return Result.success()
    }

    companion object {
        const val UNIQUE = "income_reminder"
        const val NOTIFICATION_ID = "income_reminder"
        private const val KEY_KIND = "kind"
        private const val KEY_DAY = "day"
        private const val KEY_TITLE = "title"
        private const val KEY_BODY = "body"
        private const val KEY_CHANNEL = "channel"

        fun schedule(
            context: Context,
            kind: IncomeReminderKind,
            dayOfMonth: Int,
            title: String,
            body: String,
            channel: String,
            policy: ExistingWorkPolicy,
        ) {
            val now = ZonedDateTime.now(ReminderSchedule.ZONE)
            val at = ReminderSchedule.nextIncome(now, kind, dayOfMonth)
            val request = OneTimeWorkRequestBuilder<IncomeReminderWorker>()
                .setInitialDelay(Duration.between(now, at).toMillis(), TimeUnit.MILLISECONDS)
                .setInputData(
                    Data.Builder()
                        .putInt(KEY_KIND, kind.raw)
                        .putInt(KEY_DAY, dayOfMonth)
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
