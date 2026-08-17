package com.agrovision.mobile.data.repository

import android.content.ContentValues
import android.content.Context
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import com.agrovision.mobile.core.Fmt
import java.io.OutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Hisobotlar: CSV eksport (jadval) va bir sahifali PDF KPI xulosasi.
 * Ikkalasi ham faqat Android SDK'ning o'z API'lari orqali (tashqi
 * kutubxona/tarmoq shart emas), MediaStore Downloads/AgroVision papkasiga yoziladi.
 */
@Singleton
class ReportRepository @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context,
) {
    fun exportCsv(fileName: String, headers: List<String>, rows: List<List<String>>): String {
        val content = buildString {
            appendLine(headers.joinToString(",") { csvEscape(it) })
            rows.forEach { row -> appendLine(row.joinToString(",") { csvEscape(it) }) }
        }
        return writeToDownloads("$fileName.csv", "text/csv", content.toByteArray(Charsets.UTF_8))
    }

    fun exportKpiPdf(
        year: Int,
        kpiLines: List<Pair<String, String>>,
        sectionTitle: String,
        sectionRows: List<List<String>>,
    ): String {
        val document = PdfDocument()
        val page = document.startPage(PdfDocument.PageInfo.Builder(595, 842, 1).create())
        val canvas = page.canvas
        val titlePaint = Paint().apply { textSize = 20f; isFakeBoldText = true }
        val textPaint = Paint().apply { textSize = 12f }
        val headerPaint = Paint().apply { textSize = 14f; isFakeBoldText = true }

        var y = 50f
        canvas.drawText("AgroVision Mobile — $year-yil hisoboti", 40f, y, titlePaint)
        y += 20f
        canvas.drawText(
            "Yaratildi: ${SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date())}",
            40f, y, textPaint,
        )
        y += 30f
        for ((label, value) in kpiLines) {
            canvas.drawText("$label: $value", 40f, y, textPaint)
            y += 20f
        }
        y += 15f
        canvas.drawText(sectionTitle, 40f, y, headerPaint)
        y += 22f
        for (row in sectionRows.take(28)) {
            canvas.drawText(row.joinToString("   |   "), 40f, y, textPaint)
            y += 18f
            if (y > 800f) break
        }
        document.finishPage(page)

        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val fileName = "agrovision_hisobot_${year}_$stamp.pdf"
        val bytes = java.io.ByteArrayOutputStream().also { document.writeTo(it) }.toByteArray()
        document.close()
        return writeToDownloads(fileName, "application/pdf", bytes)
    }

    private fun csvEscape(value: String): String =
        if (value.contains(",") || value.contains("\"")) "\"${value.replace("\"", "\"\"")}\"" else value

    private fun writeToDownloads(fileName: String, mimeType: String, bytes: ByteArray): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val resolver = context.contentResolver
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/AgroVision")
            }
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: error("MediaStore yozib bo'lmadi")
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
            return fileName
        }
        @Suppress("DEPRECATION")
        val dir = java.io.File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
            "AgroVision",
        ).apply { mkdirs() }
        val target = java.io.File(dir, fileName)
        target.writeBytes(bytes)
        return fileName
    }
}
