package uz.qarzsiz.app.reminders

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import uz.qarzsiz.app.MainActivity
import uz.qarzsiz.app.R
import uz.qarzsiz.app.data.AppState
import uz.qarzsiz.app.data.LoadResult
import uz.qarzsiz.app.data.ReminderSettings
import uz.qarzsiz.app.data.Stores
import uz.qarzsiz.core.Reminders
import uz.qarzsiz.core.Translit
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

/**
 * Kunlik tekshiruv signali. Internet va WorkManager'siz: `AlarmManager` (aniq bo'lmagan, Doze'da ham
 * ishlaydigan) bitta signal qo'yadi; signal kelganda keyingisi qo'yiladi. Qayta yuklanish, vaqt yoki
 * mintaqa o'zgarganda signal qaytadan qo'yiladi.
 */
object ReminderScheduler {
    private const val REQUEST_CODE = 4501
    const val ACTION_CHECK = "uz.qarzsiz.app.action.CHECK_REMINDERS"

    /** Keyingi tekshiruv vaqti: bugun `hour`:00 o'tmagan bo'lsa — bugun, aks holda ertaga. */
    fun nextTrigger(now: LocalDateTime, hour: Int): LocalDateTime {
        val today = now.toLocalDate().atTime(hour.coerceIn(0, 23), 0)
        return if (now.isBefore(today)) today else today.plusDays(1)
    }

    private fun pending(context: Context, flags: Int): PendingIntent? = PendingIntent.getBroadcast(
        context,
        REQUEST_CODE,
        Intent(context, ReminderReceiver::class.java).setAction(ACTION_CHECK),
        flags or PendingIntent.FLAG_IMMUTABLE,
    )

    fun apply(context: Context, settings: ReminderSettings) {
        if (settings.enabled) schedule(context, settings.hour) else cancel(context)
    }

    fun schedule(context: Context, hour: Int) {
        val am = context.getSystemService(AlarmManager::class.java) ?: return
        val at = nextTrigger(LocalDateTime.now(), hour).atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
        val pi = pending(context, PendingIntent.FLAG_UPDATE_CURRENT) ?: return
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
    }

    fun cancel(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java) ?: return
        pending(context, PendingIntent.FLAG_NO_CREATE)?.let {
            am.cancel(it)
            it.cancel()
        }
    }
}

object ReminderNotifier {
    const val CHANNEL_ID = "payment_reminders"
    private const val NOTIFICATION_ID = 4502

    fun canPost(context: Context): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED

    private fun ensureChannel(context: Context, state: AppState) {
        val nm = context.getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            Translit.apply("To'lov eslatmalari", state.script),
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply { description = Translit.apply("Qarz to'lov kuni yaqinlashganda", state.script) }
        nm.createNotificationChannel(channel)
    }

    /**
     * Bugungi eslatmalarni chiqaradi. `force` — sozlamadagi «Sinab ko'rish»: eslatma bo'lmasa ham xabar beradi.
     * @return chiqarilgan eslatmalar soni.
     */
    fun postDue(context: Context, state: AppState, today: LocalDate, force: Boolean = false): Int {
        if (!canPost(context)) return 0
        val payments = state.payments.mapNotNull { p ->
            runCatching { p.debtId to LocalDate.parse(p.date) }.getOrNull()
        }
        val items = Reminders.due(state.debts, payments, today, state.reminders.daysBefore)
        val (title, body) = when {
            items.isNotEmpty() -> Reminders.message(items)
            force -> "Eslatmalar ishlayapti" to "Hozircha yaqin kunlarda to'lov yo'q."
            else -> return 0
        }
        ensureChannel(context, state)
        val tr = { s: String -> Translit.apply(s, state.script) }
        val open = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        // Qulflangan ekranda qarz tafsiloti ko'rinmaydi — faqat umumiy yozuv.
        val publicVersion = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(tr("Qarzsiz"))
            .setContentText(tr("To'lov eslatmasi"))
            .build()
        val n = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setColor(0xFFD97757.toInt())
            .setContentTitle(tr(title))
            .setContentText(tr(body).lineSequence().first())
            .setStyle(NotificationCompat.BigTextStyle().bigText(tr(body)))
            .setContentIntent(open)
            .setAutoCancel(true)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setPublicVersion(publicVersion)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .build()
        @Suppress("MissingPermission") // canPost() yuqorida tekshirildi
        NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, n)
        return items.size.coerceAtLeast(if (force) 1 else 0)
    }
}

/** Kunlik signal va tizim hodisalari (qayta yuklanish, vaqt/mintaqa o'zgarishi, yangilanish). */
class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        Thread {
            try {
                handle(context.applicationContext, intent.action)
            } finally {
                pending.finish()
            }
        }.start()
    }

    companion object {
        fun handle(context: Context, action: String?) {
            val state = (Stores.factory(context).load() as? LoadResult.Ok)?.state ?: return
            if (!state.reminders.enabled) {
                ReminderScheduler.cancel(context)
                return
            }
            if (action == ReminderScheduler.ACTION_CHECK) {
                ReminderNotifier.postDue(context, state, LocalDate.now())
            }
            // Har holda keyingi kunga signal qo'yiladi.
            ReminderScheduler.schedule(context, state.reminders.hour)
        }
    }
}
