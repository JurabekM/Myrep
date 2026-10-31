package uz.epiradar.app

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import uz.epiradar.engine.model.Snapshot
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** Bosh ekran vidjeti: mamlakatingiz uchun xavf balli, darajasi va eng muhim hodisa. */
class RiskWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(
        context: Context,
        manager: AppWidgetManager,
        ids: IntArray,
    ) {
        val pending = goAsync()
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            try {
                val snapshot = (context.applicationContext as EpiRadarApp).repository.current()
                render(context, manager, ids, snapshot)
            } finally {
                pending.finish()
            }
        }
    }

    companion object {
        private val timeFmt = DateTimeFormatter.ofPattern("dd.MM HH:mm")

        fun update(
            context: Context,
            snapshot: Snapshot,
        ) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, RiskWidgetProvider::class.java))
            if (ids.isNotEmpty()) render(context, manager, ids, snapshot)
        }

        private fun render(
            context: Context,
            manager: AppWidgetManager,
            ids: IntArray,
            snapshot: Snapshot?,
        ) {
            val views = RemoteViews(context.packageName, R.layout.widget_risk)
            val open =
                PendingIntent.getActivity(
                    context,
                    0,
                    Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                    PendingIntent.FLAG_IMMUTABLE,
                )
            views.setOnClickPendingIntent(R.id.widget_root, open)
            if (snapshot != null) {
                val level = snapshot.personalLevel
                val repo = (context.applicationContext as EpiRadarApp).repository
                views.setTextViewText(R.id.widget_score, snapshot.personalScore.toString())
                views.setTextColor(R.id.widget_score, ContextCompat.getColor(context, Notifier.levelColor(level)))
                views.setTextViewText(R.id.widget_level, level.uz)
                views.setTextViewText(R.id.widget_country, repo.engine.countries.nameUz(snapshot.country))
                views.setTextViewText(R.id.widget_top, snapshot.events.firstOrNull()?.title ?: "Faol tahdid aniqlanmadi")
                views.setTextViewText(
                    R.id.widget_updated,
                    "Yangilangan: " + timeFmt.format(snapshot.generatedAt.atZone(ZoneId.systemDefault())),
                )
            }
            manager.updateAppWidget(ids, views)
        }
    }
}
