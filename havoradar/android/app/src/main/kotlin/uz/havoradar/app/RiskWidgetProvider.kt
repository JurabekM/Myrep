package uz.havoradar.app

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
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Snapshot
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.roundToInt

/** Bosh ekran vidjeti: asosiy joy uchun bugungi xavf balli, darajasi va issiqlik/havo ko'rsatkichlari. */
class RiskWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(
        context: Context,
        manager: AppWidgetManager,
        ids: IntArray,
    ) {
        val pending = goAsync()
        CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
            try {
                render(context, manager, ids, Repository.get(context).current())
            } catch (_: Exception) {
                // Vidjet xatosi butun ilova jarayonini to'xtatmasligi kerak (masalan, holat fayli o'qilmadi).
                render(context, manager, ids, null)
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
            val main = snapshot?.main
            val today = main?.today
            val score = today?.personalScore
            if (snapshot != null && main != null && score != null) {
                val level = RiskLevel.of(score)
                views.setTextViewText(R.id.widget_score, score.toString())
                views.setTextColor(R.id.widget_score, ContextCompat.getColor(context, Notifier.levelColor(level)))
                views.setTextViewText(R.id.widget_level, level.uz)
                views.setTextViewText(R.id.widget_place, main.place.name)
                val parts =
                    listOfNotNull(
                        today.feelsMax?.let { "Issiqlik ${it.roundToInt()}°C gacha" },
                        today.air?.pm25Mean?.let { "PM2.5 ${it.roundToInt()} µg/m³" },
                        today.uvMax?.let { "UV ${it.roundToInt()}" },
                    )
                views.setTextViewText(R.id.widget_top, parts.joinToString(" · "))
                views.setTextViewText(
                    R.id.widget_updated,
                    "Yangilangan: " + timeFmt.format(snapshot.generatedAt.atZone(ZoneId.systemDefault())),
                )
            }
            manager.updateAppWidget(ids, views)
        }
    }
}
