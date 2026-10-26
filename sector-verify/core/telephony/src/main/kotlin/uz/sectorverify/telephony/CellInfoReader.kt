package uz.sectorverify.telephony

import android.os.Build
import android.telephony.CellIdentityNr
import android.telephony.CellInfo
import android.telephony.CellInfoLte
import android.telephony.CellInfoNr
import android.telephony.CellSignalStrengthNr
import uz.sectorverify.model.Rat

/** Copies the public CellInfo getters into [RawCell]; GSM/WCDMA and others are ignored (null). */
object CellInfoReader {
    private const val NANOS_PER_MS = 1_000_000L

    fun read(info: CellInfo): RawCell? = when (info) {
        is CellInfoLte -> lte(info)
        is CellInfoNr -> nr(info)
        else -> null
    }

    private fun timestampNanos(info: CellInfo): Long =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            info.timestampMillis * NANOS_PER_MS
        } else {
            @Suppress("DEPRECATION")
            info.timeStamp
        }

    private fun lte(info: CellInfoLte): RawCell {
        val id = info.cellIdentity
        val ss = info.cellSignalStrength
        return RawCell(
            rat = Rat.LTE,
            registered = info.isRegistered,
            timestampNanos = timestampNanos(info),
            arfcn = id.earfcn,
            pci = id.pci,
            rsrp = ss.rsrp,
            rsrq = ss.rsrq,
            sinr = ss.rssnr,
            ta = ss.timingAdvance,
            ci = id.ci.toLong().let { if (it == Int.MAX_VALUE.toLong()) CellNormalizer.UNAVAILABLE_LONG else it },
            tac = id.tac,
        )
    }

    private fun nr(info: CellInfoNr): RawCell {
        val id = info.cellIdentity as CellIdentityNr
        val ss = info.cellSignalStrength as CellSignalStrengthNr
        return RawCell(
            rat = Rat.NR,
            registered = info.isRegistered,
            timestampNanos = timestampNanos(info),
            arfcn = id.nrarfcn,
            pci = id.pci,
            rsrp = ss.ssRsrp,
            rsrq = ss.ssRsrq,
            sinr = ss.ssSinr,
            ta = CellNormalizer.UNAVAILABLE,
            ci = id.nci,
            tac = id.tac,
        )
    }
}
