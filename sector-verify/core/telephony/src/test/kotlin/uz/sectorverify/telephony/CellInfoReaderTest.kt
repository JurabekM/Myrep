package uz.sectorverify.telephony

import android.os.Build
import android.telephony.CellInfoGsm
import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.shouldBe
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.shadows.CellIdentityLteBuilder
import org.robolectric.shadows.CellIdentityNrBuilder
import org.robolectric.shadows.CellInfoLteBuilder
import org.robolectric.shadows.CellInfoNrBuilder
import org.robolectric.shadows.CellSignalStrengthLteBuilder
import org.robolectric.shadows.CellSignalStrengthNrBuilder
import org.robolectric.util.ReflectionHelpers
import uz.sectorverify.model.Rat

/** Robolectric builder'lari bilan yasalgan soxta CellInfo obyektlari (§9, 2-bosqich). */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [Build.VERSION_CODES.UPSIDE_DOWN_CAKE])
class CellInfoReaderTest {
    @Test
    fun readsLte() {
        val info = CellInfoLteBuilder.newBuilder()
            .setRegistered(true)
            .setTimeStampNanos(7_000_000_000)
            .setCellIdentity(CellIdentityLteBuilder.newBuilder().setEarfcn(1300).setPci(141).setCi(1234).setTac(101).build())
            .setCellSignalStrength(
                CellSignalStrengthLteBuilder.newBuilder().setRsrp(-95).setRsrq(-11).setRssnr(12).setTimingAdvance(4).build(),
            )
            .build()
        val raw = CellInfoReader.read(info)!!
        raw.rat shouldBe Rat.LTE
        raw.registered shouldBe true
        raw.arfcn shouldBe 1300
        raw.pci shouldBe 141
        raw.rsrp shouldBe -95
        raw.ta shouldBe 4
        raw.ci shouldBe 1234
        raw.timestampNanos shouldBe 7_000_000_000
        CellNormalizer.normalize(raw, 8_000_000_000)!!.rsrp shouldBe -95.0
    }

    @Test
    fun readsNr() {
        val info = CellInfoNrBuilder.newBuilder()
            .setTimeStampNanos(3_000_000_000)
            .setCellIdentity(CellIdentityNrBuilder.newBuilder().setNrarfcn(636_666).setPci(900).setNci(55).setTac(7).build())
            .setCellSignalStrength(CellSignalStrengthNrBuilder.newBuilder().setSsRsrp(-100).setSsRsrq(-12).setSsSinr(10).build())
            .build()
        val raw = CellInfoReader.read(info)!!
        raw.rat shouldBe Rat.NR
        raw.arfcn shouldBe 636_666
        raw.pci shouldBe 900
        raw.rsrp shouldBe -100
        raw.ta shouldBe CellNormalizer.UNAVAILABLE
    }

    @Test
    fun ignoresOtherRats() {
        val gsm = ReflectionHelpers.callConstructor(CellInfoGsm::class.java)
        CellInfoReader.read(gsm).shouldBeNull()
    }
}
