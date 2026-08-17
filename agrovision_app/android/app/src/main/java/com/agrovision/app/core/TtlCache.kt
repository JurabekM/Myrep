package com.agrovision.app.core

/**
 * Oddiy TTL kesh — desktop `core/cache.py` porti. Og'ir agregatsiya
 * so'rovlarini qayta-qayta bajarishdan saqlaydi.
 */
class TtlCache<K, V>(private val ttlMillis: Long = 60_000, private val maxItems: Int = 128) {
    private val data = LinkedHashMap<K, Pair<Long, V>>()

    @Synchronized
    fun get(key: K): V? {
        val entry = data[key] ?: return null
        if (System.currentTimeMillis() > entry.first) {
            data.remove(key)
            return null
        }
        return entry.second
    }

    @Synchronized
    fun put(key: K, value: V) {
        if (data.size >= maxItems) {
            val oldest = data.keys.firstOrNull()
            if (oldest != null) data.remove(oldest)
        }
        data[key] = (System.currentTimeMillis() + ttlMillis) to value
    }

    @Synchronized
    fun clear() = data.clear()

    /** Keshdan o'qiydi, bo'lmasa yuklab keshlaydi (suspend — @Synchronized qo'llanmaydi). */
    suspend fun getOrPut(key: K, loader: suspend () -> V): V {
        get(key)?.let { return it }
        val value = loader()
        put(key, value)
        return value
    }
}

/** Butun ilova keshlarini bir joyda bo'shatish (import/tiklashdan keyin). */
object CacheRegistry {
    private val caches = mutableListOf<TtlCache<*, *>>()

    @Synchronized
    fun <K, V> register(cache: TtlCache<K, V>): TtlCache<K, V> {
        caches += cache
        return cache
    }

    @Synchronized
    fun clearAll() = caches.forEach { it.clear() }
}
