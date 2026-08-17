package com.agrovision.app.core

import androidx.compose.runtime.mutableStateOf

/**
 * Interfeys tarjimalari — desktop `core/i18n.py` porti. Kalit sifatida
 * o'zbekcha matn ishlatiladi (uz uchun tarjima kerak emas).
 */
object I18n {
    val LANGUAGES = listOf("uz" to "O'zbekcha", "ru" to "Русский", "en" to "English")

    private val ru = mapOf(
        "Bosh sahifa" to "Главная",
        "Ma'lumotlar" to "Данные",
        "Xarita" to "Карта",
        "Analitika" to "Аналитика",
        "Machine Learning" to "Машинное обучение",
        "Sun'iy yo'ldosh" to "Спутник",
        "Ob-havo" to "Погода",
        "Bozor" to "Рынок",
        "Sug'orish" to "Орошение",
        "Moliya" to "Финансы",
        "AI Yordamchi" to "AI Ассистент",
        "Hisobotlar" to "Отчёты",
        "Import" to "Импорт",
        "Tuproq tahlili" to "Анализ почвы",
        "Administrator" to "Администратор",
        "Sozlamalar" to "Настройки",
        "Chiqish" to "Выход",
        "Qidiruv" to "Поиск",
        "Kirish" to "Вход",
        "Yer maydoni" to "Земельная площадь",
        "Fermerlar" to "Фермеры",
        "Xo'jaliklar" to "Хозяйства",
        "Dalalar" to "Поля",
        "Ekinlar" to "Культуры",
        "Ogohlantirishlar" to "Предупреждения",
        "Saqlash" to "Сохранить",
        "Bekor qilish" to "Отмена",
        "Yil" to "Год",
        "Umumiy" to "Общее",
        "Tahlil" to "Анализ",
        "Monitoring" to "Мониторинг",
        "Iqtisod" to "Экономика",
        "Boshqaruv" to "Управление",
        "Ma'lumot yo'q" to "Нет данных",
    )

    private val en = mapOf(
        "Bosh sahifa" to "Dashboard",
        "Ma'lumotlar" to "Data",
        "Xarita" to "Map",
        "Analitika" to "Analytics",
        "Machine Learning" to "Machine Learning",
        "Sun'iy yo'ldosh" to "Satellite",
        "Ob-havo" to "Weather",
        "Bozor" to "Market",
        "Sug'orish" to "Irrigation",
        "Moliya" to "Finance",
        "AI Yordamchi" to "AI Assistant",
        "Hisobotlar" to "Reports",
        "Import" to "Import",
        "Tuproq tahlili" to "Soil analysis",
        "Administrator" to "Administrator",
        "Sozlamalar" to "Settings",
        "Chiqish" to "Log out",
        "Qidiruv" to "Search",
        "Kirish" to "Sign in",
        "Yer maydoni" to "Total area",
        "Fermerlar" to "Farmers",
        "Xo'jaliklar" to "Farms",
        "Dalalar" to "Fields",
        "Ekinlar" to "Crops",
        "Ogohlantirishlar" to "Alerts",
        "Saqlash" to "Save",
        "Bekor qilish" to "Cancel",
        "Yil" to "Year",
        "Umumiy" to "General",
        "Tahlil" to "Analysis",
        "Monitoring" to "Monitoring",
        "Iqtisod" to "Economy",
        "Boshqaruv" to "Management",
        "Ma'lumot yo'q" to "No data",
    )

    /**
     * Joriy til Compose holati sifatida saqlanadi. Oddiy `var` bo'lsa
     * `t()` chaqirgan composable'lar til almashganda qayta chizilmaydi va
     * menyu eski tilda qolib ketadi.
     */
    private val languageState = mutableStateOf("uz")

    var language: String
        get() = languageState.value
        set(value) { languageState.value = value }

    fun t(text: String): String = when (language) {
        "ru" -> ru[text] ?: text
        "en" -> en[text] ?: text
        else -> text
    }
}
