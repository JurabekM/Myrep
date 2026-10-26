package uz.sectorverify.feature.survey

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import uz.sectorverify.location.GnssCollector
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.telephony.CellCollector
import uz.sectorverify.telephony.SimInfo
import uz.sectorverify.telephony.SubscriptionSelector

/** Device state read by the pre-check screen; faked in tests. */
interface PreCheckSource {
    fun locationGranted(): Boolean

    fun phoneStateGranted(): Boolean

    fun notificationsGranted(): Boolean

    fun sims(): List<SimInfo>

    fun gpsEnabled(): Boolean

    fun fixes(): Flow<GnssFix>

    fun cells(subscriptionId: Int): Flow<List<CellSample>>
}

class AndroidPreCheckSource @Inject constructor(@ApplicationContext private val context: Context) : PreCheckSource {
    private fun granted(p: String) = ContextCompat.checkSelfPermission(context, p) == PackageManager.PERMISSION_GRANTED

    override fun locationGranted() = granted(Manifest.permission.ACCESS_FINE_LOCATION)

    override fun phoneStateGranted() = granted(Manifest.permission.READ_PHONE_STATE)

    override fun notificationsGranted() =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU || granted(Manifest.permission.POST_NOTIFICATIONS)

    override fun sims(): List<SimInfo> = if (phoneStateGranted()) SubscriptionSelector.activeSims(context) else emptyList()

    override fun gpsEnabled() = GnssCollector(context).isGpsEnabled()

    override fun fixes(): Flow<GnssFix> = if (locationGranted()) GnssCollector(context).fixes() else emptyFlow()

    override fun cells(subscriptionId: Int): Flow<List<CellSample>> =
        if (locationGranted()) CellCollector(context, subscriptionId).samples() else emptyFlow()
}

/** Runtime permissions the survey asks for; POST_NOTIFICATIONS exists only on API 33+. */
fun runtimePermissions(): Array<String> = buildList {
    add(Manifest.permission.ACCESS_FINE_LOCATION)
    add(Manifest.permission.ACCESS_COARSE_LOCATION)
    add(Manifest.permission.READ_PHONE_STATE)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) add(Manifest.permission.POST_NOTIFICATIONS)
}.toTypedArray()
