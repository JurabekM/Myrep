package uz.sectorverify.feature.report

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import androidx.core.content.res.ResourcesCompat
import java.io.ByteArrayOutputStream
import java.text.DateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.math.sin
import uz.sectorverify.analysis.Geo
import uz.sectorverify.format.SessionMeta
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.SitePlan
import uz.sectorverify.model.Verdict
import uz.sectorverify.ui.R as UiR
import uz.sectorverify.ui.components.labelRes

data class PdfInput(
    val plan: SitePlan,
    val meta: SessionMeta,
    val result: SessionResult,
    val fixes: List<GnssFix>,
    val sha256: String,
    val signatureB64: String,
)

/**
 * §8.2 PDF report drawn by hand on android.graphics.pdf.PdfDocument. [context] must already be localised to
 * the report language (independent of the app language). Paper-friendly light colours.
 */
class PdfReportWriter(private val context: Context, private val locale: Locale) {
    private val res = context.resources
    private val regular: Typeface = ResourcesCompat.getFont(context, UiR.font.noto_sans_regular) ?: Typeface.DEFAULT
    private val bold: Typeface = ResourcesCompat.getFont(context, UiR.font.noto_sans_bold) ?: Typeface.DEFAULT_BOLD
    private val doc = PdfDocument()
    private var page: PdfDocument.Page? = null
    private var pageNo = 0
    private var y = 0f

