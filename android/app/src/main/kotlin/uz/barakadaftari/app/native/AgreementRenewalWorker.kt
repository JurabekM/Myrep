package uz.barakadaftari.app.native

import android.content.Context
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.time.Duration
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZonedDateTime
import java.util.concurrent.TimeUnit

/**
 * Kelishuvni yangilash eslatmasi (SPEC 6-qonun, Vazifa 14A): yangilash
 * sanasidan 30 kun oldin, 09:00 (Asia/Tashkent). Bir martalik ish — WorkManager
 * uni qurilma qayta yoqilgandan keyin ham saqlaydi. Matnlar Dart'da (ARB).
 */
class AgreementRenewalWorker(context: Context, params: WorkerParameters) :
    Worker(context, params) {

    override fun doWork(): Result {
        val id = inputData.getString(KEY_ID).orEmpty()
        if (id.isEmpty()) return Result.failure()
        val title = inputData.getString(KEY_TITLE).orEmpty()
        val body = inputData.getString(KEY_BODY).orEmpty()
        val channel = inputData.getString(KEY_CHANNEL).orEmpty()
        ReminderScheduler.notify(applicationContext, "renewal:$id", title, body, channel)
        return Result.success()
    }

    companion object {
        private const val TAG = "agreement_renewal"
        private const val KEY_ID = "id"
        private const val KEY_TITLE = "title"
        private const val KEY_BODY = "body"
        private const val KEY_CHANNEL = "channel"

        fun uniqueName(id: String) = "renewal:$id"

        /** Eslatmani [year]-[month]-[day] kuni 09:00 ga rejalashtiradi (idempotent). */
        fun schedule(
            context: Context,
            id: String,
            year: Int,
            month: Int,
            day: Int,
            title: String,
            body: String,
            channel: String,
        ) {
            val zone = ReminderSchedule.ZONE
            val now = ZonedDateTime.now(zone)
            val at = ZonedDateTime.of(LocalDate.of(year, month, day), LocalTime.of(9, 0), zone)
            val delay = Duration.between(now, at).toMillis().coerceAtLeast(0L)
            val request = OneTimeWorkRequestBuilder<AgreementRenewalWorker>()
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .setInputData(
                    Data.Builder()
                        .putString(KEY_ID, id)
                        .putString(KEY_TITLE, title)
                        .putString(KEY_BODY, body)
                        .putString(KEY_CHANNEL, channel)
                        .build(),
                )
                .addTag(TAG)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork(uniqueName(id), ExistingWorkPolicy.REPLACE, request)
        }

        fun cancel(context: Context, id: String) {
            WorkManager.getInstance(context).cancelUniqueWork(uniqueName(id))
        }
    }
}
