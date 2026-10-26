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

    /** No SIM matches the plan MCC/MNC — the survey must not start (§7 dual-SIM). */
    data class NoMatchingSim(val planMccMnc: String) : StartResult

    data object UnknownSite : StartResult
}

/** Starts, resumes and stops surveys; faked in UI tests. */
interface SurveyLauncher {
    suspend fun start(siteId: Long, mode: SessionMode, sim: SimInfo?, appVersion: String): StartResult

    /** False (nothing started) when location permission is missing — the user must pass the pre-check again. */
    fun resume(sessionId: String): Boolean

    suspend fun abandon(sessionId: String)

    fun stop()
}

/** Creates the session row (with a full copy of the effective config) and starts the foreground service. */
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

    /** §7: a RUNNING session left by a killed process can be resumed (same id, data kept). */
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
