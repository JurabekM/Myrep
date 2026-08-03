package uz.dehqonkomakchi.app

import com.google.common.truth.Truth.assertThat
import org.junit.Test
import uz.dehqonkomakchi.app.data.repo.LedgerSummary

class LedgerSummaryTest {

    @Test
    fun `profit is revenue minus expense`() {
        val summary = LedgerSummary(totalExpense = 400_000.0, totalRevenue = 900_000.0, totalHarvestKg = 120.0)
        assertThat(summary.profit).isEqualTo(500_000.0)
    }

    @Test
    fun `cost per kg divides expense by harvested quantity`() {
        val summary = LedgerSummary(totalExpense = 240_000.0, totalRevenue = 0.0, totalHarvestKg = 120.0)
        assertThat(summary.costPerKg).isEqualTo(2_000.0)
    }

    @Test
    fun `cost per kg is null when no harvest logged yet`() {
        val summary = LedgerSummary(totalExpense = 100_000.0, totalRevenue = 0.0, totalHarvestKg = 0.0)
        assertThat(summary.costPerKg).isNull()
    }

    @Test
    fun `loss is represented as negative profit`() {
        val summary = LedgerSummary(totalExpense = 500_000.0, totalRevenue = 300_000.0, totalHarvestKg = 50.0)
        assertThat(summary.profit).isEqualTo(-200_000.0)
    }
}
