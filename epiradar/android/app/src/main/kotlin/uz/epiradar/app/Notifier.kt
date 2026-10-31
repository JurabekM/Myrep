package uz.epiradar.app

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
import uz.epiradar.engine.alert.AlertNotification
import uz.epiradar.engine.model.ThreatLevel

/** Push-bildirishnomalar: Xavf/Favqulodda — yuqori ustuvorlikdagi alohida kanal (zilzila ogohlantirishi kabi). */
object Notifier {
    const val CHANNEL_CRITICAL = "alerts_critical"
    const val CHANNEL_ALERTS = "alerts"
    const val EXTRA_EVENT_ID = "uz.epiradar.EVENT_ID"

    fun createChannels(context: Context) {
        val nm = context.getSystemService(NotificationManager::class.java)
        val critical =
            NotificationChannel(CHANNEL_CRITICAL, context.getString(R.string.channel_critical), NotificationManager.IMPORTANCE_HIGH).apply {
                description = context.getString(R.string.channel_critical_desc)
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 400, 200, 400, 200, 800)
                enableLights(true)
                lightColor = ContextCompat.getColor(context, R.color.danger)
            }
        val normal =
            NotificationChannel(CHANNEL_ALERTS, context.getString(R.string.channel_alerts), NotificationManager.IMPORTANCE_DEFAULT).apply {
                description = context.getString(R.string.channel_alerts_desc)
            }
        nm.createNotificationChannels(listOf(critical, normal))
    }

    fun canNotify(context: Context): Boolean =
        (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) &&
            NotificationManagerCompat.from(context).areNotificationsEnabled()

    fun show(
        context: Context,
        n: AlertNotification,
    ) {
        if (!canNotify(context)) return
        val open =
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra(EXTRA_EVENT_ID, n.eventId)
            }
        val pending = PendingIntent.getActivity(context, n.eventId.hashCode(), open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification =
            NotificationCompat
                .Builder(context, if (n.critical) CHANNEL_CRITICAL else CHANNEL_ALERTS)
                .setSmallIcon(R.drawable.ic_stat_radar)
                .setColor(ContextCompat.getColor(context, levelColor(n.level)))
                .setContentTitle(n.title)
                .setContentText(n.body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(n.body))
                .setCategory(if (n.critical) NotificationCompat.CATEGORY_ALARM else NotificationCompat.CATEGORY_RECOMMENDATION)
                .setPriority(if (n.critical) NotificationCompat.PRIORITY_HIGH else NotificationCompat.PRIORITY_DEFAULT)
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                .setAutoCancel(true)
                .setContentIntent(pending)
                .build()
        try {
            NotificationManagerCompat.from(context).notify(n.eventId.hashCode(), notification)
        } catch (_: SecurityException) {
            // Ruxsat shu orada bekor qilingan bo'lishi mumkin.
        }
    }

    fun levelColor(level: ThreatLevel): Int =
        when (level) {
            ThreatLevel.CALM -> R.color.level_calm
            ThreatLevel.WATCH -> R.color.level_watch
            ThreatLevel.ADVISORY -> R.color.level_advisory
            ThreatLevel.WARNING -> R.color.level_warning
            ThreatLevel.EMERGENCY -> R.color.level_emergency
        }
}
