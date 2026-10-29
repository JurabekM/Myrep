package uz.mpay.wallet.app

import android.Manifest
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import uz.mpay.core.CardChange
import uz.mpay.core.Txn
import java.util.concurrent.TimeUnit

/** Ilova: bildirishnoma kanallari va davriy sinxronlash. */
class MpayApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifier.channels(this)
        if (AppPrefs(this).onboarded) Sync.schedule(this)
    }
}

/**
 * Davriy sinxronlash (WorkManager, tarmoq bo'lganda, ~15 daqiqa): kartalar holati server bilan, kam
 * qolgan LUK'lar to'ldiriladi, yangi tranzaksiyalar va karta o'zgarishlari — bildirishnoma.
 */
object Sync {
    private const val PERIODIC = "mpay-sync"
    private const val NOW = "mpay-sync-now"
    private const val TAG = "MpaySync"

    fun schedule(context: Context) {
        val req = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.KEEP, req)
    }

    /** Darhol bir marta (masalan, ilova ochilganda). */
    fun now(context: Context) {
        WorkManager.getInstance(context).enqueue(OneTimeWorkRequestBuilder<SyncWorker>().build())
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(PERIODIC)
    }

    /**
     * Bir sinxronlash: (o'zgarishlar, yangi tranzaksiyalar). Activity ham chaqiradi (yangilash tugmasi) —
     * natija bir xil, bildirishnoma faqat fonda.
     */
    fun run(context: Context): Pair<List<CardChange>, List<Pair<String, Txn>>> {
        val prefs = AppPrefs(context)
        val changes = WalletSetup.call(context) { it.syncCards() }
        val w = WalletSetup.wallet(context)
        runCatching { WalletSetup.call(context) { it.replenishLow() } }.onFailure { Log.w(TAG, "to'ldirish: ${it.javaClass.simpleName}") }
        val fresh = mutableListOf<Pair<String, Txn>>()
        for (card in w.cards().filter { it.onDevice }) {
            val page = runCatching { WalletSetup.call(context) { it.transactions(card.tokenId, limit = 20) } }.getOrNull() ?: continue
            val r = TxnWatcher.diff(page.transactions, prefs.txnMarker(card.tokenId))
            prefs.setTxnMarker(card.tokenId, r.marker)
            r.fresh.forEach { fresh += card.dpanMasked to it }
        }
        return changes to fresh
    }
}

class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val prefs = AppPrefs(applicationContext)
        if (!prefs.onboarded) return Result.success()
        return try {
            val (changes, fresh) = Sync.run(applicationContext)
            if (prefs.notifications) Notifier.show(applicationContext, changes, fresh)
            Result.success()
        } catch (e: Exception) {
            // Faqat sinf nomi — xabarda ma'lumot bo'lishi mumkin emas, lekin ehtiyot.
            Log.w("MpaySync", "sinxronlash: ${e.javaClass.simpleName}")
            Result.retry()
        }
    }
}

/** Mahalliy bildirishnomalar (matnlar tanlangan tilda; summa va maskalangan PAN — sir emas). */
object Notifier {
    const val CH_TXN = "txn"
    const val CH_CARD = "card"

    fun channels(context: Context) {
        val c = AppPrefs.localized(context)
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CH_TXN, c.getString(R.string.channel_txn), NotificationManager.IMPORTANCE_DEFAULT))
        nm.createNotificationChannel(NotificationChannel(CH_CARD, c.getString(R.string.channel_card), NotificationManager.IMPORTANCE_HIGH))
    }

    fun allowed(context: Context): Boolean =
        (Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) &&
            NotificationManagerCompat.from(context).areNotificationsEnabled()

    @Suppress("MissingPermission") // allowed() tekshiradi
    fun show(context: Context, changes: List<CardChange>, fresh: List<Pair<String, Txn>>) {
        if (!allowed(context)) return
        val c = AppPrefs.localized(context)
        val lang = AppPrefs(context).lang
        val nm = NotificationManagerCompat.from(context)
        val open = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        fun post(channel: String, id: Int, title: String, text: String) {
            val n = NotificationCompat.Builder(context, channel)
                .setSmallIcon(R.drawable.ic_stat_mpay)
                .setContentTitle(title)
                .setContentText(text)
                .setStyle(NotificationCompat.BigTextStyle().bigText(text))
                .setContentIntent(open)
                .setAutoCancel(true)
                // Qulflangan ekranda summa va karta ko'rinmaydi.
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
                .build()
            nm.notify(id, n)
        }
        changes.forEach { ch ->
            val text = when (ch) {
                is CardChange.Removed -> c.getString(R.string.notify_card_removed, Format.last4(ch.dpanMasked))
                is CardChange.State -> when {
                    ch.to == "SUSPENDED" && ch.by == "BANK" -> c.getString(R.string.notify_card_suspended_bank)
                    ch.to == "SUSPENDED" -> c.getString(R.string.notify_card_suspended)
                    ch.to == "ACTIVE" -> c.getString(R.string.notify_card_resumed)
                    else -> c.getString(R.string.notify_card_state, ch.to)
                }
            }
            post(CH_CARD, ch.tokenId.hashCode(), c.getString(R.string.notify_card_title), text)
        }
        fresh.forEach { (dpan, t) ->
            val amount = Format.money(t.amountMinor, t.currency, lang)
            val (title, text) = when (t.status) {
                "APPROVED" -> c.getString(R.string.notify_paid_title) to c.getString(R.string.notify_paid, amount, t.merchantId, Format.last4(dpan))
                "REVERSED" -> c.getString(R.string.notify_reversed_title) to c.getString(R.string.notify_reversed, amount, t.merchantId)
                else -> c.getString(R.string.notify_declined_title) to c.getString(R.string.notify_declined, amount, t.merchantId, t.responseCode)
            }
            post(CH_TXN, t.id.hashCode(), title, text)
        }
    }
}