    private fun paint(size: Float, typeface: Typeface = regular, color: Int = INK) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size
        this.typeface = typeface
        this.color = color
    }

    private val body = paint(BODY)
    private val small = paint(SMALL, color = MUTED)
    private val h1 = paint(H1, bold)
    private val h2 = paint(H2, bold, ACCENT)

    private val canvas: Canvas get() = page!!.canvas

    fun write(input: PdfInput): ByteArray {
        newPage()
        header(input)
        sectors(input)
        polar(input)
        route(input)
        findings(input)
        appendix(input)
        finishPage()
        return ByteArrayOutputStream().also { doc.writeTo(it) }.toByteArray().also { doc.close() }
    }

    val pages: Int get() = pageNo

    private fun newPage() {
        finishPage()
        pageNo++
        page = doc.startPage(PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNo).create())
        y = MARGIN
        canvas.drawText(res.getString(R.string.pdf_page, pageNo), PAGE_W - MARGIN - 60f, PAGE_H - 20f, small)
    }

    private fun finishPage() {
        page?.let { doc.finishPage(it) }
        page = null
    }

    private fun need(h: Float) {
        if (y + h > PAGE_H - MARGIN) newPage()
    }

    private fun line(text: String, p: Paint = body, gap: Float = 4f) {
        for (l in wrap(text, p, PAGE_W - 2 * MARGIN)) {
            need(p.textSize + gap)
            y += p.textSize
            canvas.drawText(l, MARGIN, y, p)
            y += gap
        }
    }

    private fun wrap(text: String, p: Paint, width: Float): List<String> {
        val out = ArrayList<String>()
        for (para in text.split('\n')) {
            var rest = para
            while (rest.isNotEmpty()) {
                var n = p.breakText(rest, true, width, null)
                if (n < rest.length) rest.lastIndexOf(' ', n).takeIf { it > 0 }?.let { n = it }
                out += rest.substring(0, n).trimEnd()
                rest = rest.substring(n).trimStart()
            }
            if (para.isEmpty()) out += ""
        }
        return out
    }

    private fun verdict(v: Verdict) = res.getString(v.labelRes())

    private fun header(i: PdfInput) {
        val df = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT, locale)
        line(res.getString(R.string.pdf_title), h1, 8f)
        line(res.getString(R.string.pdf_site, i.plan.code, i.plan.name))
        line(res.getString(R.string.pdf_coords, "%.5f, %.5f".format(Locale.ROOT, i.plan.lat, i.plan.lon), i.plan.mccMnc))
        line(
            res.getString(
                R.string.pdf_date,
                df.format(Date(i.meta.startedAtUtcMs)),
                i.meta.endedAtUtcMs?.let { df.format(Date(it)) } ?: "—",
            ),
        )
        line(res.getString(R.string.pdf_engineer, i.meta.engineer?.ifBlank { null } ?: "—"))
        line(res.getString(R.string.pdf_device, i.meta.deviceModel, i.meta.apiLevel))
        line(res.getString(R.string.pdf_versions, i.meta.appVersion, i.meta.algoVersion, i.meta.mode.name))
        y += 6f
        val coverage = (i.result.overallCoverage * PERCENT).roundToInt()
        line(res.getString(R.string.pdf_overall, verdict(i.result.verdict), coverage), paint(H2, bold, verdictColor(i.result.verdict)), 8f)
    }

    private fun sectors(i: PdfInput) {
        line(res.getString(R.string.pdf_sectors), h2, 6f)
        val cols = floatArrayOf(0f, 50f, 165f, 210f, 260f, 305f, 350f, 425f)
        val headers = listOf(
            R.string.pdf_col_sector,
            R.string.pdf_col_cell,
            R.string.pdf_col_plan,
            R.string.pdf_col_est,
            R.string.pdf_col_ci,
            R.string.pdf_col_err,
            R.string.pdf_col_verdict,
            R.string.pdf_col_cause,
        ).map(res::getString)
        row(cols, headers, paint(SMALL, bold))
        for (s in i.result.sectors) {
            val e = s.estimate
            row(
                cols,
                listOf(
                    s.label ?: "—",
                    s.key.toString(),
                    s.planAzimuthDeg?.let { "${it.roundToInt()}°" } ?: "—",
                    e?.let { "${it.alphaDeg.roundToInt()}°" } ?: "—",
                    e?.let { "${it.ciHalfDeg.roundToInt()}°" } ?: "—",
                    s.errorDeg?.let { "${it.roundToInt()}°" } ?: "—",
                    verdict(s.verdict).substringBefore(" —"),
                    res.getString(s.cause.labelRes()),
                ),
                paint(SMALL, color = verdictColor(s.verdict)),
            )
        }
        y += 8f
    }

    private fun row(cols: FloatArray, cells: List<String>, p: Paint) {
        need(SMALL + 6f)
        y += SMALL + 2f
        cells.forEachIndexed { idx, c ->
            val w = (cols.getOrNull(idx + 1) ?: (PAGE_W - 2 * MARGIN)) - cols[idx] - 4f
            val n = p.breakText(c, true, w, null)
            canvas.drawText(c.take(n), MARGIN + cols[idx], y, p)
        }
        y += 4f
    }

    private fun polar(i: PdfInput) {
        val groups = i.result.sectors.filter { it.label != null }.groupBy { it.key.rat to it.key.arfcn }
        for ((k, list) in groups) {
            need(POLAR + 30f)
            line(res.getString(R.string.pdf_polar, "${k.first} ${k.second}"), h2, 4f)
            val cx = PAGE_W / 2f
            val cy = y + POLAR / 2f
            val r = POLAR / 2f - 14f
            val grid = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE
                color = LINE
                strokeWidth = 1f
            }
            for (f in listOf(1f, 0.66f, 0.33f)) canvas.drawCircle(cx, cy, r * f, grid)
            canvas.drawText(res.getString(UiR.string.common_north).take(1), cx - 4f, cy - r - 4f, small)
            list.forEachIndexed { idx, s ->
                val color = PALETTE[idx % PALETTE.size]
                s.planAzimuthDeg?.let { a ->
                    val dash = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                        this.color = color
                        strokeWidth = 2f
                        pathEffect = DashPathEffect(floatArrayOf(8f, 6f), 0f)
                    }
                    ray(cx, cy, r, a, dash)
                }
                val e = s.estimate ?: return@forEachIndexed
                val arc = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    this.color =
                        Color.argb(ALPHA_ARC, Color.red(color), Color.green(color), Color.blue(color))
                }
                val sweep = ((e.ciHighDeg - e.ciLowDeg) % 360 + 360) % 360
                canvas.drawArc(
                    RectF(cx - r * 0.9f, cy - r * 0.9f, cx + r * 0.9f, cy + r * 0.9f),
                    (e.ciLowDeg - 90).toFloat(),
                    sweep.toFloat(),
                    true,
                    arc,
                )
                ray(
                    cx,
                    cy,
                    r * 0.95f,
                    e.alphaDeg,
                    Paint(Paint.ANTI_ALIAS_FLAG).apply {
                        this.color = color
                        strokeWidth = 4f
                    },
                )
                val (lx, ly) = point(cx, cy, r + 8f, e.alphaDeg)
                canvas.drawText(s.label.orEmpty(), lx - 8f, ly + 4f, paint(SMALL, bold, color))
            }
            y += POLAR + 6f
        }
    }

    private fun route(i: PdfInput) {
        need(POLAR + 30f)
        line(res.getString(R.string.pdf_route), h2, 4f)
        val cx = PAGE_W / 2f
        val cy = y + POLAR / 2f
        val r = POLAR / 2f - 10f
        val bins = i.result.coveredBins
        val step = 360f / max(1, bins.size)
        val ring = RectF(cx - r, cy - r, cx + r, cy + r)
        bins.forEachIndexed { idx, ok ->
            val p = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE
                strokeWidth = 10f
                color = if (ok) OK else WARN_LIGHT
            }
            canvas.drawArc(ring, idx * step - 90f + 1f, step - 2f, false, p)
        }
        val polar = i.fixes.map {
            Geo.distanceM(i.plan.lat, i.plan.lon, it.lat, it.lon) to
                Geo.bearingDeg(i.plan.lat, i.plan.lon, it.lat, it.lon)
        }
        val extent = max(ROUTE_MIN_EXTENT_M, polar.maxOfOrNull { it.first } ?: 0.0)
        val track = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = ACCENT
            strokeWidth = 1.5f
        }
        polar.zipWithNext().forEach { (a, b) ->
            val (x1, y1) = point(cx, cy, (a.first / extent * (r - 14f)).toFloat(), a.second)
            val (x2, y2) = point(cx, cy, (b.first / extent * (r - 14f)).toFloat(), b.second)
            canvas.drawLine(x1, y1, x2, y2, track)
        }
        canvas.drawCircle(cx, cy, 4f, paint(BODY, color = INK))
        y += POLAR + 6f
    }

    private fun findings(i: PdfInput) {
        line(res.getString(R.string.pdf_findings), h2, 6f)
        for (s in i.result.sectors) {
            val head = "${s.label ?: "—"} · ${s.key} — ${verdict(s.verdict).substringBefore(" —")}"
            line(head, paint(BODY, bold, verdictColor(s.verdict)), 2f)
            line(Recommendations.forSector(res, s, i.result.findings), body, 2f)
            if (s.missingBins.isNotEmpty() && s.verdict == Verdict.INCONCLUSIVE) {
                line(res.getString(R.string.result_missing, Recommendations.directions(s.missingBins)), small, 2f)
            }
            y += 4f
        }
    }

    private fun appendix(i: PdfInput) {
        line(res.getString(R.string.pdf_appendix), h2, 6f)
        line(res.getString(R.string.pdf_rate, i.meta.measuredRateHz?.let { "%.2f".format(Locale.ROOT, it) } ?: "—"), small)
        line(res.getString(R.string.pdf_cleaning, i.result.cleaning.total, i.result.cleaning.kept), small)
        val c = i.meta.config
        line(
            "preset=${c.preset} n=${c.pathLossExponent} rMin=${c.rMinM} rMax=${c.rMaxM} bin=${c.binDeg}° minBins=${c.minBinsForFit} " +
                "bootstrap=${c.bootstrapIterations} cov=${c.minOverallCoverage}/${c.minSectorCoverage} swapErr=${c.swapMaxErrDeg} " +
                "pass=${c.passMaxErrDeg}/${c.passMaxCiHalfDeg} warn=${c.warnMaxErrDeg}/${c.warnMaxCiHalfDeg} seed=${c.seed}",
            small,
        )
        line(res.getString(R.string.pdf_sha, i.sha256), small)
        line(res.getString(R.string.pdf_signature, i.signatureB64), small)
    }

    private fun point(cx: Float, cy: Float, r: Float, bearing: Double): Pair<Float, Float> {
        val a = Math.toRadians(bearing)
        return (cx + r * sin(a)).toFloat() to (cy - r * cos(a)).toFloat()
    }

    private fun ray(cx: Float, cy: Float, r: Float, bearing: Double, p: Paint) {
        val (x, y2) = point(cx, cy, r, bearing)
        canvas.drawLine(cx, cy, x, y2, p)
    }

    private fun verdictColor(v: Verdict) = when (v) {
        Verdict.PASS -> OK
        Verdict.WARN -> WARN
        Verdict.FAIL -> DANGER
        Verdict.INCONCLUSIVE -> MUTED
    }

    private companion object {
        const val PAGE_W = 595 // A4 in PostScript points
        const val PAGE_H = 842
        const val MARGIN = 40f
        const val H1 = 18f
        const val H2 = 13f
        const val BODY = 10f
        const val SMALL = 8f
        const val POLAR = 230f
        const val PERCENT = 100
        const val ALPHA_ARC = 70
        const val ROUTE_MIN_EXTENT_M = 450.0

        // Light (paper) tokens of the Myrep palette.
        val INK = Color.parseColor("#141413")
        val MUTED = Color.parseColor("#5E5D59")
        val LINE = Color.parseColor("#DAD8CE")
        val ACCENT = Color.parseColor("#A9502F")
        val OK = Color.parseColor("#2F6B2E")
        val WARN = Color.parseColor("#9A5B13")
        val WARN_LIGHT = Color.parseColor("#E8C9A0")
        val DANGER = Color.parseColor("#A23B3B")
        val PALETTE = intArrayOf(Color.parseColor("#2A78D6"), Color.parseColor("#EB6834"), OK, WARN, ACCENT, DANGER)
    }
}
