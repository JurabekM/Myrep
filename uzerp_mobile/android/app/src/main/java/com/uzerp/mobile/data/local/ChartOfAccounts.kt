package com.uzerp.mobile.data.local

/**
 * O'zbekiston buxgalteriya hisobi milliy standarti (NAS-21) asosidagi
 * soddalashtirilgan hisoblar rejasi — Python `schema.py` bilan AYNAN bir xil.
 *
 * (kod, nom, tur, kassami, bankmi)
 */
val CHART_OF_ACCOUNTS: List<AccountSeed> = listOf(
    AccountSeed("0100", "Asosiy vositalar", "asset"),
    AccountSeed("0200", "Asosiy vositalar eskirishi (amortizatsiya)", "contra_asset"),
    AccountSeed("1000", "Materiallar", "asset"),
    AccountSeed("2900", "Tovarlar", "asset"),
    AccountSeed("4010", "Xaridorlar va buyurtmachilar qarzi", "asset"),
    AccountSeed("4310", "Ta'minotchilarga berilgan avanslar", "asset"),
    AccountSeed("4410", "Hisobga olinadigan QQS (kirim QQS)", "asset"),
    AccountSeed("5010", "Kassa (milliy valyuta)", "asset", isCash = true),
    AccountSeed("5110", "Hisob-kitob raqami (bank)", "asset", isBank = true),
    AccountSeed("6010", "Ta'minotchilarga to'lanadigan qarz", "liability"),
    AccountSeed("6310", "Xaridorlardan olingan avanslar", "liability"),
    AccountSeed("6410", "Byudjetga to'lovlar bo'yicha qarz (soliqlar)", "liability"),
    AccountSeed("6520", "QQS bo'yicha qarz", "liability"),
    AccountSeed("6710", "Mehnat haqi bo'yicha xodimlarga qarz", "liability"),
    AccountSeed("8330", "Ustav kapitali", "equity"),
    AccountSeed("8710", "Taqsimlanmagan foyda", "equity"),
    AccountSeed("9010", "Mahsulot (tovar) sotishdan daromad", "income"),
    AccountSeed("9110", "Sotilgan mahsulot tannarxi", "expense"),
    AccountSeed("9410", "Davr xarajatlari (ma'muriy, savdo)", "expense"),
    AccountSeed("9430", "Boshqa operatsion xarajatlar", "expense"),
    AccountSeed("9910", "Yakuniy moliyaviy natija", "equity"),
)

data class AccountSeed(
    val code: String,
    val name: String,
    val type: String,
    val isCash: Boolean = false,
    val isBank: Boolean = false,
)
