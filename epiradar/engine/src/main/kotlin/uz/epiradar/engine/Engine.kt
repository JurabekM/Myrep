package uz.epiradar.engine

import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import uz.epiradar.engine.geo.Countries
import uz.epiradar.engine.json.Codec
import uz.epiradar.engine.json.StoredState
import uz.epiradar.engine.knowledge.DiseaseCatalog
import uz.epiradar.engine.model.Settings
import uz.epiradar.engine.model.Signal
import uz.epiradar.engine.model.Snapshot
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.model.SourceStatus
import uz.epiradar.engine.model.TrendSeries
import uz.epiradar.engine.net.HttpFetcher
import uz.epiradar.engine.risk.EventClusterer
import uz.epiradar.engine.risk.RiskScorer
import uz.epiradar.engine.sources.CdcTravelSource
import uz.epiradar.engine.sources.EcdcSource
import uz.epiradar.engine.sources.SignalFactory
import uz.epiradar.engine.sources.SignalSource
import uz.epiradar.engine.sources.WhoDonSource
import uz.epiradar.engine.text.SignalClassifier
import uz.epiradar.engine.trend.FluNetSource
import uz.epiradar.engine.trend.TrendAnalyzer
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset

/**
 * EpiRadar yadrosi: manbalardan yig'ish → tasniflash → hodisalarga birlashtirish → xavfni baholash
 * → trend anomaliyalari. Tarmoq, vaqt va ma'lumotnomalar tashqaridan beriladi (testlanadi).
 */
