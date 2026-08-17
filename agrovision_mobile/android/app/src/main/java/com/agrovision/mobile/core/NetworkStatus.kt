package com.agrovision.mobile.core

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

/** Qurilmaning joriy tarmoq holatini tekshirish (faqat Ob-havo modulida ishlatiladi). */
object NetworkStatus {
    fun isOnline(context: Context): Boolean {
        val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
        val network = manager.activeNetwork ?: return false
        val capabilities = manager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }
}
