package uz.sectorverify.feature.survey.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlin.math.roundToInt
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import uz.sectorverify.data.BufferedSampleWriter
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.feature.survey.R
import uz.sectorverify.feature.survey.SessionAnalysis
import uz.sectorverify.feature.survey.SurveyController
import uz.sectorverify.feature.survey.SurveyEngine
import uz.sectorverify.format.SvJson
import uz.sectorverify.location.GnssCollector
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.telephony.CellCollector
import uz.sectorverify.telephony.TrafficGenerator
import uz.sectorverify.ui.util.LocaleStore

/**
 * §7 SurveyForegroundService: "location" turi, partial WakeLock, namunalar soni va qamrov ko'rsatilgan doimiy
 * bildirishnoma. Ikkala oqim [BufferedSampleWriter] orqali o'tadi (1 s, bitta Room tranzaksiyasi).
 */
@AndroidEntryPoint
class SurveyForegroundService : LifecycleService() {
    @Inject lateinit var sessions: SessionRepository

    @Inject lateinit var settings: SettingsRepository

    @Inject lateinit var controller: SurveyController

    @Inject lateinit var analysis: SessionAnalysis

    private var engine: SurveyEngine? = null
    private var pipeline: Job? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var readyShown = false

    /** Darhol (korutinadan oldin) o'rnatiladi: takroriy START ikkinchi engine yaratmaydi. */
    private var activeSessionId: String? = null

    /** Engine hali tayyor bo'lmaganda kelgan STOP — engine ishga tushgach bajariladi. */
    private var stopRequested = false
    private var finishing = false

    /** Bildirishnomalar tizim tiliga emas, ilova tiliga amal qiladi. */
    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(LocaleStore.wrap(newBase))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ACTION_START -> intent.getStringExtra(EXTRA_SESSION)?.let(::begin)
            ACTION_STOP -> finish()
        }
        return START_NOT_STICKY
    }

    private fun begin(sessionId: String) {
        createChannels()
        try {
            // Har bir startForegroundService() chaqiruvidan keyin startForeground() majburiy — takroriy START uchun ham.
            ServiceCompat.startForeground(this, NOTIFICATION_ID, progressNotification(0, 0), ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } catch (expected: SecurityException) {
            // Joylashuv ruxsati oldindan tekshiruvdan keyin olib qo'yilgan: sessiya RUNNING qoladi, keyin tiklash mumkin.
            if (activeSessionId == null) stopSelf()
            return
        }
        if (activeSessionId != null) return
        activeSessionId = sessionId
        wakeLock = getSystemService(PowerManager::class.java)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "SectorVerify:survey")
            .apply { acquire(MAX_WAKE_MS) }
        lifecycleScope.launch {
            val session = sessions.session(sessionId) ?: return@launch stopSelf()
            val plan = sessions.plan(sessionId) ?: return@launch stopSelf()
            val config = SvJson.parseConfig(session.configJson)
            val subId = session.subscriptionId ?: return@launch stopSelf()
            val e = SurveyEngine(sessionId, plan, config, BufferedSampleWriter(sessions.sink(sessionId)))
            engine = e
            pipeline = e.start(
                scope = lifecycleScope,
                cells = CellCollector(this@SurveyForegroundService, subId).samples(),
                gnss = GnssCollector(this@SurveyForegroundService).fixes(),
                traffic = TrafficGenerator(settings.current().trafficUrl).run(),
                restoredSamples = sessions.samples(sessionId),
                restoredFixes = sessions.fixes(sessionId),
            )
            if (stopRequested) finish()
            e.state.collectLatest { s ->
                controller.publish(s)
                val pct = ((s.live?.overallCoverage ?: 0.0) * PERCENT).roundToInt()
                notify(NOTIFICATION_ID, progressNotification(s.samples, pct))
                if (s.readyAtSamples != null && !readyShown) {
                    readyShown = true
                    notify(READY_NOTIFICATION_ID, readyNotification())
                }
            }
        }
    }

    private fun finish() {
        val e = engine
        if (e == null) {
            if (activeSessionId != null) stopRequested = true else stopSelf()
            return
        }
        if (finishing) return
        finishing = true
        val sessionId = e.state.value.sessionId ?: return stopSelf()
        lifecycleScope.launch {
            withContext(NonCancellable) {
                e.stop()
                pipeline?.cancel()
                sessions.setMeasuredRate(sessionId, e.measuredRateHz)
                sessions.finish(sessionId, SessionStatus.DONE)
                analysis.analyze(sessionId)
                controller.finished(sessionId)
            }
            engine = null
            ServiceCompat.stopForeground(this@SurveyForegroundService, ServiceCompat.STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    override fun onDestroy() {
        wakeLock?.takeIf { it.isHeld }?.release()
        super.onDestroy()
    }

    private fun createChannels() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL, getString(R.string.survey_channel_name), NotificationManager.IMPORTANCE_LOW),
        )
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_READY, getString(R.string.survey_channel_ready), NotificationManager.IMPORTANCE_HIGH),
        )
    }

    private fun openApp(): PendingIntent? = packageManager.getLaunchIntentForPackage(packageName)?.let {
        PendingIntent.getActivity(this, 0, it, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    private fun progressNotification(samples: Int, coveragePct: Int): Notification {
        val stop = PendingIntent.getService(
            this,
            1,
            Intent(this, SurveyForegroundService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_survey_notification)
            .setContentTitle(getString(R.string.survey_notification_title))
            .setContentText(getString(R.string.survey_notification_text, samples, coveragePct))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openApp())
            .addAction(0, getString(R.string.survey_notification_stop), stop)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun readyNotification(): Notification = NotificationCompat.Builder(this, CHANNEL_READY)
        .setSmallIcon(R.drawable.ic_survey_notification)
        .setContentTitle(getString(R.string.survey_notification_ready_title))
        .setContentText(getString(R.string.survey_notification_ready_text))
        .setContentIntent(openApp())
        .setAutoCancel(true)
        .build()

    @Suppress("MissingPermission") // POST_NOTIFICATIONS rad etilgan → tizim uni jimgina tashlaydi; oldindan tekshiruv ogohlantiradi.
    private fun notify(id: Int, n: Notification) = getSystemService(NotificationManager::class.java).notify(id, n)

    companion object {
        const val ACTION_START = "uz.sectorverify.survey.START"
        const val ACTION_STOP = "uz.sectorverify.survey.STOP"
        const val EXTRA_SESSION = "session_id"
        private const val CHANNEL = "survey"
        private const val CHANNEL_READY = "survey_ready"
        private const val NOTIFICATION_ID = 1001
        private const val READY_NOTIFICATION_ID = 1002
        private const val MAX_WAKE_MS = 3 * 60 * 60 * 1000L
        private const val PERCENT = 100

        fun start(context: Context, sessionId: String) = ContextCompat.startForegroundService(
            context,
            Intent(context, SurveyForegroundService::class.java).setAction(ACTION_START).putExtra(EXTRA_SESSION, sessionId),
        )

        fun stop(context: Context) = context.startService(Intent(context, SurveyForegroundService::class.java).setAction(ACTION_STOP))
    }
}
