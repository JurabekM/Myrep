package uz.barakadaftari.app.native

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

class WidgetApiImpl(private val context: Context) : WidgetApi {
    private val store = WidgetStore(context)

    override fun setTemplates(templates: List<WidgetTemplate>, texts: WidgetTexts) {
        store.saveState(
            WidgetStore.State(
                templates = templates.map { WidgetStore.Template(it.id, it.title, it.amountLabel) },
                title = texts.title,
                locked = texts.locked,
                empty = texts.empty,
            ),
        )
        QuickExpenseWidget.refresh(context)
    }

    override fun setVisibleUntil(epochMillis: Long) {
        applyVisibleUntil(context, epochMillis)
    }

    override fun takePending(): List<PendingWidgetExpense> {
        val list = store.takePending().map { (id, at) ->
            PendingWidgetExpense(templateId = id, recordedAtMillis = at)
        }
        if (list.isNotEmpty()) QuickExpenseWidget.refresh(context)
        return list
    }

    companion object {
        /** 0 — darhol yashirish (ilova qulflangan / qayta ishga tushgan). */
        fun applyVisibleUntil(context: Context, epochMillis: Long) {
            WidgetStore(context).visibleUntil = epochMillis
            QuickExpenseWidget.refresh(context)
            val wm = WorkManager.getInstance(context)
            val delay = epochMillis - System.currentTimeMillis()
            if (delay > 0 && epochMillis != Long.MAX_VALUE) {
                wm.enqueueUniqueWork(
                    WidgetHideWorker.UNIQUE,
                    ExistingWorkPolicy.REPLACE,
                    OneTimeWorkRequestBuilder<WidgetHideWorker>()
                        .setInitialDelay(delay + 1000, TimeUnit.MILLISECONDS)
                        .build(),
                )
            } else {
                wm.cancelUniqueWork(WidgetHideWorker.UNIQUE)
            }
        }
    }
}

/** Qulf vaqti tugaganda vidjetdagi summalarni yashiradi. */
class WidgetHideWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        runCatching { QuickExpenseWidget.bumpAll(applicationContext) }
        return Result.success()
    }

    companion object {
        const val UNIQUE = "widget_hide"
    }
}
