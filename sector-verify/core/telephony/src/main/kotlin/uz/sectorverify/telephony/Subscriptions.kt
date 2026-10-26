package uz.sectorverify.telephony

import android.annotation.SuppressLint
import android.content.Context
import android.telephony.SubscriptionManager

data class SimInfo(val subscriptionId: Int, val mcc: String?, val mnc: String?, val carrierName: String?, val slotIndex: Int) {
    val mccMnc: String? get() = if (mcc != null && mnc != null) mcc + mnc else null
}

/** §7 dual-SIM: the subscription whose MCC/MNC matches the plan; none → the survey must not start. */
object SubscriptionSelector {
    fun select(sims: List<SimInfo>, planMccMnc: String): SimInfo? = sims.firstOrNull { it.mccMnc == planMccMnc.trim() }

    /** Needs READ_PHONE_STATE. */
    @SuppressLint("MissingPermission")
    fun activeSims(context: Context): List<SimInfo> {
        val sm = context.getSystemService(SubscriptionManager::class.java) ?: return emptyList()
        return sm.activeSubscriptionInfoList.orEmpty().map {
            SimInfo(it.subscriptionId, it.mccString, it.mncString, it.carrierName?.toString(), it.simSlotIndex)
        }
    }
}
