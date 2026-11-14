package uz.rostor.rostor2.call

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import uz.rostor.rostor2.MainActivity
import uz.rostor.rostor2.R
import uz.rostor.rostor2.db.DbLoader

/**
 * Qo'ng'iroq Qalqonining Android qismi: baza indeksi, sozlamalar, tarix va ogohlantirish.
 * Hamma narsa qurilmada: raqamlar hech qayerga yuborilmaydi, tarixda faqat belgilangan
 * qo'ng'iroqlar saqlanadi (oddiy noma'lum raqamlar yozilmaydi).
 */
object CallShield {
    const val ACTION_OPEN = "uz.rostor.rostor2.OPEN_CALLS"
    private const val CHANNEL = "call_shield"
    private const val HISTORY_MAX = 50

    @Volatile private var index: PhoneIndex? = null
    @Volatile var dbError: String? = null
        private set

    fun index(ctx: Context): PhoneIndex {
        index?.let { return it }
        synchronized(this) {
            index?.let { return it }
            val r = DbLoader.load(ctx)
            val idx = if (r.ok) PhoneIndex.fromPayload(r.payloadJson!!) else PhoneIndex.EMPTY
            dbError = r.error
            index = idx
            return idx
        }
    }

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(DbLoader.PREFS, Context.MODE_PRIVATE)

    private fun flag(ctx: Context, key: String, default: Boolean): Boolean =
        prefs(ctx).getString(key, null)?.let { it == "1" } ?: default

    fun policy(ctx: Context): CallPolicy {
        val blocked = prefs(ctx).getString("call_blocklist", null)?.let { s ->
            try {
                val a = JSONArray(s)
                (0 until a.length()).mapNotNull { PhoneNumbers.normalize(a.getString(it)) }.toSet()
            } catch (e: Exception) { emptySet() }
        } ?: emptySet()
        return CallPolicy(
            blockFlagged = flag(ctx, "call_block", true),
            silenceInternational = flag(ctx, "call_silence_intl", false),
            notifyOfficial = flag(ctx, "call_notify_official", true),
            userBlocked = blocked,
        )
    }

    fun screen(ctx: Context, raw: String?, hidden: Boolean, verification: Int): CallVerdict =
        PhoneRules.evaluate(raw, hidden, verification, index(ctx), policy(ctx))

    /** UI'dagi "raqamni tekshirish": qo'ng'iroq bilan bir xil qoidalar, faqat operator tasdig'isiz. */
    fun check(ctx: Context, raw: String): Map<String, Any?> {
        if (PhoneNumbers.normalize(raw) == null) return mapOf("error" to "Bu telefon raqamiga o'xshamaydi")
        return PhoneRules.evaluate(raw, false, PhoneRules.VERIFY_NONE, index(ctx), policy(ctx)).toMap()
    }

    /** Qo'ng'iroqqa javob berilgandan keyin: tarix va ogohlantirish. */
    fun after(ctx: Context, v: CallVerdict) {
        val policy = policy(ctx)
        if (v.severity != "ok") record(ctx, v)
        if (PhoneRules.shouldNotify(v, policy) || v.block) notify(ctx, v)
    }

    private fun record(ctx: Context, v: CallVerdict) {
        val p = prefs(ctx)
        synchronized(this) {
            val old = try { JSONArray(p.getString("call_history", "[]")) } catch (e: Exception) { JSONArray() }
            val top = v.top!!
            val entry = JSONObject()
                .put("t", System.currentTimeMillis())
                .put("number", v.normalized ?: JSONObject.NULL)
                .put("display", v.normalized?.let { PhoneNumbers.display(it) } ?: "Yashirin raqam")
                .put("severity", v.severity)
                .put("code", top.code)
                .put("title", top.title)
                .put("blocked", v.block)
                .put("silenced", v.silence)
            val out = JSONArray().put(entry)
            for (i in 0 until minOf(old.length(), HISTORY_MAX - 1)) out.put(old.get(i))
            p.edit().putString("call_history", out.toString()).apply()
        }
    }

    fun ensureChannel(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL) != null) return
        val ch = NotificationChannel(CHANNEL, "Qo'ng'iroq Qalqoni", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Kiruvchi qo'ng'iroq rasmiy, firibgar yoki xorijiy raqamdan bo'lsa ogohlantiradi"
            lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        }
        nm.createNotificationChannel(ch)
    }

    fun notificationsEnabled(ctx: Context): Boolean {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        if (!nm.areNotificationsEnabled()) return false
        if (Build.VERSION.SDK_INT >= 26) {
            val ch = nm.getNotificationChannel(CHANNEL)
            if (ch != null && ch.importance == NotificationManager.IMPORTANCE_NONE) return false
        }
        return true
    }

    /** Foydalanuvchi ogohlantirish qanday ko'rinishini va ruxsat ishlashini sinab ko'radi. */
    fun notifyTest(ctx: Context): Boolean {
        val f = CallFinding(
            "call.test", "medium", "Sinov ogohlantirishi",
            "Shubhali qo'ng'iroq kelganda ROSTOR-2 shunday ogohlantiradi: kim qo'ng'iroq qilayotgani va nima qilish kerakligi.",
        )
        notify(ctx, CallVerdict(null, listOf(f), block = false, silence = false, official = emptyList()), "ROSTOR-2: sinov ogohlantirishi")
        return notificationsEnabled(ctx)
    }

    fun notify(ctx: Context, v: CallVerdict, titleOverride: String? = null) {
        ensureChannel(ctx)
        val top = v.top ?: return
        val who = v.normalized?.let { PhoneNumbers.display(it) } ?: "Yashirin raqam"
        val title = titleOverride ?: when {
            v.block -> "Bloklandi: $who"
            v.severity == "info" -> "${top.title}: $who"
            else -> "Diqqat — ${top.title.replaceFirstChar { it.lowercase() }}: $who"
        }
        val open = PendingIntent.getActivity(
            ctx, 0,
            Intent(ctx, MainActivity::class.java).setAction(ACTION_OPEN).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val color = when (v.severity) {
            "critical" -> 0xFFE5484D.toInt()
            "high" -> 0xFFF76B15.toInt()
            "medium" -> 0xFFFFC53D.toInt()
            "info" -> 0xFF4FD1C5.toInt()
            else -> 0xFF8DA2C0.toInt()
        }
        val publicVersion = Notification.Builder(ctx, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle("ROSTOR-2: qo'ng'iroq haqida ogohlantirish")
            .setColor(color)
            .build()
        val n = Notification.Builder(ctx, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setColor(color)
            .setContentTitle(title)
            .setContentText(top.explain)
            .setStyle(Notification.BigTextStyle().bigText(top.explain))
            .setCategory(if (v.severity == "info") Notification.CATEGORY_STATUS else Notification.CATEGORY_ALARM)
            .setPublicVersion(publicVersion)
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        val nm = ctx.getSystemService(NotificationManager::class.java)
        try {
            nm.notify(7000 + ((v.normalized ?: "hidden").hashCode() and 0xFFF), n)
        } catch (e: SecurityException) {
            // POST_NOTIFICATIONS berilmagan: qaror (bloklash) baribir qo'llangan, tarix yozilgan.
        }
    }
}
