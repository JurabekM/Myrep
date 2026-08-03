package uz.dehqonkomakchi.app.ui.nav

object Routes {
    const val ONBOARDING = "onboarding"
    const val HOME = "home"
    const val DIAGNOSE = "diagnose"
    const val DIAGNOSE_RESULT = "diagnose_result/{recordId}"
    const val IRRIGATION = "irrigation"
    const val LEDGER = "ledger"
    const val MARKET = "market"
    const val MARKET_NEW_LISTING = "market_new_listing"
    const val SETTINGS = "settings"
    const val PRIVACY_POLICY = "privacy_policy"
    const val TERMS = "terms"

    fun diagnoseResult(recordId: String) = "diagnose_result/$recordId"
}
