package com.agrovision.app.config

/** Desktop `config/settings.py` dagi konstantalarning ko'chirmasi. */
object Constants {
    const val APP_NAME = "AgroVision"
    const val APP_VERSION = "1.0.0"

    const val HISTORY_START_YEAR = 2021
    val HISTORY_YEARS = (HISTORY_START_YEAR until HISTORY_START_YEAR + 5).toList()

    /** Vegetatsiya mavsumi: aprel–sentabr. */
    val SEASON_MONTHS = 4..9

    const val LOGIN_MAX_ATTEMPTS = 5
    const val LOGIN_LOCK_MINUTES = 10

    /** Moliyaviy kalibrovka (desktop seed.py bilan bir xil). */
    const val WHOLESALE_FACTOR = 0.45
    const val EXPENSE_FACTOR_MIN = 1.5
    const val EXPENSE_FACTOR_MAX = 1.9

    val DEFAULT_SETTINGS = mapOf(
        "theme" to "system",
        "language" to "uz",
        "offline_mode" to "auto",
        "weather_provider" to "open-meteo",
        "map_default_lat" to "41.3",
        "map_default_lon" to "64.5",
        "backup_keep" to "20",
    )

    val SOIL_TYPES = listOf(
        "bo'z tuproq", "o'tloq tuproq", "sho'rlangan tuproq", "qumloq tuproq", "gilli tuproq",
    )
    val IRRIGATION_METHODS = listOf("egat", "tomchilatib", "yomg'irlatib", "bostirib")
    val FINANCE_CATEGORIES = listOf(
        "income" to "Daromad", "expense" to "Xarajat",
        "credit" to "Kredit", "subsidy" to "Subsidiya",
    )
}
