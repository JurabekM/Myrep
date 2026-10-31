package uz.qarzsiz.app.data

import kotlinx.serialization.Serializable
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.Habit
import uz.qarzsiz.core.Habits
import uz.qarzsiz.core.PlanSettings
import uz.qarzsiz.core.Script

/** To'lov yozuvi (qarz valyutasida). */
@Serializable
data class Payment(
    val id: String,
    val debtId: String,
    val amount: Long,
    /** ISO sana (yyyy-MM-dd). */
    val date: String,
    val note: String = "",
)

/** Ilovaning butun holati — bitta shifrlangan faylda saqlanadi. */
@Serializable
data class AppState(
    val schemaVersion: Int = SCHEMA_VERSION,
    val onboardingDone: Boolean = false,
    /** Ekranni suratga olish va «so'nggi ilovalar»da ko'rinishni taqiqlash. */
    val secureScreen: Boolean = true,
    val settings: PlanSettings = PlanSettings(),
    val debts: List<Debt> = emptyList(),
    val payments: List<Payment> = emptyList(),
    val habits: List<Habit> = Habits.defaults,
    /** Bajarilgan odatlar: «2026-10-31|early». */
    val habitDone: Set<String> = emptySet(),
    /** Interfeys yozuvi: lotin yoki kirill. */
    val script: Script = Script.LATIN,
    /** «Yo'l xaritasi» o'qildi (2-qadam belgisi uchun). */
    val analysisSeen: Boolean = false,
) {
    companion object {
        const val SCHEMA_VERSION = 1
    }
}
