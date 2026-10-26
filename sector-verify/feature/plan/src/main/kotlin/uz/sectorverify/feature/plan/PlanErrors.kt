package uz.sectorverify.feature.plan

import android.content.res.Resources
import uz.sectorverify.format.PlanError
import uz.sectorverify.format.PlanErrorCode

/** Localised CSV error with its line number (§5.3). */
fun PlanError.localized(res: Resources): String {
    val id = when (code) {
        PlanErrorCode.EMPTY_FILE -> R.string.plan_err_empty_file
        PlanErrorCode.MISSING_COLUMN -> R.string.plan_err_missing_column
        PlanErrorCode.WRONG_COLUMN_COUNT -> R.string.plan_err_wrong_column_count
        PlanErrorCode.EMPTY_VALUE -> R.string.plan_err_empty_value
        PlanErrorCode.NOT_A_NUMBER -> R.string.plan_err_not_a_number
        PlanErrorCode.LAT_RANGE -> R.string.plan_err_lat_range
        PlanErrorCode.LON_RANGE -> R.string.plan_err_lon_range
        PlanErrorCode.BAD_RAT -> R.string.plan_err_bad_rat
        PlanErrorCode.PCI_RANGE -> R.string.plan_err_pci_range
        PlanErrorCode.AZIMUTH_RANGE -> R.string.plan_err_azimuth_range
        PlanErrorCode.HPBW_RANGE -> R.string.plan_err_hpbw_range
        PlanErrorCode.ARFCN_RANGE -> R.string.plan_err_arfcn_range
        PlanErrorCode.DUPLICATE_CELL -> R.string.plan_err_duplicate_cell
        PlanErrorCode.SITE_COORDS_MISMATCH -> R.string.plan_err_site_coords_mismatch
    }
    val text = res.getString(id, column.orEmpty(), value.orEmpty())
    return res.getString(R.string.plan_error_line, line, text)
}
