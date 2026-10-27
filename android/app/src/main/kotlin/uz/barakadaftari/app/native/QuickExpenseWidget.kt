package uz.barakadaftari.app.native

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.action.ActionParameters
import androidx.glance.action.actionParametersOf
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.state.updateAppWidgetState
import androidx.glance.currentState
import androidx.glance.state.PreferencesGlanceStateDefinition
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.color.ColorProvider
import androidx.glance.layout.Column
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Bosh ekran vidjeti (SPEC 2B.1): shablon tugmalari, bir bosishda yozish.
 * Ilova qulfli bo'lsa summalar ko'rsatilmaydi — faqat nomlar.
 */
class QuickExpenseWidget : GlanceAppWidget() {
    // Holatda faqat versiya: u o'zgarsa kompozitsiya ma'lumotni qayta o'qiydi
    // (shifrlangan ombordan). `update()` ishlayotgan sessiyada
    // `provideGlance` ni qayta chaqirmaydi.
    override val stateDefinition = PreferencesGlanceStateDefinition

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val store = WidgetStore(context)
        provideContent {
            val version = currentState(VERSION) ?: 0L
            val snapshot = remember(version) {
                Triple(store.state(), store.showAmounts(System.currentTimeMillis()), store.pendingCount())
            }
            Content(snapshot.first, snapshot.second, snapshot.third)
        }
    }

    @Composable
    private fun Content(state: WidgetStore.State, showAmounts: Boolean, pending: Int) {
        // «Daftar» ranglari (kun / tun).
        val paper = ColorProvider(Color(0xFFF8F3E6), Color(0xFF26241F))
        val ink = ColorProvider(Color(0xFF2B2A26), Color(0xFFEDE6D6))
        val muted = ColorProvider(Color(0xFF6B655A), Color(0xFFB5AD9C))
        val chip = ColorProvider(Color(0xFFE6EFE4), Color(0xFF34402F))
        Column(
            modifier = GlanceModifier.fillMaxSize().background(paper).cornerRadius(16.dp).padding(12.dp),
        ) {
            Text(
                text = if (pending > 0) "${state.title} · ✓$pending" else state.title,
                style = TextStyle(color = ink, fontWeight = FontWeight.Bold, fontSize = 14.sp),
            )
            Spacer(GlanceModifier.height(6.dp))
            if (state.templates.isEmpty()) {
                Text(state.empty, style = TextStyle(color = muted, fontSize = 12.sp))
            }
            state.templates.take(MAX_BUTTONS).forEach { t ->
                Text(
                    text = if (showAmounts) "${t.title} · ${t.amountLabel}" else t.title,
                    style = TextStyle(color = ink, fontSize = 14.sp),
                    modifier = GlanceModifier
                        .fillMaxWidth()
                        .background(chip)
                        .cornerRadius(10.dp)
                        .padding(horizontal = 10.dp, vertical = 8.dp)
                        .clickable(
                            actionRunCallback<RecordTemplateAction>(actionParametersOf(TEMPLATE_ID to t.id)),
                        ),
                )
                Spacer(GlanceModifier.height(4.dp))
            }
            if (!showAmounts && state.templates.isNotEmpty()) {
                Text(state.locked, style = TextStyle(color = muted, fontSize = 11.sp))
            }
        }
    }

    companion object {
        const val MAX_BUTTONS = 4
        val TEMPLATE_ID = ActionParameters.Key<String>("templateId")
        private val VERSION = longPreferencesKey("version")

        /** Barcha vidjet nusxalarini qayta chizish (oqimdan qat'i nazar). */
        fun refresh(context: Context) {
            CoroutineScope(Dispatchers.Default).launch { runCatching { bumpAll(context) } }
        }

        suspend fun bumpAll(context: Context) {
            GlanceAppWidgetManager(context).getGlanceIds(QuickExpenseWidget::class.java)
                .forEach { bump(context, it) }
        }

        suspend fun bump(context: Context, id: GlanceId) {
            updateAppWidgetState(context, id) { it[VERSION] = System.nanoTime() }
            QuickExpenseWidget().update(context, id)
        }
    }
}

/** Tugma bosildi: yozuv shifrlangan navbatga tushadi; ilova ochilganda yoziladi. */
class RecordTemplateAction : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val id = parameters[QuickExpenseWidget.TEMPLATE_ID] ?: return
        WidgetStore(context).addPending(id, System.currentTimeMillis())
        QuickExpenseWidget.bump(context, glanceId)
    }
}

class QuickExpenseWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = QuickExpenseWidget()
}
