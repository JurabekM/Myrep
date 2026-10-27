package uz.barakadaftari.app.native

import android.content.Context
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.time.DayOfWeek
import java.time.Duration
import java.time.ZonedDateTime
import java.util.concurrent.TimeUnit

/**
 * «Juma shirinligi» (SPEC 2B.4): har hafta tanlangan kuni 09:00 quvonchli
 * eslatma. Ko'rsatgach keyingi haftani o'zi rejalashtiradi.
 */
class TreatReminderWorker(context: Context, params: WorkerParameters) :
    Worker(context, params) {

    override fun doWork(): Result {
        val treat = Treat(
            id = inputData.getString(KEY_ID).orEmpty(),
            weekday = inputData.getInt(KEY_WEEKDAY, DayOfWeek.FRIDAY.value),
            title = inputData.getString(KEY_TITLE).orEmpty(),
            body = inputData.getString(KEY_BODY).orEmpty(),
        )
        val channel = inputData.getString(KEY_CHANNEL).orEmpty()
        ReminderScheduler.notify(applicationContext, "treat:${treat.id}", treat.title, treat.body, channel)
        // Shu daqiqada qayta ishga tushmasligi uchun keyingi hafta hisobi
        // bir daqiqa keyingi vaqtdan boshlanadi.
        enqueue(applicationContext, treat, channel, ExistingWorkPolicy.APPEND_OR_REPLACE, ZonedDateTime.now().plusMinutes(1))
        return Result.success()
    }

    data class Treat(val id: String, val weekday: Int, val title: String, val body: String)

    companion object {
        const val TAG = "treat_reminder"
        private const val PREFS = "treat_reminders"
        private const val KEY_SCHEDULED = "__scheduled"
        private const val KEY_ID = "id"
        private const val KEY_WEEKDAY = "weekday"
        private const val KEY_TITLE = "title"
        private const val KEY_BODY = "body"
        private const val KEY_CHANNEL = "channel"

        fun uniqueName(id: String) = "treat:$id"

        /** Ro'yxatni aynan shu holatga keltiradi: yo'qlari bekor qilinadi. */
        fun sync(context: Context, treats: List<Treat>, channelName: String) {
            val wm = WorkManager.getInstance(context)
            val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val keep = treats.map { it.id }.toSet()
            prefs.getStringSet(KEY_SCHEDULED, emptySet()).orEmpty()
                .filter { it !in keep }
                .forEach { wm.cancelUniqueWork(uniqueName(it)) }
            prefs.edit().putStringSet(KEY_SCHEDULED, keep).apply()
            treats.forEach { enqueue(context, it, channelName, ExistingWorkPolicy.REPLACE) }
        }

        fun enqueue(
            context: Context,
            treat: Treat,
            channelName: String,
            policy: ExistingWorkPolicy,
            from: ZonedDateTime = ZonedDateTime.now(ReminderSchedule.ZONE),
        ) {
            val now = ZonedDateTime.now(ReminderSchedule.ZONE)
            val at = ReminderSchedule.nextWeekday(from, DayOfWeek.of(treat.weekday.coerceIn(1, 7)))
            val delay = Duration.between(now, at).toMillis().coerceAtLeast(0)
            val request = OneTimeWorkRequestBuilder<TreatReminderWorker>()
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .setInputData(
                    Data.Builder()
                        .putString(KEY_ID, treat.id)
                        .putInt(KEY_WEEKDAY, treat.weekday)
                        .putString(KEY_TITLE, treat.title)
                        .putString(KEY_BODY, treat.body)
                        .putString(KEY_CHANNEL, channelName)
                        .build(),
                )
                .addTag(TAG)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(uniqueName(treat.id), policy, request)
        }
    }
}
