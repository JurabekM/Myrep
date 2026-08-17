package com.agrovision.app.core

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

/**
 * Tarmoq holati — desktop `weather.service.is_online()` analogi.
 * `offline_mode` sozlamasi: auto | on (majburiy offlayn) | off (majburiy onlayn).
 */
object NetworkStatus {
    @Volatile
    var offlineMode: String = "auto"

    fun isOnline(context: Context): Boolean {
        if (offlineMode == "on") return false
        if (offlineMode == "off") return true
        return hasNetwork(context)
    }

    fun hasNetwork(context: Context): Boolean {
        val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false
        val network = manager.activeNetwork ?: return false
        val capabilities = manager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }
}
