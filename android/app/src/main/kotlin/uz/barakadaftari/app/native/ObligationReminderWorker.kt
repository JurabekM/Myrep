package uz.barakadaftari.app.native

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.time.Duration
import java.time.LocalDate
import java.time.ZonedDateTime
import java.util.concurrent.TimeUnit

/**
 * Majburiyat eslatmasi. Bildirishnomani ko'rsatadi va keyingi oyni o'zi
 * rejalashtiradi — ilova ochilmasa ham eslatmalar davom etadi. WorkManager
 * ishlarni qayta yuklanishdan keyin ham saqlaydi.
 */
class ObligationReminderWorker(context: Context, params: WorkerParameters) :
    Worker(context, params) {

    override fun doWork(): Result {
        val id = inputData.getString(KEY_ID) ?: return Result.failure()
        val day = inputData.getInt(KEY_DAY, 0)
        val title = inputData.getString(KEY_TITLE).orEmpty()
        val body = inputData.getString(KEY_BODY).orEmpty()
        val channel = inputData.getString(KEY_CHANNEL).orEmpty()
        val due = inputData.getString(KEY_DUE)?.let(LocalDate::parse)

        val reminder = Reminder(id, day, title, body)
        val shown = ReminderScheduler.notify(applicationContext, id, title, body, channel)
        val today = LocalDate.now(ReminderSchedule.ZONE)
        if (!shown && due != null && !due.isBefore(today)) {
            // Ruxsat yo'q (masalan, hali so'ralmagan) — eslatmani yo'qotmaymiz:
            // to'lov kunigacha soatiga bir qayta urinamiz.
            ReminderScheduler.enqueue(
                applicationContext,
                reminder,
                channel,
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                notBefore = ZonedDateTime.now(ReminderSchedule.ZONE).plusHours(1),
            )
            return Result.success()
        }
        if (due != null) ReminderScheduler.markNotified(applicationContext, id, due)
        ReminderScheduler.enqueue(
            applicationContext,
            reminder,
            channel,
            ExistingWorkPolicy.APPEND_OR_REPLACE,
        )
        return Result.success()
    }

    companion object {
        const val KEY_ID = "id"
        const val KEY_DAY = "day"
        const val KEY_TITLE = "title"
        const val KEY_BODY = "body"
        const val KEY_CHANNEL = "channel"
        const val KEY_DUE = "due"
    }
}

data class Reminder(val id: String, val dayOfMonth: Int, val title: String, val body: String)

object ReminderScheduler {
    const val TAG = "obligation_reminder"
    const val CHANNEL_ID = "obligations"
    private const val PREFS = "reminders"
    private const val KEY_SCHEDULED = "__scheduled"

    fun uniqueName(id: String) = "obligation:$id"

    /** Ro'yxatni aynan shu holatga keltiradi: yo'qlari bekor qilinadi. */
    fun sync(context: Context, reminders: List<Reminder>, channelName: String) {
        val wm = WorkManager.getInstance(context)
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val keep = reminders.map { it.id }.toSet()
        // Avval rejalashtirilgan, endi ro'yxatda yo'q eslatmalar bekor qilinadi.
        prefs.getStringSet(KEY_SCHEDULED, emptySet()).orEmpty()
            .filter { it !in keep }
            .forEach { wm.cancelUniqueWork(uniqueName(it)) }
        prefs.edit().putStringSet(KEY_SCHEDULED, keep).apply()
        reminders.forEach { enqueue(context, it, channelName, ExistingWorkPolicy.REPLACE) }
    }

    fun enqueue(
        context: Context,
        reminder: Reminder,
        channelName: String,
        policy: ExistingWorkPolicy,
        notBefore: ZonedDateTime? = null,
    ) {
        val now = ZonedDateTime.now(ReminderSchedule.ZONE)
        val trigger = ReminderSchedule.next(now, reminder.dayOfMonth, lastNotified(context, reminder.id))
        val at = if (notBefore != null && notBefore.isAfter(trigger.at)) notBefore else trigger.at
        val delay = Duration.between(now, at).toMillis().coerceAtLeast(0)
        val data = Data.Builder()
            .putString(ObligationReminderWorker.KEY_ID, reminder.id)
            .putInt(ObligationReminderWorker.KEY_DAY, reminder.dayOfMonth)
            .putString(ObligationReminderWorker.KEY_TITLE, reminder.title)
            .putString(ObligationReminderWorker.KEY_BODY, reminder.body)
            .putString(ObligationReminderWorker.KEY_CHANNEL, channelName)
            .putString(ObligationReminderWorker.KEY_DUE, trigger.due.toString())
            .build()
        val request = OneTimeWorkRequestBuilder<ObligationReminderWorker>()
            .setInitialDelay(delay, TimeUnit.MILLISECONDS)
            .setInputData(data)
            .addTag(TAG)
            .addTag(uniqueName(reminder.id))
            .build()
        WorkManager.getInstance(context)
            .enqueueUniqueWork(uniqueName(reminder.id), policy, request)
    }

    fun markNotified(context: Context, id: String, due: LocalDate) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("due:$id", due.toString()).apply()
    }

    private fun lastNotified(context: Context, id: String): LocalDate? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString("due:$id", null)?.let(LocalDate::parse)

    /** Ko'rsatildimi (ruxsat yo'q yoki o'chirilgan bo'lsa — `false`). */
    fun notify(context: Context, id: String, title: String, body: String, channelName: String): Boolean {
        ensureChannel(context, channelName)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return false
        }
        if (!NotificationManagerCompat.from(context).areNotificationsEnabled()) return false
        val launch = context.packageManager.getLaunchIntentForPackage(context.packageName)
            ?: Intent()
        val pending = PendingIntent.getActivity(
            context,
            id.hashCode(),
            launch,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_popup_reminder)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(pending)
            // Qulflangan ekranda matn yashiriladi (moliyaviy ma'lumot).
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .build()
        NotificationManagerCompat.from(context).notify(id.hashCode(), notification)
        return true
    }

    fun ensureChannel(context: Context, name: String) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, name.ifBlank { "Baraka" }, NotificationManager.IMPORTANCE_DEFAULT),
        )
    }
}
