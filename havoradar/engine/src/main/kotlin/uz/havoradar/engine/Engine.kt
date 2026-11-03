package uz.havoradar.engine

import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import uz.havoradar.engine.geo.Places
import uz.havoradar.engine.json.Codec
import uz.havoradar.engine.knowledge.Guide
import uz.havoradar.engine.model.AirSeries
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.Snapshot
import uz.havoradar.engine.model.SourceId
import uz.havoradar.engine.model.SourceStatus
import uz.havoradar.engine.model.StoredState
import uz.havoradar.engine.model.WeatherSeries
import uz.havoradar.engine.net.HttpException
import uz.havoradar.engine.net.HttpFetcher
import uz.havoradar.engine.risk.ReportBuilder
import uz.havoradar.engine.sources.OpenMeteo
import uz.havoradar.engine.sources.SourceFormatException
import java.time.Duration
import java.time.Instant

/**
 * HavoRadar yadrosi: har bir joy uchun ob-havo va havo sifati prognozini yig'ish → kunlik issiqlik va havo
 * xavfini baholash. Tarmoq va vaqt tashqaridan beriladi (testlanadi). Ishlamagan manba o'rniga oldingi
 * prognoz ([STALE_MAX] gacha) «eskirgan» belgisi bilan ishlatiladi.
 */
class Engine(
    private val http: HttpFetcher,
    val places: Places = Places.load(),
    val guide: Guide = Guide.load(),
    private val clock: () -> Instant = Instant::now,
) {
    val codec = Codec(places, guide)

    /** Sinxronlash natijasi: UI uchun baholangan snapshot va diskka yoziladigan xom holat. */
    data class Synced(
        val snapshot: Snapshot,
        val state: StoredState,
    )

    suspend fun sync(
        settings: Settings,
        previous: StoredState?,
    ): Synced =
        coroutineScope {
            val now = clock()
            val targets = settings.allPlaces.mapNotNull { places[it] }
            val weatherJobs = targets.map { p -> async { p.id to runCatching { OpenMeteo.fetchWeather(http, p, now) } } }
            val airJobs = targets.map { p -> async { p.id to runCatching { OpenMeteo.fetchAir(http, p, now) } } }

            val weather = mutableListOf<WeatherSeries>()
            val air = mutableListOf<AirSeries>()
            val statuses = mutableListOf<SourceStatus>()

            fun <T> collect(
                id: SourceId,
                results: List<Pair<String, Result<T>>>,
                old: (String) -> T?,
                fetchedAt: (T) -> Instant,
                out: MutableList<T>,
            ) {
                var stale = false
                val errors = mutableListOf<String>()
                for ((placeId, r) in results) {
                    val fresh = r.getOrNull()
                    if (fresh != null) {
                        out += fresh
                        continue
                    }
                    errors += "${places.name(placeId)}: ${describe(r.exceptionOrNull())}"
                    old(placeId)?.takeIf { Duration.between(fetchedAt(it), now) <= STALE_MAX }?.let {
                        out += it
                        stale = true
                    }
                }
                // Xato holatida fetchedAt — oxirgi muvaffaqiyatli vaqt; ketma-ket xatolarda ham saqlanib qoladi.
                val lastOk = previous?.sources?.firstOrNull { it.source == id }?.fetchedAt
                statuses +=
                    SourceStatus(
                        source = id,
                        ok = errors.isEmpty(),
                        fetchedAt = if (errors.isEmpty()) now else lastOk ?: now,
                        error = errors.takeIf { it.isNotEmpty() }?.joinToString("; "),
                        stale = stale,
                    )
            }

            collect(SourceId.WEATHER, weatherJobs.awaitAll(), { id -> previous?.weather?.firstOrNull { it.placeId == id } }, { it.fetchedAt }, weather)
            collect(SourceId.AIR, airJobs.awaitAll(), { id -> previous?.air?.firstOrNull { it.placeId == id } }, { it.fetchedAt }, air)

            val state = StoredState(now, weather, air, statuses)
            Synced(build(now, settings, state), state)
        }

    /** Tarmoqsiz qayta baholash (profil yoki joy o'zgarganda; vaqt o'tgani sari «bugun» ham siljiydi). */
    fun reassess(
        state: StoredState,
        settings: Settings,
    ): Snapshot = build(clock(), settings, state)

    private fun build(
        now: Instant,
        settings: Settings,
        state: StoredState,
    ): Snapshot {
        val reports =
            settings.allPlaces.mapNotNull { id ->
                val place = places[id] ?: return@mapNotNull null
                ReportBuilder.build(
                    place,
                    state.weather.firstOrNull { it.placeId == id },
                    state.air.firstOrNull { it.placeId == id },
                    settings.profile,
                    now,
                )
            }
        return Snapshot(state.generatedAt, settings.profile, reports, state.sources)
    }

    companion object {
        /** Eski prognoz shu muddatgacha ishlatiladi (7 kunlik prognozning keyingi kunlari hali foydali). */
        val STALE_MAX: Duration = Duration.ofDays(3)

        fun describe(t: Throwable?): String =
            when (t) {
                null -> "noma'lum xato"
                is java.net.UnknownHostException -> "Internet aloqasi yo'q"
                is java.net.SocketTimeoutException -> "Server javob bermadi (vaqt tugadi)"
                is HttpException ->
                    when (t.code) {
                        429 -> "So'rovlar limiti tugadi (HTTP 429), keyinroq qayta urinadi"
                        else -> "Server xatosi (HTTP ${t.code})"
                    }
                is SourceFormatException -> t.message ?: "Javob formati noto'g'ri"
                else -> t.message?.take(160) ?: t::class.java.simpleName
            }
    }
}
