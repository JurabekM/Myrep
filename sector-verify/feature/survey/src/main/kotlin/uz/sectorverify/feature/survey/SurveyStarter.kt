package uz.sectorverify.feature.survey

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import uz.sectorverify.analysis.ALGO_VERSION
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.feature.survey.service.SurveyForegroundService
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.telephony.SimInfo

sealed interface StartResult {
    data class Started(val sessionId: String) : StartResult

    /** Hech bir SIM reja MCC/MNC ga mos emas — o'lchov boshlanmasligi kerak (§7 dual-SIM). */
    data class NoMatchingSim(val planMccMnc: String) : StartResult

    data object UnknownSite : StartResult
}

/** O'lchovlarni boshlaydi, davom ettiradi va to'xtatadi; UI testlarda soxtalashtiriladi. */
interface SurveyLauncher {
    suspend fun start(siteId: Long, mode: SessionMode, sim: SimInfo?, appVersion: String): StartResult

    /** Joylashuv ruxsati bo'lmasa false (hech narsa boshlanmaydi) — foydalanuvchi oldindan tekshiruvdan qayta o'tishi kerak. */
    fun resume(sessionId: String): Boolean

    suspend fun abandon(sessionId: String)

    fun stop()
}

/** Sessiya qatorini (amaldagi config'ning to'liq nusxasi bilan) yaratadi va foreground service'ni ishga tushiradi. */
class SurveyStarter @Inject constructor(
    @ApplicationContext private val context: Context,
    private val plans: PlanRepository,
    private val sessions: SessionRepository,
    private val settings: SettingsRepository,
) : SurveyLauncher {
    override suspend fun start(siteId: Long, mode: SessionMode, sim: SimInfo?, appVersion: String): StartResult {
        val site = plans.site(siteId) ?: return StartResult.UnknownSite
        if (sim == null) return StartResult.NoMatchingSim(site.plan.mccMnc)
        val s = settings.current()
        val id = sessions.create(
            NewSession(
                siteId = siteId,
                mode = mode,
                deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}",
                apiLevel = Build.VERSION.SDK_INT,
                baseband = Build.getRadioVersion(),
                appVersion = appVersion,
                algoVersion = ALGO_VERSION,
                config = s.effectiveConfig,
                subscriptionId = sim.subscriptionId,
            ),
        )
        SurveyForegroundService.start(context, id)
        return StartResult.Started(id)
    }

    /** §7: o'ldirilgan jarayon qoldirgan RUNNING sessiyani davom ettirish mumkin (o'sha id, ma'lumotlar saqlanadi). */
    override fun resume(sessionId: String): Boolean {
        val granted =
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (granted) SurveyForegroundService.start(context, sessionId)
        return granted
    }

    override suspend fun abandon(sessionId: String) = sessions.finish(sessionId, SessionStatus.ABORTED)

    override fun stop() {
        SurveyForegroundService.stop(context)
    }
}