class Engine(
    private val http: HttpFetcher,
    val catalog: DiseaseCatalog = DiseaseCatalog.load(),
    val countries: Countries = Countries.load(),
    private val clock: () -> Instant = Instant::now,
) {
    private val classifier = SignalClassifier(catalog, countries)
    private val factory = SignalFactory(classifier)
    private val scorer = RiskScorer(catalog, countries)
    private val trendAnalyzer = TrendAnalyzer(countries)
    private val fluNet = FluNetSource()
    val codec = Codec(catalog, countries)

    val sources: List<SignalSource> =
        listOf(
            WhoDonSource(factory),
            EcdcSource(factory),
            CdcTravelSource(factory),
        )

    /** To'liq sinxronlash. Ishlamagan manba o'rniga oldingi muvaffaqiyatli ma'lumot ishlatiladi. */
    suspend fun sync(
        settings: Settings,
        previous: StoredState?,
    ): Snapshot =
        coroutineScope {
            val now = clock()
            val fetched = sources.map { src -> async { src.id to runCatching { src.fetch(http) } } }
            val trendCountries = trendCountries(settings)
            val reuseTrends =
                previous?.trendsFetchedAt?.let { Duration.between(it, now) < TREND_MAX_AGE } == true &&
                    previous.trends.map { it.country }.toSet() == trendCountries.toSet()
            val trendJob =
                if (reuseTrends) {
                    null
                } else {
                    trendCountries.map { iso3 ->
                        async {
                            iso3 to
                                runCatching {
                                    val since = now.atZone(ZoneOffset.UTC).toLocalDate().minusYears(TREND_YEARS)
                                    fluNet.fetch(http, iso3, since)
                                }
                        }
                    }
                }

            val signals = mutableListOf<Signal>()
            val statuses = mutableListOf<SourceStatus>()
            for ((id, result) in fetched.awaitAll()) {
                val fresh = result.getOrNull()
                if (fresh != null) {
                    // Lenta faqat oxirgi N ta xabarni beradi: lentadan tushib qolgan eski xabarlar tarixda saqlanadi
                    // (KEEP_DAYS gacha). Aks holda hodisaning eng birinchi xabari yo'qolib, hodisa id'si o'zgaradi va
                    // bir xil avj olish haqida qayta-qayta bildirishnoma ketadi.
                    val freshIds = fresh.mapTo(HashSet()) { it.id }
                    signals += fresh
                    signals += previous?.signals?.filter { it.source == id && it.id !in freshIds }.orEmpty()
                    statuses += SourceStatus(id, true, fresh.size, now, null, stale = false)
                } else {
                    val old = previous?.signals?.filter { it.source == id }.orEmpty()
                    signals += old
                    val lastOk = previous?.sources?.firstOrNull { it.source == id && it.ok }?.fetchedAt ?: previous?.sources?.firstOrNull { it.source == id }?.fetchedAt
                    statuses += SourceStatus(id, false, old.size, lastOk ?: now, describe(result.exceptionOrNull()), stale = old.isNotEmpty())
                }
            }

            val today = now.atZone(ZoneOffset.UTC).toLocalDate()
            val trends: List<TrendSeries>
            val trendsFetchedAt: Instant?
            if (trendJob == null) {
                trends = previous!!.trends
                trendsFetchedAt = previous.trendsFetchedAt
                signals += previous.signals.filter { it.source == SourceId.WHO_FLUNET }
                statuses += previous.sources.firstOrNull { it.source == SourceId.WHO_FLUNET } ?: SourceStatus(SourceId.WHO_FLUNET, true, trends.size, trendsFetchedAt!!, null, false)
            } else {
                val results = trendJob.awaitAll()
                val ok = results.filter { it.second.isSuccess }
                if (ok.isEmpty() && previous != null && previous.trends.isNotEmpty()) {
                    trends = previous.trends
                    trendsFetchedAt = previous.trendsFetchedAt
                    signals += previous.signals.filter { it.source == SourceId.WHO_FLUNET }
                    statuses += SourceStatus(SourceId.WHO_FLUNET, false, trends.size, trendsFetchedAt ?: now, describe(results.firstOrNull()?.second?.exceptionOrNull()), stale = true)
                } else {
                    val outputs = ok.map { (iso3, r) -> trendAnalyzer.analyze(iso3, r.getOrThrow(), today) }
                    trends = outputs.map { it.series }
                    trendsFetchedAt = if (ok.isEmpty()) null else now
                    signals += outputs.flatMap { it.signals }
                    val failed = results.size - ok.size
                    statuses +=
                        SourceStatus(
                            SourceId.WHO_FLUNET,
                            ok.isNotEmpty(),
                            trends.size,
                            now,
                            if (failed > 0) "$failed ta mamlakat ma'lumoti olinmadi: ${describe(results.first { it.second.isFailure }.second.exceptionOrNull())}" else null,
                            stale = false,
                        )
                }
            }

            build(now, settings, StoredState(now, signals.distinctBy { it.id }, trends, trendsFetchedAt, statuses))
        }

    /** Tarmoqsiz qayta baholash (masalan, foydalanuvchi mamlakatni o'zgartirganda). */
    fun reassess(
        state: StoredState,
        settings: Settings,
    ): Snapshot = build(clock(), settings, state)

    private fun build(
        now: Instant,
        settings: Settings,
        state: StoredState,
    ): Snapshot {
        val cutoff = now.minus(Duration.ofDays(KEEP_DAYS))
        val signals = state.signals.filter { it.publishedAt.isAfter(cutoff) }
        val events =
            EventClusterer
                .cluster(signals)
                .map { scorer.assess(it, settings.country, now) }
                .sortedWith(compareByDescending<uz.epiradar.engine.model.OutbreakEvent> { it.assessment.personalScore }.thenByDescending { it.lastUpdated })
        return Snapshot(
            generatedAt = state.generatedAt,
            country = settings.country,
            globalScore = RiskScorer.combine(events.map { it.assessment.globalScore }),
            personalScore = RiskScorer.combine(events.map { it.assessment.personalScore }),
            signals = signals,
            events = events,
            trends = state.trends,
            trendsFetchedAt = state.trendsFetchedAt,
            sources = state.sources,
        )
    }

    /** Gripp trendi kuzatiladigan mamlakatlar: o'zingiz, qo'shnilar, kuzatuv ro'yxati (ko'pi bilan 8). */
    fun trendCountries(settings: Settings): List<String> =
        (listOf(settings.country) + countries[settings.country]?.borders.orEmpty() + settings.watchCountries)
            .filter { countries[it] != null }
            .distinct()
            .take(MAX_TREND_COUNTRIES)

    companion object {
        val TREND_MAX_AGE: Duration = Duration.ofHours(12)
        const val TREND_YEARS = 4L
        const val KEEP_DAYS = 180L
        const val MAX_TREND_COUNTRIES = 8

        fun describe(t: Throwable?): String =
            when (t) {
                null -> "noma'lum xato"
                is java.net.UnknownHostException -> "Internet aloqasi yo'q"
                is java.net.SocketTimeoutException -> "Server javob bermadi (vaqt tugadi)"
                is uz.epiradar.engine.net.HttpException -> "Server xatosi (HTTP ${t.code})"
                else -> t.message?.take(160) ?: t::class.java.simpleName
            }
    }
}
