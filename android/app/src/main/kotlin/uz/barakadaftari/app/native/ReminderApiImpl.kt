package uz.barakadaftari.app.native

import android.Manifest
import android.content.Context
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationManagerCompat
import androidx.fragment.app.FragmentActivity
import java.util.concurrent.Executors

class ReminderApiImpl(
    private val context: Context,
    private val activityProvider: () -> FragmentActivity?,
) : ReminderApi {
    private val background = Executors.newSingleThreadExecutor()

    override fun sync(reminders: List<ObligationReminder>, channelName: String) {
        val list = reminders.map { Reminder(it.id, it.dayOfMonth.toInt(), it.title, it.body) }
        // WorkManager so'rovlari (getWorkInfos().get()) asosiy oqimni bloklamasin.
        background.execute { ReminderScheduler.sync(context, list, channelName) }
    }

    override fun scheduleWeekly(title: String, body: String, channelName: String) {
        background.execute {
            WeeklyChapterWorker.schedule(
                context,
                title,
                body,
                channelName,
                androidx.work.ExistingWorkPolicy.REPLACE,
            )
        }
    }

    override fun syncTreats(treats: List<TreatReminder>, channelName: String) {
        val list = treats.map {
            TreatReminderWorker.Treat(it.id, it.weekday.toInt(), it.title, it.body)
        }
        background.execute { TreatReminderWorker.sync(context, list, channelName) }
    }

    override fun scheduleIncomeReminder(
        kind: IncomeReminderKind,
        dayOfMonth: Long,
        title: String,
        body: String,
        channelName: String,
    ) {
        background.execute {
            IncomeReminderWorker.schedule(
                context,
                kind,
                dayOfMonth.toInt().coerceIn(1, 31),
                title,
                body,
                channelName,
                androidx.work.ExistingWorkPolicy.REPLACE,
            )
        }
    }

    override fun scheduleAgreementRenewal(
        id: String,
        year: Long,
        month: Long,
        day: Long,
        title: String,
        body: String,
        channelName: String,
    ) {
        background.execute {
            AgreementRenewalWorker.schedule(
                context,
                id,
                year.toInt(),
                month.toInt(),
                day.toInt(),
                title,
                body,
                channelName,
            )
        }
    }

    override fun cancelAgreementRenewal(id: String) {
        background.execute { AgreementRenewalWorker.cancel(context, id) }
    }

    override fun areNotificationsEnabled(): Boolean =
        NotificationManagerCompat.from(context).areNotificationsEnabled()

    override fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val activity = activityProvider() ?: return
        ActivityCompat.requestPermissions(
            activity,
            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
            REQUEST_CODE,
        )
    }

    companion object {
        const val REQUEST_CODE = 4401
    }
}
